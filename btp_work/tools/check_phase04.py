"""NEW Phase04 final evidence gate; correctness and honest negative findings."""
import argparse,hashlib,importlib.util,json,math,re,sys
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.trace.model import fingerprint
from implementation.lookahead.potential import load_options


def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes_match(mapping):return all((ROOT/name).exists() and sha(ROOT/name)==value for name,value in mapping.items())
def normalized(name):return name.replace('\\','/')


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--finalize',action='store_true');args=parser.parse_args();out=args.out.resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a fresh gate output inside btp_work')
 checks={};tests=read('reports/phase_04/tests_06/result.json');reg=read('reports/phase_04/phase03_regression_01/result.json')
 checks['accepted_phase03_dependency']=read('reports/phase_03/gate_01.json')['status']=='complete'
 checks['seventeen_lookahead_groups_pass']=tests['successful'] and tests['tests']==17 and not tests['errors'] and not tests['failures']
 checks['tested_current_code_configs_unchanged']=hashes_match(tests['artifact_sha256'])
 checks['sixteen_model_regression_groups_pass']=reg['successful'] and reg['tests']==16 and not reg['errors'] and not reg['failures']
 checks['shared_model_regression_artifacts_unchanged']=hashes_match(reg['artifact_sha256'])
 start=read('reports/phase_04/start_record.json')['frozen_artifact_sha256'];receipt=read('reports/phase_04/concurrent_controller_change.json');operational=receipt['path']
 scientific={k:v for k,v in start.items() if k!=operational}
 checks['original_scientific_sources_worker_plan_unchanged']=hashes_match(scientific)
 checks['external_operational_guard_audited']=receipt['starting_sha256']==start[operational] and sha(ROOT/operational)==receipt['current_sha256'] and sha(ROOT/receipt['archived_pre_guard_source'])==receipt['starting_sha256'] and receipt['phase04_modified_this_file'] is False
 configs=[load_options(p) for p in (ROOT/'configs/variants').glob('lookahead.*.json')]
 checks['five_frozen_variants']=len(configs)==5 and {p['h'] for p in configs if p['lookahead_policy']=='next_events'}=={1,2,4,8} and all(p['gamma']==.9 and p['weight_mode']=='uniform' and p['assignment_future_bias'] is False for p in configs)
 final=read('runs/phase_04/pilot_03/pilot_results.json');manifest=read('runs/phase_04/pilot_03/pilot_manifest.json');replay=read('runs/phase_04/pilot_03/cached_replay.json');rows=final['rows']
 checks['current_replay_artifacts_frozen']=hashes_match(final['artifact_sha256'])
 old=final['source_compilation_artifact_sha256'];changed={normalized(k) for k,v in old.items() if sha(ROOT/k)!=v}
 checks['cached_production_code_unchanged_except_counterexample']=changed=={'implementation/lookahead/fixtures.py'}
 spec=importlib.util.spec_from_file_location('_phase04_gate_cases',ROOT/'tools/run_phase04_pilot.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 checks['all_compiled_case_dictionaries_unchanged']=fingerprint(module.cases())==fingerprint(manifest['cases']) and replay['source_cases_unchanged']
 checks['forty_schedules_accepted_and_replayed']=len(rows)==40 and final['status_counts']=={'ok':40} and final['all_accepted'] and len(replay['records'])==40 and replay['all_identical'] and all(row['accepted_schedule'] and row['status']=='ok' for row in rows)
 checks['cached_raw_integrity']=all(sha(ROOT/item['cached_result'])==item['cached_result_sha256'] and item['status']=='ok' and item['budget_identical'] for item in replay['records'])
 checks['no_timing_relabelled_as_new_compile']=final['fresh_compile_attempts']==0 and final['current_validation_replay_count']==40 and all(item['compiled_timing_reused_without_relabelling'] for item in replay['records'])
 checks['compiled_and_replayed_schedule_hashes_match']=True;checks['source_instructions_intact']=True;checks['no_future_placement_or_consumed_gate_in_audit']=True;checks['exact_legacy_instruction_files_equal']=True
 for row,item in zip(rows,replay['records']):
  result_path=ROOT/row['raw_result'];raw=json.loads(result_path.read_text());comp=json.loads(result_path.with_name('compilation.json').read_text())
  checks['compiled_and_replayed_schedule_hashes_match'] &= sha(ROOT/row['raw_schedule'])==item['schedule_sha256']
  checks['source_instructions_intact'] &= sha(result_path.with_name('instructions.txt'))==row['instructions_sha256']
  batches={(b['logical_layer'],tuple(b['active_gate_ids'])):b for b in comp['batches']}
  for d in comp['decisions']:
   if d['policy']!='next_events':continue
   blocked=set(d['completed_gate_ids'])|set(d['active_gate_ids'])
   checks['no_future_placement_or_consumed_gate_in_audit'] &= all(e['gate_id'] not in blocked and e['logical_layer_delta']>=0 for e in d['events'])
   batch=batches[(d['logical_layer'],tuple(d['active_gate_ids']))];snapshot={**batch['current_positions'],**batch['committed_active_targets']}
   for anchor in d['resolved_anchors']:
    checks['no_future_placement_or_consumed_gate_in_audit'] &= anchor['site']==snapshot[str(anchor['partner'])] and anchor['origin'] in ('current','committed_active')
  if row['variant']=='legacy_exact':checks['exact_legacy_instruction_files_equal'] &= result_path.with_name('instructions.txt').read_bytes()==result_path.with_name('direct_control_instructions.txt').read_bytes() and raw['legacy_rng_after_equal']
 compatibility=read('runs/phase_04/pilot_03/legacy_compatibility.json')
 checks['eight_exact_legacy_controls']=compatibility['all_exact'] and len(compatibility['exact_controls'])==8 and all(c['schedule_equal'] and c['rng_equal'] for c in compatibility['exact_controls'])
 checks['generalized_h1_differences_reported']=final['generalized_h1_changed_schedules']==4 and sum(c['schedule_equal_to_legacy'] is False for c in compatibility['generalized_h1_differences'])==4
 golden=read('runs/phase_00/compiled_fixture_01/trace.json');frozen_row=next(row for row in rows if row['case']=='forced_eviction_ladder6' and row['seed']==42 and row['variant']=='legacy_exact')
 checks['historical_fixture_normalized_text_hash']=frozen_row['instructions_sha256']==golden['trace_sha256']
 counter=read('runs/phase_04/pilot_03/nonmonotonic_horizon.json')
 checks['vacant_target_nonmonotonic_example']=all(c['status']=='ok' and c['destination_initially_vacant'] for c in counter.values()) and counter['1']['chosen_site']==[0,2] and counter['2']['chosen_site']==[2,1] and counter['2']['E']>counter['1']['E'] and counter['2']['makespan_us']>counter['1']['makespan_us']
 proofs=[read('reports/phase_04/full_original_'+h+'_01/comparison.json') for h in ['h1','h4']]
 checks['full_original_qft5_semantics']=all(p['equivalent_up_to_global_phase'] and p['full_original_circuit_checked'] and p['maximum_absolute_error']<1e-9 and not p['physical_validity_implied'] for p in proofs)
 checks['both_cli_smokes_pass']=all(read('runs/phase_04/cli_'+name+'_01/result.json')['status']=='ok' for name in ['legacy','h4'])
 checks['honest_negative_pilot_result']=sum(row['delta_E_vs_legacy']<-1e-14 for row in rows)==0 and sum(row['delta_E_vs_legacy']>1e-14 for row in rows)==6
 checks['report_exports_match_canonical']=all((ROOT/'reports/phase_04'/name).read_bytes()==(ROOT/'runs/phase_04/pilot_03'/name).read_bytes() for name in ['pilot_results.csv','pilot_results.json','pilot_results.svg','pilot_results.png'])
 checks['original_papers_unchanged']=all(sha(ROOT.parent/item['source'])==item['sha256'] for item in read('source_review/manifest.json'))
 required=['reports/phase_04/lookahead_spec.md','reports/phase_04/source_research.md','reports/phase_04/validation_report.md','reports/phase_04/pilot_results.md','reports/phase_04/legacy_compatibility_report.md','reports/phase_04/change_ledger.md','reports/decisions/D006_PHASE04_EVENT_LOOKAHEAD.md','handoffs/phase_04.md']
 checks['required_deliverables_present']=all((ROOT/p).exists() for p in required)
 docs=[ROOT/'README.md']
 for base in ['plan','handoffs','reports/phase_04','reports/decisions']:docs.extend((ROOT/base).rglob('*.md'))
 issues=[];links=0
 for doc in set(docs):
  for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
   target=match.group(1).strip().strip('<>')
   if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
   part=target.partition('#')[0];dest=(doc.parent/unquote(part)).resolve() if part else doc;links+=1
   if not dest.exists():issues.append({'document':str(doc.relative_to(ROOT)),'missing_target':target})
 checks['project_document_links']=not issues
 complete=all(checks.values());status_text=(ROOT/'plan/STATUS.md').read_text(encoding='utf-8');phase1=[line for line in status_text.splitlines() if line.startswith('| 01 |')]
 result={'phase':'04','status':'complete' if complete else 'needs_revision','accepted_scope':'parking-only next-event implementation and small analytical pilot',
         'checks':checks,'documents_checked':len(set(docs)),'local_links_checked':links,'document_link_issues':issues,
         'tested_k':[1,2,4,8],'gamma':.9,'best_k_selected':False,'improvement_over_legacy_demonstrated':False,
         'phase01_controlled_or_restarted':False,'phase01_tracker_row_observed':phase1,'phase01_completion_claimed':False,
         'quality_attempts':40,'source_timing_samples':80,'replay_fresh_compile_attempts':0,'current_counterexamples':2,
         'command':sys.argv}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 if complete and args.finalize:
  changes={
   'handoffs/phase_04.md':('**Status: in_progress; final evidence gate pending.**','**Status: complete within the declared implementation/pilot scope.** [Final gate](../reports/phase_04/gate_01.json) passes.'),
   'reports/phase_04/validation_report.md':('Status: final evidence gate pending.','Status: complete within the declared implementation/pilot scope; [final gate](gate_01.json) passes.'),
   'README.md':('Phase04 lookahead implementation/tests/pilot delivered; final evidence gate pending.','Phase04 lookahead implementation and pilot complete; [final gate](reports/phase_04/gate_01.json) passes.'),
   'plan/phases/04_K_FUTURE_LOOKAHEAD.md':('delivered; final gate pending.','delivered; [final gate](../../reports/phase_04/gate_01.json) passes within the declared implementation/pilot scope.')}
  for name,(old,new) in changes.items():
   p=ROOT/name;text=p.read_text(encoding='utf-8')
   if old not in text:raise ValueError('Missing finalization anchor '+name)
   p.write_text(text.replace(old,new),encoding='utf-8',newline='\n')
  p=ROOT/'plan/STATUS.md';text=p.read_text(encoding='utf-8');lines=text.splitlines()
  for i,line in enumerate(lines):
   if line.startswith('| 04 |'):lines[i]='| 04 | complete | Codex /root | Accepted03 analytical model, D006 | gate_01 passes:17 lookahead groups,16 unchanged model groups,40 replayed valid schedules and8 exact legacy controls; no improvement over legacy demonstrated; no best k selected |'
  text='\n'.join(lines)+'\n';text=text.replace('Code/test/pilot work delivered; final evidence gate pending.','Code/test/pilot complete within declared scope; [final gate](../reports/phase_04/gate_01.json) passes.')
  p.write_text(text,encoding='utf-8',newline='\n')
  with (ROOT/'handoffs/phase_04.md').open('a',encoding='utf-8') as f:f.write('\nFinal tested gate command:\n\n```powershell\n& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/check_phase04.py --out btp_work/reports/phase_04/gate_01.json --finalize\n```\n\nAll gate checks pass. This closes Phase04 implementation/pilot acceptance, not a performance-improvement claim or Phase01 completion.\n')
 print(json.dumps({'status':result['status'],'passed':sum(checks.values()),'total':len(checks),'link_issues':issues,'improvement_demonstrated':False,'best_k_selected':False}))
 if not complete:print(json.dumps({'failed_checks':[k for k,v in checks.items() if not v]}))
 return 0 if complete else 1


if __name__=='__main__':raise SystemExit(main())