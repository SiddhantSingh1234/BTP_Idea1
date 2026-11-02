"""Phase06 evidence gate: bounded implementation and analytical pilot only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from implementation.trace.model import fingerprint
from implementation.repair.artifacts import write

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes(mapping):return all((ROOT/name).is_file() and sha(ROOT/name)==digest for name,digest in mapping.items())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Use fresh gate output under btp_work')
    checks={}
    checks['accepted_phase05_engineering_gate']=read('reports/phase_05/gate_02.json')['status']=='complete'
    tests=read('reports/phase_06/tests_03/result.json')
    checks['twentyone_acceptance_groups_pass']=tests['tests']==21 and tests['successful'] and tests['errors']==tests['failures']==0
    checks['tested_code_and_configs_identical']=hashes(tests['artifact_sha256'])
    previous=read('reports/phase_06/phase05_regression_01/result.json')
    checks['sixteen_phase05_scientific_regression_groups_pass']=previous['successful'] and previous['tests']==16 and hashes(previous['artifact_sha256'])
    proofs=tests['full_original_semantic_proofs']
    checks['both_original_qft5_unitaries_verified']=len(proofs)==2 and all(p['equivalent_up_to_global_phase'] and p['full_original_circuit_checked'] and p['basis_states']==32 and p['maximum_absolute_error']<1e-12 for p in proofs)
    start=read('reports/phase_06/start_record.json')
    checks['starting_scientific_sources_unchanged']=hashes(start['frozen_artifact_sha256'])
    frozen=True;frozen_count=0
    for study,record in start['benchmark_manifests'].items():
        directory=ROOT/'runs'/study
        frozen &= sha(directory/'manifest.json')==record['manifest_sha256']
        for name,digest in record['files'].items():
            frozen &= sha(directory/name)==digest;frozen_count+=1
    directory=ROOT/'runs/phase05_matched_benchmark_v1'
    manifest=read('runs/phase05_matched_benchmark_v1/manifest.json')
    frozen &= sha(directory/'manifest.json')==(directory/'manifest.sha256').read_text().strip()
    for name,digest in manifest['files'].items():frozen &= sha(directory/name)==digest;frozen_count+=1
    checks['four_frozen_benchmark_studies_intact']=bool(frozen)
    protocol=read('configs/studies/phase06_pilot_v1.json')
    checks['eight_fixed_pipeline_configs_identical']=len(protocol['configuration_sha256'])==8 and hashes(protocol['configuration_sha256'])
    checks['fixed_split_predeclared']=protocol['frozen_before_evaluation'] and len(protocol['development_cases'])==5 and len(protocol['evaluation_cases'])==10 and not set(protocol['development_cases'])&set(protocol['evaluation_cases'])
    dev=read('runs/phase_06/development_01/pilot_results.json');pilot=read('runs/phase_06/pilot_01/pilot_results.json')
    checks['forty_development_outputs_valid']=dev['final_schedules']==40 and dev['all_accepted'] and dev['status_counts']=={'ok':40}
    checks['onehundredsixty_evaluation_outputs_valid']=pilot['final_schedules']==160 and pilot['all_accepted'] and pilot['status_counts']=={'ok':160}
    checks['pilot_compiled_versions_unchanged']=hashes(dev['artifact_sha256']) and hashes(pilot['artifact_sha256'])
    checks['actual_case_hashes_match_frozen_split']=all(read('runs/phase_06/'+folder+'/manifest.json')['input_hashes']==protocol[split+'_cases'] for split,folder in [('development','development_01'),('evaluation','pilot_01')])
    audit=read('runs/phase_06/audit_02/audit.json')
    records=read('runs/phase_06/audit_02/candidate_reconstruction.json')
    checks['all_200_final_outputs_replayed']=audit['status']=='ok' and audit['final_schedules_replayed']==200
    checks['all_616_candidates_independently_reconstructed']=audit['candidate_evaluations_reconstructed']==audit['candidate_records']==len(records)==dev['candidate_evaluations']+pilot['candidate_evaluations']==616
    accepted=[r for r in records if r.get('accepted')]
    checks['all_53_commits_valid_strict_full_improvements']=len(accepted)==audit['accepted_repairs']==53 and all(r['valid'] and r['prefix_unchanged'] and r['after_E']<r['before_E']-1e-12 for r in accepted)
    checks['53_local_global_traps_rejected']=audit['local_global_traps_rejected']==53
    checks['straggler_and_actual_conflict_batch_examples']=audit['straggler_examples']>0 and audit['conflict_batch_examples']>0 and all((ROOT/path).is_file() for path in audit['examples'].values())
    checks['fifty_exact_phase05_controls']=audit['phase05_exact_controls']==50
    checks['audit_tool_version_matches_executed']=sha(ROOT/'tools/finalize_phase06_evidence.py')==audit['source_sha256']
    checks['original_attempt_records_unchanged']=hashes(audit['attempt_record_sha256'])
    raw=[];rows=dev['rows']+pilot['rows']
    for row in rows:raw.append(read(row['raw_result']))
    checks['disabled_and_zero_have_exact_schedule_identity']=all(r['candidate_evaluations']==0 and r['final_schedule_sha256']==r['original_schedule_sha256'] for r in rows if r['repair'] in ['disabled','zero'])
    checks['every_trial_rolls_back_parent_and_rng']=all(e['incumbent_unchanged_after_trial'] and e['caller_rng_restored_after_trial'] for r in raw for e in r['audit'])
    checks['every_result_keeps_valid_baseline_and_caller_state']=all(r['baseline_input_unchanged'] and r['caller_rng_restored'] and r['E']<=r['baseline_E']+1e-12 for r in rows)
    checks['deterministic_work_limits_account_for_failures']=all(r['candidate_evaluations']==len(r['audit']) and r['candidate_evaluations']<=r['options']['max_evaluations'] and r['rounds']<=r['options']['max_rounds'] for r in raw)
    checks['full_repair_work_and_rejected_trials_charged']=all(r['repair_seconds']>=sum(e['evaluation_seconds'] for e in r['audit'])-1e-6 for r in raw) and all(r['total_compile_validate_repair_seconds']==r['baseline_compile_validate_seconds']+r['repair_seconds'] for r in rows)
    checks['no_final_error_regressions']=all(r['E']<=r['baseline_E']+1e-12 for r in rows)
    checks['native_physical_scope_not_overstated']=not pilot['native_physical_validity_claimed'] and not pilot['best_default_selected_from_evaluation']
    checks['resource_peaks_and_storage_measured']=audit['maximum_observed_process_family_peak_bytes']>0 and audit['raw_bytes']>0
    checks['report_csv_and_json_are_exact_raw_exports']=all((ROOT/'reports/phase_06'/name).read_bytes()==(ROOT/'runs/phase_06/pilot_01'/name).read_bytes() for name in ['pilot_results.csv','pilot_results.json','repair_audit.csv'])
    with (ROOT/'reports/phase_06/repair_audit.csv').open(encoding='utf-8',newline='') as handle:csv_rows=list(csv.DictReader(handle))
    checks['audit_csv_contains_all_456_evaluation_trials']=len(csv_rows)==456 and all(all(key in r for key in ['parent_run','candidate_id','predicted_local_E','actual_full_E','valid','accepted','evaluation_seconds','changed_events']) for r in csv_rows)
    checks['primary_archived_pdfs_intact']=all(sha(ROOT/item['path'])==item['sha256'] for item in read('source_review/phase06_primary/manifest.json'))
    version=read('reports/phase_06/version_manifest.json')
    checks['final_pre_evaluation_version_frozen']=hashes(version['artifact_sha256']) and version['version_id']=='phase06-'+fingerprint(version['artifact_sha256'])[:16]
    required=['reports/phase_06/repair_spec.md','reports/phase_06/source_research.md','reports/phase_06/pilot_results.md',
        'reports/phase_06/validation_report.md','reports/phase_06/change_ledger.md','reports/phase_06/runtime_environment.json',
        'reports/phase_06/pilot_results.png','reports/phase_06/pilot_results.svg','reports/phase_06/version_manifest.json',
        'source_review/phase06_primary/README.md','source_review/phase06_primary/references.bib',
        'reports/decisions/D009_PHASE06_FULL_REPLAY_REPAIR.md','handoffs/phase_06.md']
    checks['all_deliverables_present']=all((ROOT/name).is_file() for name in required)
    documents=[ROOT/'README.md',ROOT/'plan/STATUS.md',ROOT/'plan/phases/06_BOUNDED_REPAIR.md',ROOT/'handoffs/phase_06.md',ROOT/'reports/decisions/D009_PHASE06_FULL_REPLAY_REPAIR.md',ROOT/'source_review/phase06_primary/README.md']+list((ROOT/'reports/phase_06').glob('*.md'))
    issues=[];links=0
    for doc in documents:
        for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            target=match[1].strip().strip('<>')
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
            path=unquote(target.partition('#')[0]);dest=(doc.parent/path).resolve() if path else doc;links+=1
            if not dest.exists() and dest!=out:issues.append({'document':doc.relative_to(ROOT).as_posix(),'missing':target})
    checks['all_current_document_links_resolve']=not issues
    result={'phase':'06','status':'complete' if all(checks.values()) else 'needs_revision',
        'accepted_scope':'bounded full-replay repair implementation and fixed small analytical pilot',
        'version_id':version['version_id'],'checks':checks,'passed':sum(checks.values()),'total':len(checks),
        'frozen_benchmark_files_checked':frozen_count,'local_links_checked':links,'link_issues':issues,
        'baseline_controllers_modified_or_restarted':False,'final_full_benchmark_evaluation_claimed':False,
        'artifact_sha256':{'tools/check_phase06.py':sha(Path(__file__))},'command':sys.argv}
    write(out,result)
    print(json.dumps({'status':result['status'],'passed':result['passed'],'total':result['total'],'failed':[k for k,v in checks.items() if not v],'link_issues':issues,'version_id':version['version_id']}))
    return 0 if result['status']=='complete' else 1
if __name__=='__main__':raise SystemExit(main())
