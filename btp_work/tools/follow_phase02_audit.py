"""Audit every terminal Phase 01 attempt without writing to the live study.

Immutable per-attempt evidence; resume-safe; one writer; all repetitions.
Follow exits only after the controller has stopped and every planned job has
an attempt or an explicit censored omission. It never declares Phase 01 passed.
"""
import argparse
from collections import Counter
import csv
import ctypes
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from implementation.adapters.upstream import adapt_run
from implementation.metrics.legacy import measure_trace
from implementation.trace.model import fingerprint
from implementation.validation.checker import check_trace


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def now():return datetime.now(timezone.utc).isoformat()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def compare_legacy(source,metrics):
    legacy=metrics['legacy'];native=source.get('native_metrics',{});pairs={}
    if source['algorithm']=='rft':
        names={'gate_stages':'Num Gate Cycles','movement_blocks':'Num Movement Ops',
            'scored_qubits':'Num Qubit','scored_CZ':'Num CZ Gates',
            'four_per_block_transfer_alias':'Num Transferred Qubits',
            'sum_batch_max_distance_um':'Total Move Distance','runtime_proxy_us':'Total_T (us)',
            'idle_proxy_us':'Idle Time (us)','fidelity_proxy':'Fidelity (DasAtom Model)'}
        pairs={key:(legacy[key],native[name]) for key,name in names.items()}
        pairs['move_records']=(metrics['move_records'],native['Num Moves'])
    else:
        score=native['native_score']
        for key,index in [('idle_proxy_us',0),('fidelity_proxy',1),('runtime_proxy_us',3),
            ('four_per_block_transfer_alias',4),('sum_batch_max_distance_um',6)]:pairs[key]=(legacy[key],score[index])
        pairs['move_records']=(metrics['move_records'],score[5])
    comparison={key:{'independent':actual,'native':expected,
        'matches':math.isclose(actual,expected,rel_tol=1e-11,abs_tol=1e-300)} for key,(actual,expected) in pairs.items()}
    return {'all_match':all(r['matches'] for r in comparison.values()),'inputs':comparison}


def audit_one(record_path,destination,plan):
    record=read(record_path);job=record['job'];worker=record_path.parent/'worker'
    row={'job_id':job['id'],'attempt':record['attempt'],'algorithm':job['algorithm'],
        'repetition':job['repetition'],'source_status':record['status'],
        'source_diagnostic_status':record.get('diagnostic_status'),
        'record_path':str(record_path.relative_to(ROOT)),'record_sha256':sha(record_path),
        'audited_utc':now(),'adapter_error':False,'legacy_all_match':None,
        'saved_final_mapping_matches':None,'evidence_status':None,'paper_batch_policy_status':None}
    required=['result.json','normalized.qasm',('instructions.txt' if job['algorithm']=='rft' else 'native_dasatom.json')]
    missing=[name for name in required if not (worker/name).exists()]
    row['missing_artifacts']=missing
    if missing:
        row['coverage']='no_complete_trace_available'
        write(destination/'audit.json',row);return row
    try:
        source=read(worker/'result.json')
        normalized_ok=source.get('normalized_sha256')==job['expected_normalized_sha256']==sha(worker/'normalized.qasm')
        worker_ok=record['worker_sha256']==plan['worker_sha256']
        row['frozen_contract_matches']=normalized_ok and worker_ok
        trace=adapt_run(worker,job['algorithm'])
        validation=check_trace(trace);metrics=measure_trace(trace);legacy=compare_legacy(source,metrics)
        original_errors=(source.get('boundary_replay') or {}).get('errors',[])
        saved=(source.get('boundary_replay') or source.get('native_boundary_replay') or {}).get('final_positions')
        final_match=validation['final_positions']=={f'a{q}':p for q,p in saved.items()} if saved is not None else None
        # Explicit load/move/unload interpretation from DasAtom Section III.
        # This is a derived interpretation, never native observed timing.
        policy_trace=adapt_run(worker,job['algorithm'],timing='two_transfer_stages')
        policy_validation=check_trace(policy_trace)
        row.update(coverage='trace_audited',legacy_all_match=legacy['all_match'],
            saved_final_mapping_matches=final_match,evidence_status=validation['status'],
            paper_batch_policy_status=policy_validation['status'],
            paper_batch_violation_codes=sorted({v['code'] for v in policy_validation['violations']}),
            source_boundary_errors=original_errors,
            evidence_violation_codes=sorted({v['code'] for v in validation['violations']}),
            unsupported=validation['coverage']['unsupported'],
            original_register_complete=trace['metadata']['origin']['original_register_complete'],
            eligible_as_physically_validated_baseline=False)
        for name,value in [('evidence_validation',validation),('batch_policy_validation',policy_validation),('metrics',metrics),('legacy_comparison',legacy)]:
            write(destination/(name+'.json'),value)
        # Preserve hashes and all native pointers without duplicating large traces.
        write(destination/'trace_manifest.json',{'format':'audited_trace_manifest.v1',
            'metadata':trace['metadata'],'canonical_events_sha256':fingerprint(trace['events']),
            'event_count':len(trace['events']),'regeneration':'adapt_run(worker, algorithm, timing=evidence)',
            'physical_trace_stored':False})
    except Exception as exc:
        row.update(adapter_error=True,coverage='audit_error',error_type=type(exc).__name__,error=str(exc))
    write(destination/'audit.json',row);return row


