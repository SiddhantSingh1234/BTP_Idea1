"""Cap-only follow-up of every initial timed-out QFT cell; preserve all originals."""
from copy import deepcopy
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from remaining_experiments import verify,read,write,sha


def main():
    original=ROOT/'runs/remaining_experiments_6h_v2'
    out=ROOT/'runs/idea1_completion_followup_v1'
    if out.exists():raise FileExistsError('Follow-up already prepared; do not overwrite')
    manifest=verify(original)
    rows=list(csv.DictReader((original/'results.csv').open(encoding='utf-8-sig')))
    failed={r['id']:r for r in rows if r['status']=='timeout'}
    assert len(failed)==30 and all(r['suite']=='scale' for r in failed.values())
    jobs=[]
    for job in manifest['jobs']:
        if job['id'] not in failed:continue
        fresh=deepcopy(job)
        n=int(job['case_id'].split('_')[-1])
        fresh['timeout']=360 if n<=70 else 480 if n<=80 else 600 if n<=90 else 720
        if job['variant']!='proposed_small':fresh['timeout']=180
        fresh['initial_cap_seconds']=job['timeout']
        fresh['initial_record_path']=failed[job['id']]['record_path']
        jobs.append(fresh)
    budget=read(original/'budget.json')
    remaining=budget['max_seconds']-budget['spent_seconds']
    assert sum(j['timeout'] for j in jobs)+1200<remaining
    out.mkdir(parents=True)
    shutil.copytree(original/'frozen',out/'frozen')
    updated={**manifest,'schema':'idea1_completion.cap_only.v1','prepared_utc':datetime.now(timezone.utc).isoformat(),
        'jobs':jobs,'max_seconds':remaining,'max_worker_cap_sum_seconds':sum(j['timeout'] for j in jobs),
        'followup_of':str(original.relative_to(ROOT)),'original_csv_sha256':sha(original/'results.csv'),
        'selection_rule':'Every initial scale timeout, no selected quality successes; caps changed only, all scientific source/config/input frozen unchanged',
        'cumulative_time_accounting':{'initial_spent_seconds':budget['spent_seconds'],'original_total_budget_seconds':budget['max_seconds']},
        'hypothesis':'Determine whether complete replay succeeds at higher finite caps; preserve original censors and new failures alike'}
    write(out/'manifest.json',updated);write(out/'manifest.sha256.json',{'sha256':sha(out/'manifest.json')})
    write(out/'budget.json',{'spent_seconds':0.,'max_seconds':remaining})
    for name,digest in updated['frozen_files'].items():assert sha(out/'frozen'/name)==digest
    print(json.dumps({'study':str(out),'jobs':len(jobs),'worker_cap_sum_seconds':sum(j['timeout'] for j in jobs),
        'remaining_original_budget_seconds':remaining,'scientific_changes':False}))
if __name__=='__main__':main()
