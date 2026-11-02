"""Audit a read-only snapshot of completed attempts; never writes to the study."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from implementation.adapters.upstream import adapt_run
from implementation.metrics.legacy import measure_trace
from implementation.trace.model import save_trace
from implementation.validation.checker import check_trace


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--limit',type=int,default=24)
    args=parser.parse_args();out=args.out.resolve();study=args.study.resolve()
    if not out.is_relative_to(ROOT) or out.is_relative_to(study):raise ValueError('Audit output must be under btp_work, outside the live study')
    if out.exists():raise FileExistsError('Audit output already exists')
    out.mkdir(parents=True);started=time.time()
    records=sorted(study.glob('attempts/*/attempt_*/attempt_record.json'))
    # Prefer first repetitions, cover distinct method/grid/family/outcome strata,
    # then add more source cases. Paths are fixed before reading any worker files.
    strata={};remaining=[]
    for record_path in records:
        record=json.loads(record_path.read_text(encoding='utf-8'))
        worker=record_path.parent/'worker'
        if not (worker/'result.json').exists():continue
        source=json.loads((worker/'result.json').read_text(encoding='utf-8'))
        if not (worker/'normalized.qasm').exists():continue
        job=record.get('job',{})
        if job.get('repetition',1)!=1:continue
        key=(source.get('algorithm'),job.get('family'),job.get('grid'),source.get('status'))
        item=(record_path,record,source)
        if key not in strata:strata[key]=item
        else:remaining.append(item)
    selected=list(strata.values())+remaining
    if args.limit>0:selected=selected[:args.limit]
    rows=[]
    for record_path,record,source in selected:
        worker=record_path.parent/'worker';name=record_path.parent.parent.name
        target=out/'attempts'/name
        row={'job_id':name,'source_status':source.get('status'),'algorithm':source['algorithm'],
            'source_boundary_errors':json.dumps((source.get('boundary_replay') or {}).get('errors',[])),
            'record_path':str(record_path.relative_to(ROOT)),
            'record_sha256':hashlib.sha256(record_path.read_bytes()).hexdigest()}
        try:
            trace=adapt_run(worker,source['algorithm']);save_trace(target/'trace',trace)
            validation=check_trace(trace);metrics=measure_trace(trace)
            native=source.get('native_metrics',{})
            ref=native.get('Fidelity (DasAtom Model)') if source['algorithm']=='rft' else (native.get('native_score') or [None,None])[1]
            score_match=ref is not None and abs(metrics['legacy']['fidelity_proxy']-ref)<=1e-12
            final_ref=(source.get('boundary_replay') or source.get('native_boundary_replay') or {}).get('final_positions')
            mapping_match=validation['final_positions']=={f'a{q}':p for q,p in final_ref.items()} if final_ref is not None else None
            for filename,result in [('validation.json',validation),('metrics.json',metrics)]:
                (target/filename).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            row.update(validator_status=validation['status'],structural_valid=validation['structural_valid'],
                violation_codes=','.join(sorted({v['code'] for v in validation['violations']})),
                unsupported=','.join(validation['coverage']['unsupported']),legacy_score_matches=score_match,
                final_mapping_matches_saved_replay=mapping_match,
                required_CZ=metrics['required_CZ'],observed_CZ=metrics['observed_CZ'],
                original_register_complete=trace['metadata']['origin']['original_register_complete'])
        except Exception as exc:
            row.update(validator_status='adapter_error',structural_valid=False,violation_codes=type(exc).__name__+': '+str(exc))
            target.mkdir(parents=True,exist_ok=True)
            (target/'adapter_error.json').write_text(json.dumps({'error':str(exc),'type':type(exc).__name__},indent=2)+'\n',encoding='utf-8')
        rows.append(row)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (out/'audit.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    summary={'scope':'completed_attempt_snapshot','full_baseline_audit_complete':False,
        'completed_records_at_snapshot':len(records),'selected':len(rows),
        'statuses':dict(Counter(r['validator_status'] for r in rows)),
        'violation_counts':dict(Counter(c for r in rows for c in r.get('violation_codes','').split(',') if c)),
        'legacy_score_mismatches':sum(r.get('legacy_score_matches') is False for r in rows),
        'final_mapping_mismatches':sum(r.get('final_mapping_matches_saved_replay') is False for r in rows),
        'source_statuses':dict(Counter(r['source_status'] for r in rows)),
        'wall_seconds':time.time()-started,'command':sys.argv,
        'implementation_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'implementation').rglob('*.py')}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='implementation_sha256'}))


if __name__=='__main__':main()
