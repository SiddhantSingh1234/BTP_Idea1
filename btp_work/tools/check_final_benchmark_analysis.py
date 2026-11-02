"""Independent final report gate and scoped acceptance metadata; no measurement edits."""
import argparse,csv,hashlib,json,math,re,shutil,statistics,sys
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
import standalone_baseline as baseline
import model_comparison as comparison

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvrows(p):return list(csv.DictReader(p.open(newline='',encoding='utf-8-sig')))
def near(a,b):return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-280)

def receipt_tests(out):
    folder=ROOT/'runs/final_acceptance_metadata_fixture_01';folder.mkdir()
    manifest=folder/'manifest.json';manifest.write_text('{"fixture":true}')
    results=folder/'results.csv';results.write_text('target,value\nx,1\n')
    record=folder/'measurements/x/attempt_01/attempt_record.json';write(record,{'status':'ok'})
    gate=folder/'fixture_gate.json';write(gate,{'passed':True})
    receipt={'schema':'benchmark_acceptance.v1','accepted_utc':'fixture','scope':'metadata_test_only',
        'manifest_sha256':sha(manifest),'results_sha256':sha(results),'gate_path':str(gate.relative_to(ROOT)),
        'gate_sha256':sha(gate),'record_sha256':{str(record.relative_to(folder)):sha(record)},
        'status_fields':{'phase_01_complete':True}}
    state={'progress':{'phase_01_complete':False},'summary':{'phase_01_complete':False}}
    checks={}
    checks['missing_receipt_preserves_status']=baseline.apply_final_acceptance(folder,deepcopy(state))==state
    write(folder/'final_acceptance.json',receipt)
    accepted=baseline.apply_final_acceptance(folder,deepcopy(state))
    checks['matching_receipt_accepted']=accepted['final_acceptance']['valid'] and accepted['summary']['phase_01_complete']
    for name,target in [('results',results),('manifest',manifest),('gate',gate),('record',record)]:
        data=target.read_bytes();target.write_bytes(data+b' ')
        value=baseline.apply_final_acceptance(folder,deepcopy(accepted))
        checks[name+'_tamper_rejected']=not value['final_acceptance']['valid'] and not value['summary']['phase_01_complete']
        target.write_bytes(data)
    write(out/'acceptance_status_tests.json',{'checks':checks,'passed':all(checks.values()),'tests':len(checks)})
    return all(checks.values())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--commit',action='store_true');args=parser.parse_args()
    out=ROOT/'reports/final_benchmark_analysis_01';gate_path=out/'final_gate.json'
    if gate_path.exists():raise ValueError('Final gate already exists; preserve it')
    s1=ROOT/'runs/phase01_frozen_baseline_v1';s3=ROOT/'runs/phase03_matched_benchmark_v1';s4=ROOT/'runs/phase04_matched_benchmark_v2'
    a1=ROOT/'reports/phase_01/final_dataset_audit_02';a3=ROOT/'reports/phase_03/full_dataset_audit_02'
    checks={};m1=baseline.verify(s1,runtime=True);m3=comparison.verify(s3,runtime=True);m4=comparison.verify(s4,runtime=True)
    checks['all_frozen_manifests_and_environment_verified']=True
    checks['phase1_independent_replay_132']=read(a1/'summary.json')['passed'] and read(a1/'summary.json')['passed_targets']==132
    checks['phase3_independent_reconstruction_132']=read(a3/'summary.json')['passed'] and read(a3/'summary.json')['passed_targets']==132
    evidence=read(a1/'evidence.json')
    checks['datasets_match_audit']=sha(s1/'results.csv')==evidence['phase1_results_sha256'] and sha(s3/'results.csv')==evidence['phase3_results_sha256']
    expected_records=evidence['record_sha256']
    checks['all_committed_audit_records_match']=all(sha((s3/name[len('phase03/'):]) if name.startswith('phase03/') else (s1/name))==expected for name,expected in expected_records.items())
    hashes=read(out/'artifact_sha256.json')
    checks['all_generated_artifacts_match']=all(sha(out/name)==expected for name,expected in hashes.items())
    from PIL import Image
    for image in out.glob('*.png'):
        with Image.open(image) as im:im.verify()
    checks['five_valid_plot_exports']=len(list(out.glob('*.png')))==5 and len(list(out.glob('*.svg')))==5 and (out/'benchmark_figures.pdf').stat().st_size>1000
    raw1=csvrows(s1/'results.csv');raw3=csvrows(s3/'results.csv');raw4=csvrows(s4/'results.csv')
    paper=csvrows(out/'paper_comparison_all132.csv');model=csvrows(out/'phase3_model_change_all132.csv');lookahead=csvrows(out/'phase4_matched_comparison_all396.csv')
    checks['all_target_rows_exported']=len(raw1)==len(raw3)==len(paper)==len(model)==132 and len(raw4)==len(lookahead)==396
    by1={r['target_id']:r for r in raw1};by3={r['target_id']:r for r in raw3}
    checks['paper_ratios_recomputed']=all(near(r['compile_measured_to_paper'],float(by1[r['target_id']]['compile_seconds'])/float(r['paper_compile_seconds'])) and int(r['movement_delta'])==int(by1[r['target_id']]['movement_batches'])-int(r['paper_movement_batches']) for r in paper)
    checks['model_changes_recomputed']=all(near(r['fidelity_retention'],float(by3[r['target_id']]['extended_fidelity'])/float(by1[r['target_id']]['legacy_fidelity'])) and near(r['runtime_ratio'],float(by3[r['target_id']]['extended_makespan_us'])/float(by1[r['target_id']]['runtime_us'])) for r in model)
    summary=read(out/'summary.json');models=summary['phase3_model_summary']
    checks['model_summary_medians_match']=all(near(r['median_fidelity_retention'],statistics.median(float(x['fidelity_retention']) for x in model if x['algorithm']==r['algorithm'])) for r in models)
    bases={r['target_id']:r for r in raw4 if r['variant']=='legacy_exact'}
    checks['matched_phase4_ratios_recomputed']=all(near(r['compile_ratio_vs_matched_original'],float(r['compile_seconds'])/float(bases[r['target_id']]['compile_seconds'])) and near(r['delta_E_vs_matched_original'],float(r['extended_E'])-float(bases[r['target_id']]['extended_E'])) for r in lookahead)
    checks['all_horizon_outcomes_accounted']=all(r['better']+r['tie']+r['worse']==66 for r in summary['phase4_summary'])
    analysis_evidence=read(out/'evidence.json')
    checks['phase4_commit_records_match']=all(sha(s4/name)==value for name,value in analysis_evidence['phase4_record_sha256'].items())
    ref=ROOT/'reports/phase_01/paper_reference_01';rv=read(ref/'verification.json')
    checks['paper_180_printed_and_288_vector_values_verified']=rv['printed_numeric_cells_verified']==180 and rv['figure_metric_values_recovered']==288 and rv['reference_sha256']==sha(ref/'paper_reference.csv')
    checks['timing_drift_66_existing_controls']=len(csvrows(out/'unchanged_RFT_timing_drift.csv'))==66 and analysis_evidence['timing_drift_controls_reused']==66
    report=(out/'report.md').read_text()
    checks['limitations_explicit']=all(token in report for token in ['not exact historical paper reproduction','different timer scopes','one fresh accepted sample','no confidence interval','not a heating-only effect'])
    checks['paper_and_physical_reproduction_not_claimed']=summary['paper_exact_reproduction_claimed'] is False and summary['calibrated_hardware_fidelity_claimed'] is False
    checks['acceptance_metadata_regressions_pass']=receipt_tests(out)
    gate={'created_utc':datetime.now(timezone.utc).isoformat(),'passed':all(checks.values()),'checks':checks,
        'scope':'D001/D005/D006 pinned-source baseline and completed model/benchmark analysis',
        'phase1_dataset_and_analysis_complete':all(checks.values()),'phase3_dataset_and_analysis_complete':all(checks.values()),
        'phase4_artifact_inline_validation_and_analysis_complete':all(checks.values()),'phase4_additional_full_physics_replay_performed':False,
        'exact_paper_reproduction_claimed':False,'calibrated_physical_fidelity_claimed':False,
        'limitations':['Unknown manuscript revision/options/input identities','Different historical host and timer scopes','Three RFT timing samples and one new sample per target/variant','Normalized CZ and declared analytical geometry scope'],
        'artifact_manifest_sha256':sha(out/'artifact_sha256.json'),'auditor_source_sha256':sha(Path(__file__))}
    write(gate_path,gate)
    print(json.dumps({'passed':gate['passed'],'checks':checks}),flush=True)
    if not gate['passed']:return 1
    if args.commit:
        stamp=gate['created_utc']
        phase1_records={name:value for name,value in expected_records.items() if not name.startswith('phase03/')}
        phase3_records={name[len('phase03/'):]:value for name,value in expected_records.items() if name.startswith('phase03/')}
        descriptors=[
            (s1,phase1_records,'pinned_source_baseline_D001_D005_D006',{'phase_01_complete':True,'final_dataset_audit_passed':True,'acceptance_scope':'pinned_source_baseline_D001_D005_D006','remaining_acceptance':None,'paper_reproduction_claimed':False}),
            (s3,phase3_records,'Phase03_full_dataset_and_model_analysis',{'full_benchmark_analysis_complete':True,'final_dataset_audit_passed':True}),
            (s4,analysis_evidence['phase4_record_sha256'],'Phase04_matched_integrity_inline_validation_analysis',{'full_benchmark_analysis_complete':True,'artifact_and_inline_validation_audit_passed':True,'additional_full_physics_replay_performed':False})]
        for study,records,scope,fields in descriptors:
            receipt={'schema':'benchmark_acceptance.v1','accepted_utc':stamp,'scope':scope,
                'manifest_sha256':sha(study/'manifest.json'),'results_sha256':sha(study/'results.csv'),
                'gate_path':str(gate_path.relative_to(ROOT)),'gate_sha256':sha(gate_path),
                'record_sha256':records,'status_fields':fields}
            write(study/'final_acceptance.json',receipt)
            for name in ['progress.json','summary.json']:
                value=read(study/name);value.update(fields);value['accepted_utc']=stamp;write(study/name,value)
            value=baseline.apply_final_acceptance(study,{'progress':read(study/'progress.json'),'summary':read(study/'summary.json')})
            assert value['final_acceptance']['valid']
        wrappers=[('phase_01','reproduction_report.md','Phase 1 accepted pinned-source baseline','All 132 targets, 198 RFT timing samples and 66 corrected DasAtom measurements are complete. Independent replay passes every target. Exact manuscript reproduction and calibrated native physical validity are not claimed.'),
            ('phase_03','full_benchmark_report.md','Phase 3 full benchmark/model analysis complete','All 132 schedules pass exact reconstruction and serialized evaluator replay. Compilation and routing choices are unchanged; this is a model/timing change.'),
            ('phase_04','full_benchmark_report.md','Phase 4 full matched analysis complete','All 396 rows on 66 targets are available. Artifact hashes, exact unchanged controls, shared model, inline validation and budget algebra were verified. No additional full physical replay of variants was performed.')]
        for folder,name,title,body in wrappers:
            (ROOT/'reports'/folder/name).write_text('# '+title+'\n\n'+body+'\n\n[Full report, statistics and comparisons](../final_benchmark_analysis_01/report.md)\n\n[Final gate](../final_benchmark_analysis_01/final_gate.json)\n',encoding='utf-8')
        shutil.copyfile(out/'paper_comparison_all132.csv',ROOT/'reports/phase_01/comparison.csv')
        descriptions={'01':'Complete within D001/D005/D006 pinned-source scope: 132 targets, 198 RFT samples and 66 corrected DasAtom measurements. Independent replay and legacy formulas pass. Historical paper configuration and native physical evidence remain explicit limits.',
            '03':'The full132-schedule benchmark and model-change analysis are complete. Every schedule reconstructs exactly and every serialized evaluator output replays identically. Same decisions; one analytical no-cooling profile.',
            '04':'Full matched benchmark:396 accepted rows. h1 better/tie/worse E counts41/2/23; h2 41/3/22; h4 37/4/25; h8 32/4/30. Median compilation overhead is positive. No best h or universal gain is claimed. Artifact/inline-validation/budget audit passed; no additional full physical replay was run.'}
        for phase,body in descriptions.items():
            handoff=ROOT/('handoffs/phase_'+phase+'.md')
            prefix='# Final benchmark analysis checkpoint, 29 October 2026\n\n'+body+'\n\n[Audited results and plots](../reports/final_benchmark_analysis_01/report.md) | [Final gate](../reports/final_benchmark_analysis_01/final_gate.json).\n\nEarlier checkpoints below remain historical evidence.\n\n---\n\n'
            handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8')
        status=ROOT/'plan/STATUS.md';text=status.read_text(encoding='utf-8')
        current="""<!-- BEGIN PAPER_FOCUS_V2 CURRENT -->
Final analysis, 29 October2026: Phase01 is complete within D001/D005/D006 pinned-source scope. All132 measurements, 198 RFT timing samples and66 corrected DasAtom traces are complete. Independent Phase01 replay and Phase03 reconstruction/evaluation pass132/132. Phase03 full analysis and Phase04 matched396-row analysis are complete. [Report](../reports/final_benchmark_analysis_01/report.md), [gate](../reports/final_benchmark_analysis_01/final_gate.json). Exact historical paper identity and calibrated physical fidelity remain unclaimed.
<!-- END PAPER_FOCUS_V2 CURRENT -->"""
        text=re.sub(r'<!-- BEGIN PAPER_FOCUS_V2 CURRENT -->.*?<!-- END PAPER_FOCUS_V2 CURRENT -->',current,text,flags=re.S)
        text=re.sub(r'<!-- BEGIN PHASE03 D004 current status -->.*?<!-- END PHASE03 D004 current status -->','<!-- BEGIN PHASE03 D004 current status -->\nPhase02 engineering remains accepted under D004. Phase03 engineering and132-row analysis are complete; Phase01 now closes under pinned-source scope. Historical paper/calibration limitations remain.\n<!-- END PHASE03 D004 current status -->',text,flags=re.S)
        replacements={
            '01':'| 01 | complete | Codex /root | D001/D005/D006 pinned-source scope | 132 targets; 198 RFT samples; 66 corrected DasAtom traces; replay/formulas, paper comparison and figure/table exports pass final gate; historical paper/physical calibration unclaimed |',
            '03':'| 03 | complete | Codex /root | Accepted02, D004 | Engineering evidence retained; full132-row dataset independently reconstructed/replayed; common-model analysis and final gate pass |',
            '04':'| 04 | complete | Codex /root | Accepted03 | Full66-target/396-row matched analysis; quality gains mixed and median compilation overhead positive; no best h; artifact/inline-validation audit passes |'}
        for key,line in replacements.items():text=re.sub(r'^\| '+key+r' \|.*$',lambda match:line,text,flags=re.M)
        status.write_text(text,encoding='utf-8')
        plan=ROOT/'plan/phases/01_RFT_REPRODUCTION.md';text=plan.read_text(encoding='utf-8')
        note='> Current acceptance,29 October2026: complete under D001/D005/D006 pinned-source scope. All132 targets and final audit/analysis deliverables pass [the final gate](../../reports/final_benchmark_analysis_01/final_gate.json). The original exact-paper checklist below is historical; unknown manuscript configuration and physical calibration remain limitations.\n\n'
        plan.write_text(note+text,encoding='utf-8')
        with (ROOT/'README.md').open('a',encoding='utf-8') as stream:
            stream.write('\n\n## Final baseline/model analysis\n\n[Phase1/paper, Phase3 model and matched Phase4 report](reports/final_benchmark_analysis_01/report.md), [visual report](reports/final_benchmark_analysis_01/report.html), and [acceptance gate](reports/final_benchmark_analysis_01/final_gate.json).\n')
        print('Committed scoped acceptance receipts and current handoffs/status. Measured CSVs and frozen sources remain unchanged.')
    return 0

if __name__=='__main__':raise SystemExit(main())
