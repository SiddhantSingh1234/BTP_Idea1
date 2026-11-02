"""Compiler-free final replay audit of the frozen Phase01 and Phase03 datasets."""
import argparse,csv,hashlib,json,math,statistics,sys,time,traceback
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
import standalone_baseline as baseline
import model_comparison as comparison


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-280)
def csv_write(p,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase1-out',required=True,type=Path);parser.add_argument('--phase3-out',required=True,type=Path);args=parser.parse_args()
    out1=args.phase1_out.resolve();out3=args.phase3_out.resolve()
    for out in [out1,out3]:
        if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Use fresh output under btp_work')
    lock=None
    while lock is None:
        lock=comparison.acquire(ROOT/'runs/model_comparison_execution.lock')
        if lock is None:print('Waiting for an active timed comparison before audit',flush=True);time.sleep(3)
    start=time.perf_counter()
    try:
        s1=ROOT/'runs/phase01_frozen_baseline_v1';s3=ROOT/'runs/phase03_matched_benchmark_v1'
        m1=baseline.verify(s1,runtime=True);m3=comparison.verify(s3,runtime=True)
        baseline.verify_controller_repair(s1);comparison.verify_execution_revision(s3)
        assert read(s1/'summary.json')['measurement_matrix_complete']
        assert read(s3/'summary.json')['matrix_complete']
        shared=[p for p in m1['files'] if p.startswith('frozen/implementation/')]
        assert all(m1['files'][p]==m3['files'][p] for p in shared)
        sys.path.insert(0,str(s3/'frozen'))
        from implementation.trace.model import load_trace,read_cz_qasm,fingerprint
        from implementation.adapters.upstream import adapt_run
        from implementation.validation.checker import check_trace
        from implementation.metrics.legacy import measure_trace
        from implementation.movement_error.schedule import make_schedule,decision_records
        from implementation.movement_error.evaluator import evaluate
        out1.mkdir(parents=True);out3.mkdir(parents=True)
        for out in [out1,out3]:(out/'audit_source.py').write_bytes(Path(__file__).read_bytes())
        rows1=list(csv.DictReader((s1/'results.csv').open()));rows3=list(csv.DictReader((s3/'results.csv').open()))
        assert len(rows1)==len(rows3)==len(m1['jobs'])==132
        by1={r['target_id']:r for r in rows1};by3={r['target_id']:r for r in rows3}
        assert len(by1)==len(by3)==132 and by1.keys()==by3.keys()=={j['target_id'] for j in m1['jobs']}
        receipts1=[];receipts3=[];errors1=[];errors3=[];source_decisions={};record_hashes={};source_scalars={}
        for i,job in enumerate(m1['jobs']):
            target=job['target_id'];r=by1[target]
            audit={'target_id':target,'algorithm':job['algorithm'],'case':job['case'],'grid':job['grid'],'passed':False}
            try:
                qasm=s1/job['frozen_input'];assert sha(qasm)==job['expected_normalized_sha256']
                assert sha(s1/'frozen'/job['raw_path'])==job['raw_sha256']
                circuit=read_cz_qasm(qasm)
                if job['algorithm']=='rft':
                    records=[(s1/p,read(s1/p)) for p in job['frozen_native_records']]
                    assert len(records)==3 and all(v['status']=='ok' for p,v in records)
                    samples=[v['worker_result']['native_metrics']['Elapsed Time (s)'] for p,v in records]
                    assert len({v['worker_result']['trace_sha256'] for p,v in records})==1
                    selected=job['selected_reference'];worker=s1/'references'/selected['worker']
                    selected_path=s1/'references'/selected['record'];assert sha(selected_path)==selected['sha256']
                    trace=adapt_run(worker,'rft');source=read(worker/'result.json')
                    assert sha(worker/'normalized.qasm')==job['expected_normalized_sha256']
                    assert sha(worker/'instructions.txt')==source['trace_sha256']
                    ref=Path(selected['record']);prior=s1/'references/reports/phase_02/live_audit_v2/attempts'/ref.parent.parent.name/ref.parent.name/'audit.json'
                    assert read(prior)['record_sha256']==selected['sha256']
                    assert read(prior)['legacy_all_match'] and read(prior)['saved_final_mapping_matches']
                    audit['repeat_trace_identical']=True;audit['sample_count']=3
                    assert close(r['compile_seconds'],statistics.median(samples))
                    assert close(r['compile_min_seconds'],min(samples)) and close(r['compile_max_seconds'],max(samples))
                    assert int(r['compile_sample_count'])==3
                    assert close(r['compile_cv'],statistics.stdev(samples)/statistics.mean(samples))
                    for path,value in records:record_hashes[str(path.relative_to(s1))]=sha(path)
                    saved_final=source['boundary_replay']['final_positions']
                else:
                    path,value=next((p,read(p)) for p in sorted((s1/'measurements'/target).glob('attempt_*/attempt_record.json')) if read(p)['status']=='ok')
                    assert value['worker_sha256']==sha(s1/'frozen/tools/corrected_dasatom_worker.py')
                    for name,expected in value['worker_artifact_sha256'].items():assert sha(path.parent/name)==expected,(path,name)
                    assert value.get('monitor_error') is None
                    worker=path.parent/'worker';trace=load_trace(worker/'trace');source=read(worker/'result.json')
                    assert source['full_declared_register']==circuit['num_qubits']
                    assert source['input_sha256']==job['expected_normalized_sha256'] and source['status']=='ok'
                    assert close(r['compile_seconds'],source['corrected_compile_seconds']) and int(r['compile_sample_count'])==1
                    assert source['full_physical_validity_claimed'] is False
                    assert value['process_wall_seconds']<=value['timeout_seconds']+30
                    assert value['peak_working_set_bytes']<=value['memory_limit_bytes']
                    record_hashes[str(path.relative_to(s1))]=sha(path)
                    saved_final=read(worker/'validation.json')['final_positions']
                    audit.update(sample_count=1,wall_seconds=value['process_wall_seconds'],peak_bytes=value['peak_working_set_bytes'],
                        restored_idle_qubits=trace['metadata'].get('register_repair',{}).get('restored_idle_qubits',0),
                        corrected_native_transitions=sum(not x['native_transition_reused'] for x in trace['metadata'].get('transition_reports',[])))
                assert fingerprint(trace['metadata']['circuit'])==fingerprint(circuit)
                validation=check_trace(trace);metrics=measure_trace(trace);legacy=metrics['legacy']
                assert validation['structural_valid'] and not validation['violations']
                expected_final={str(q) if str(q).startswith('a') else 'a'+str(q):tuple(p) for q,p in saved_final.items()}
                assert {q:tuple(p) for q,p in validation['final_positions'].items()}==expected_final
                assert metrics['required_CZ']==metrics['observed_CZ']==len(circuit['gates'])
                for column,key in [('runtime_us','runtime_proxy_us'),('movement_batches','movement_blocks'),('legacy_fidelity','fidelity_proxy')]:assert close(r[column],legacy[key]),(target,column)
                hw=trace['metadata']['hardware'];moves=[e for e in trace['events'] if e['kind']=='move'];gates=[e for e in trace['events'] if e['kind']=='gate']
                B=sum(bool(e['atom_ids']) for e in moves);H=len({e.get('gate_batch',e['event_id']) for e in gates})
                D=sum(max((math.dist(a,b)*hw['spacing_um'] for a,b in zip(e['from_sites'],e['to_sites'])),default=0) for e in moves)
                N=trace['metadata'].get('legacy_scored_qubits',circuit['num_qubits']);G=trace['metadata'].get('legacy_scored_CZ',len(circuit['gates']))
                T=H*hw['cz_duration_us']+4*B*hw['transfer_stage_duration_us']+D/hw['move_speed_um_per_us']
                idle=N*T-G*hw['cz_duration_us'];E=idle/hw['legacy_T2_us']-G*math.log(hw['legacy_f_cz'])-4*B*math.log(hw['legacy_f_transfer'])
                assert close(T,legacy['runtime_proxy_us']) and close(math.exp(-E),legacy['fidelity_proxy'])
                decisions=fingerprint(decision_records(trace['events']));source_decisions[target]=decisions
                source_scalars[target]={'compile_seconds':float(r['compile_seconds']),'runtime_us':float(r['runtime_us']),
                    'movement_batches':int(r['movement_batches']),'fidelity':float(r['legacy_fidelity'])}
                audit.update(passed=True,validation_status=validation['status'],structural_valid=True,
                    unsupported=','.join(validation['coverage']['unsupported']),full_physical_validity_claimed=False,
                    input_register_complete=True,required_CZ=metrics['required_CZ'],observed_CZ=metrics['observed_CZ'],
                    independent_legacy_formula_matches=True,metric_columns_match=True,
                    decisions_sha256=decisions,trace_fingerprint=fingerprint(trace),legacy_E=E)
                write(out1/'targets'/target/'validation.json',validation)
                write(out1/'targets'/target/'metrics.json',metrics)
            except Exception as exc:
                audit['error']=str(exc);errors1.append({'target_id':target,'error':str(exc),'traceback':traceback.format_exc()})
            receipts1.append(audit)
            if (i+1)%12==0:print('Phase01 independent replay',i+1,'/132; failures',len(errors1),flush=True)
        profile_hashes=set();geometry_hashes=set()
        for i,job in enumerate(m3['jobs']):
            target=job['target_id'];r=by3[target];audit={'target_id':target,'algorithm':job['algorithm'],'case':job['case'],'grid':job['grid'],'passed':False}
            try:
                path,record=next((p,read(p)) for p in sorted((s3/'measurements'/target).glob('attempt_*/attempt_record.json')) if read(p)['status']=='ok')
                for name,expected in record['worker_artifact_sha256'].items():assert sha(path.parent/name)==expected,(path,name)
                row=record['result']['rows'][0];directory=ROOT/row['output']
                saved=read(directory/'schedule.json');old=read(directory/'evaluation.json')
                assert row['compilation_reused'] and row['accepted_schedule'] and row['status']=='ok'
                assert r['accepted_schedule']=='True' and r['compilation_reused']=='True'
                assert sha(s3/job['frozen_input'])==job['expected_normalized_sha256']==r['normalized_sha256']
                assert fingerprint(decision_records(saved['source_trace']['events']))==source_decisions[target]
                rebuilt=make_schedule(saved['source_trace'],saved['profile'],'retime')
                assert fingerprint(rebuilt)==fingerprint(saved),'Retiming reconstruction changed'
                result=evaluate(rebuilt,include_audit=False)
                assert result['status']=='ok' and result['valid_for_comparison']
                assert json.loads(json.dumps(result,allow_nan=False))==old,'Independent serialized evaluation differs from saved evaluation'
                budget=result['budget'];terms=budget['terms']
                assert close(sum(terms.values()),budget['total_E']) and close(math.exp(-budget['total_E']),budget['fidelity_proxy'])
                assert saved['profile']['cooling']['enabled'] is False and terms['E_cooling_gate']==0
                scalar=source_scalars[target]
                for field,value in [('compile_seconds',scalar['compile_seconds']),('legacy_runtime_us',scalar['runtime_us']),
                                    ('legacy_fidelity',scalar['fidelity']),('routing_batches',scalar['movement_batches']),
                                    ('extended_E',budget['total_E']),('extended_fidelity',budget['fidelity_proxy']),('extended_makespan_us',result['makespan_us'])]:
                    assert close(r[field],value),(target,field)
                    assert close(row[field],value)
                assert r['profile_sha256']==row['profile_sha256']==result['profile_sha256']==saved['profile_sha256']
                profile_hashes.add(row['profile_sha256']);geometry_hashes.add(row['geometry_sha256'])
                record_hashes['phase03/'+str(path.relative_to(s3))]=sha(path)
                audit.update(passed=True,source_decisions_unchanged=True,compilation_reused=True,retiming_reconstructed_exactly=True,
                    independent_evaluation_identical=True,accepted_under_declared_model=True,native_physical_validity_claimed=False,
                    profile_sha256=result['profile_sha256'],schedule_sha256=fingerprint(saved),
                    total_E=budget['total_E'],fidelity=budget['fidelity_proxy'],runtime_us=result['makespan_us'])
                write(out3/'targets'/target/'validation.json',result['validation'])
            except Exception as exc:
                audit['error']=str(exc);errors3.append({'target_id':target,'error':str(exc),'traceback':traceback.format_exc()})
            receipts3.append(audit)
            if (i+1)%12==0:print('Phase03 independent reconstruction/evaluation',i+1,'/132; failures',len(errors3),flush=True)
        if len(profile_hashes)!=1 or len(geometry_hashes)!=3:
            errors3.append({'target_id':'profile_coverage','error':'Expected one resolved profile and three geometry hashes'})
        basechecks={'original_manifest_verified':True,'controller_repair_verified':True,'runtime_environment_verified':True,
                    'targets':132,'audited_RFT_timing_samples':198,'audited_corrected_DasAtom_measurements':66,
                    'paper_reproduction_claimed':False,'full_physical_validity_claimed':False}
        summary1={**basechecks,'passed':not errors1,'passed_targets':sum(r['passed'] for r in receipts1),
            'validation_statuses':dict(Counter(r.get('validation_status') for r in receipts1)),
            'restored_idle_register_targets':sum(r.get('restored_idle_qubits',0)>0 for r in receipts1),'errors':errors1}
        summary3={'passed':not errors3,'targets':132,'passed_targets':sum(r['passed'] for r in receipts3),
            'common_profile_hashes':sorted(profile_hashes),'geometry_hashes':sorted(geometry_hashes),
            'source_decisions_unchanged':not errors3,'compilation_reused':not errors3,
            'retiming_and_evaluation_replayed':not errors3,'native_physical_validity_claimed':False,'errors':errors3}
        evidence={'created_utc':datetime.now(timezone.utc).isoformat(),'phase1_manifest_sha256':sha(s1/'manifest.json'),
            'phase1_results_sha256':sha(s1/'results.csv'),'phase3_manifest_sha256':sha(s3/'manifest.json'),
            'phase3_results_sha256':sha(s3/'results.csv'),'record_sha256':record_hashes,
            'phase1_complete_decisions_sha256':source_decisions,'auditor_sha256':sha(__file__),
            'wall_seconds':time.perf_counter()-start,'no_compiler_executed':True}
        for out,receipts,summary in [(out1,receipts1,summary1),(out3,receipts3,summary3)]:
            write(out/'summary.json',summary);write(out/'receipts.json',receipts);write(out/'evidence.json',evidence);csv_write(out/'audit.csv',receipts)
        print(json.dumps({'phase1_passed':summary1['passed'],'phase3_passed':summary3['passed'],'wall_seconds':evidence['wall_seconds']}),flush=True)
        return 0 if summary1['passed'] and summary3['passed'] else 1
    finally:comparison.release(lock)


if __name__=='__main__':raise SystemExit(main())
