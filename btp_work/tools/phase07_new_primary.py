"""Only new QAOA/QV primary-baseline cells; completed paper targets are reused."""
import argparse
import csv
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from phase07_extension import read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);args=p.parse_args()
    study=args.study.resolve();protocol=read(study/'protocol.json');out=study/'primary_baselines'
    if out.exists() or not study.is_relative_to(ROOT):raise ValueError('Fresh primary output under btp_work required')
    out.mkdir(parents=True)
    planned=[{'case':case,'seed':seed} for case in protocol['cases'] if case['family'] in ['qaoa','quantum_volume']
             for seed in protocol['quality_seeds']]
    write(out/'protocol.json',{'cells':[{'case':r['case']['case_id'],'seed':r['seed']} for r in planned],
        'worker_sha256':sha(ROOT/'tools/corrected_dasatom_worker.py'),
        'router_sha256':sha(ROOT/'implementation/corrected/dasatom_routes.py'),
        'scorer_sha256':sha(ROOT/'tools/model_comparison_worker.py'),
        'worker_wall_seconds':120,'campaign_wall_seconds':1500,'memory_bytes':4294967296,
        'geometry':'identical declared two-plane hardware/profile as factorial',
        'timing':'DasAtom compile excludes validation/scoring; do not directly compare to factorial end-to-end speed'})
    from run_paper_focus import bounded_job
    from model_comparison_worker import score_uncached
    rows=[];started=time.perf_counter()
    for entry in planned:
        case,seed=entry['case'],entry['seed'];label=case['case_id']+f'__s{seed}'
        job={'target_id':label,'algorithm':'dasatom','family':case['family'],'case':case['case_id'],
            'grid':11,'seed':seed,'expected_normalized_sha256':case['normalized_sha256']}
        if time.perf_counter()-started>1500:record={'status':'unrun_budget'}
        else:record=bounded_job(job,120,output_root=out/'raw',input_path=ROOT/case['normalized_path'])
        row={**{k:job[k] for k in ['target_id','algorithm','family','case','grid','seed']},
            'status':record['status'],'accepted_schedule':False,'attempt_record':record.get('record_path')}
        if record['status']=='ok':
            from implementation.trace.model import load_trace
            worker=ROOT/record['record_path'];worker=worker.parent/'worker'
            raw=read(worker/'result.json')
            target=out/'scored'/label
            target.mkdir(parents=True)
            scored=score_uncached(load_trace(worker/'trace'),{'geometry':case['geometry'],'job':job},
                'dasatom_corrected_common_model',target,raw['corrected_compile_seconds'])
            row.update(scored,seed=seed,attempt_record=record['record_path'])
        rows.append(row)
        write(out/'progress.json',{'completed':len(rows),'planned':len(planned),'last_status':row['status']})
        print(json.dumps({'case':case['case_id'],'seed':seed,'status':row['status']}),flush=True)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (out/'results.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
    write(out/'summary.json',{'planned':len(planned),'rows':len(rows),'accepted':sum(r['accepted_schedule'] for r in rows),
        'wall_seconds':time.perf_counter()-started,'script_sha256':sha(Path(__file__))})
    return 0
if __name__=='__main__':raise SystemExit(main())