def account_jobs(plan,records,omitted,controller_running):
    planned={j['id'] for j in plan['jobs']};attempted={r['job_id'] for r in records}
    omitted_ids={r['job_id'] for r in omitted}
    missing=sorted(planned-attempted-omitted_ids)
    return {'planned_jobs':len(planned),'attempted_jobs':len(attempted),
        'explicitly_omitted_jobs':len(omitted_ids-attempted),'unaccounted_jobs':missing,
        'unknown_job_ids':sorted((attempted|omitted_ids)-planned),
        'all_jobs_accounted':not missing and not ((attempted|omitted_ids)-planned),
        'controller_running':controller_running,
        'first_pass_dataset_audit_complete':not controller_running and not missing and not ((attempted|omitted_ids)-planned)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--follow',action='store_true');parser.add_argument('--poll-seconds',type=float,default=20)
    args=parser.parse_args();study=args.study.resolve();out=args.out.resolve()
    if not out.is_relative_to(ROOT) or out.is_relative_to(study):raise ValueError('Output must be under btp_work and outside the live study')
    if args.poll_seconds<1:raise ValueError('Poll interval too short')
    out.mkdir(parents=True,exist_ok=True)
    import msvcrt
    with (out/'audit.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        kernel=ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype=ctypes.c_void_p
        kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
        kernel.SetPriorityClass.restype=ctypes.c_int
        low_priority=bool(kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000))
        files=list((ROOT/'implementation').rglob('*.py'))+[Path(__file__)]
        hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
        freeze={'plan_sha256':sha(study/'plan.json'),'implementation_sha256':hashes}
        freeze_path=out/'audit_configuration.json'
        if freeze_path.exists() and read(freeze_path)!=freeze:raise ValueError('Audit code/plan changed; use a fresh output version')
        if not freeze_path.exists():write(freeze_path,freeze)
        plan=read(study/'plan.json')
        known={}
        for path in (out/'attempts').glob('*/attempt_*/audit.json'):
            value=read(path);known[(value['job_id'],value['attempt'])]=value
        try:
            while True:
                if any(sha(ROOT/name)!=digest for name,digest in hashes.items()):raise ValueError('Audit code changed during follow')
                added=0
                for record_path in sorted(study.glob('attempts/*/attempt_*/attempt_record.json')):
                    relative=record_path.relative_to(study/'attempts');key=(relative.parts[0],int(relative.parts[1].split('_')[1]))
                    if key in known:
                        if sha(record_path)!=known[key]['record_sha256']:raise ValueError('Previously audited raw record changed')
                        continue
                    destination=out/'attempts'/relative.parent
                    known[key]=audit_one(record_path,destination,plan);added+=1
                    if added%20==0:print(json.dumps({'newly_audited':added,'total':len(known)}),flush=True)
                progress=read(study/'progress.json')
                omitted=read(study/'omitted_repetitions.json') if (study/'omitted_repetitions.json').exists() else []
                running=progress.get('state')=='running';rows=list(known.values())
                accounting=account_jobs(plan,rows,omitted,running)
                counts=lambda key:dict(Counter(str(r.get(key)) for r in rows))
                summary={'updated_utc':now(),'auditor_pid':os.getpid(),'priority_below_normal':low_priority,
                    'state':'following' if running else 'snapshot','audited_attempts':len(rows),
                    'source_statuses':counts('source_status'),'coverage':counts('coverage'),
                    'batch_policy_statuses':counts('paper_batch_policy_status'),
                    'adapter_errors':sum(r['adapter_error'] for r in rows),
                    'legacy_mismatches':sum(r['legacy_all_match'] is False for r in rows),
                    'mapping_mismatches':sum(r['saved_final_mapping_matches'] is False for r in rows),
                    'frozen_contract_mismatches':sum(r.get('frozen_contract_matches') is False for r in rows),
                    'job_accounting':accounting,'phase_01_complete':False,'phase_02_complete':False,
                    'note':'Physical unsupported/invalid outcomes remain excluded; complete first-pass audit does not complete either research phase'}
                write(out/'live_status.json',summary)
                with (out/'audit.csv').open('w',newline='',encoding='utf-8') as stream:
                    fields=['job_id','attempt','algorithm','repetition','source_status','coverage','evidence_status','paper_batch_policy_status','legacy_all_match','saved_final_mapping_matches','adapter_error','record_path']
                    writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
                print(json.dumps({k:v for k,v in summary.items() if k not in ['job_accounting']}),flush=True)
                if accounting['first_pass_dataset_audit_complete']:
                    write(out/'first_pass_final_audit.json',summary);break
                if not args.follow:break
                time.sleep(min(args.poll_seconds,60))
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


if __name__=='__main__':main()
