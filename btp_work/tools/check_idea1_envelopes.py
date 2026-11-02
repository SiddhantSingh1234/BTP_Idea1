"""Supplement replay receipts with exact input/register and launcher identities."""
import argparse
import csv
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from audit_idea1_completion import read,write,sha,locations


def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();study=args.study.resolve();out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output required')
    out.mkdir(parents=True);manifest=read(study/'manifest.json');jobs={j['id']:j for j in manifest['jobs']}
    checked=[]
    for row in csv.DictReader((study/'results.csv').open(encoding='utf-8-sig')):
        record=read(ROOT/row['record_path'])
        if row['status']!='reused_quality':
            assert record['worker_sha256']==manifest['frozen_files']['tools/bounded_experiment_worker.py']
            assert record['router_sha256']==manifest['frozen_files']['implementation/budgeted_study/weighting.py']
        if row['status'] not in {'ok','reused_quality'}:continue
        job=jobs[row['id']]
        if not job.get('case_path'):continue
        case=read(ROOT/job['case_path']);path,_=locations(row);schedule=read(path)
        assert row['normalized_sha256']==case['normalized_sha256'],row['id']
        assert schedule['source_trace']['metadata']['circuit']==case['circuit'],row['id']
        checked.append({'id':row['id'],'normalized_sha256':row['normalized_sha256'],
                        'declared_register_qubits':case['circuit']['num_qubits'],'schedule_file_sha256':sha(path)})
    write(out/'verification.json',{'status':'ok','study':str(study.relative_to(ROOT)),
        'results_sha256':sha(study/'results.csv'),'script_sha256':sha(__file__),
        'checked_final_circuit_envelopes':len(checked),'checks':checked,
        'inherited_field_name_note':'router_sha256 stores the weighting helper supplied by this controller; frozen compiler/router sources are separately verified by the 99-file manifest'})
    print('Verified '+str(len(checked))+' exact circuit/register envelopes.',flush=True)


if __name__=='__main__':main()
