"""Paired new QAOA/QV primary comparisons and explicit semantic checks."""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from phase07_extension import read,write,sha
from implementation.validation.full_circuit import verify_original
from implementation.trace.model import load_trace,fingerprint
from implementation.movement_error.evaluator import evaluate


def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();study=a.study.resolve();out=a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output under btp_work required')
    out.mkdir(parents=True)
    primary=list(csv.DictReader((study/'primary_baselines/results.csv').open(encoding='utf-8-sig')))
    ext=list(csv.DictReader((study/'campaign/results.csv').open(encoding='utf-8-sig')))
    table={(r['case'],r['seed']):r for r in ext if r['quality_sample'].lower()=='true' and r['variant']=='L1A1R1'}
    cases={c['case_id']:c for c in read(study/'protocol.json')['cases']}
    pairs=[];proofs=[]
    for d in primary:
        r=table[d['case'],d['seed']]
        if d['status']!='ok' or d['accepted_schedule'].lower()!='true':
            pairs.append({'case':d['case'],'seed':d['seed'],'family':d['family'],'status':d['status']});continue
        assert d['normalized_sha256']==r['normalized_sha256']
        ds=read(ROOT/d['output']/'schedule.json');rs=read(ROOT/r['final_bundle_directory']/'schedule.json')
        assert ds['profile_sha256']==rs['profile_sha256']
        assert ds['source_trace']['metadata']['hardware_sha256']==rs['source_trace']['metadata']['hardware_sha256']
        score=evaluate(ds,include_audit=False)
        assert score['status']=='ok' and score['valid_for_comparison']
        assert score['budget']['total_E']==float(d['extended_E'])
        e,base=float(r['E']),float(d['extended_E'])
        pairs.append({'case':d['case'],'seed':d['seed'],'family':d['family'],'status':'ok','full_E':e,'dasatom_E':base,
            'delta_E':e-base,'relative_E_percent':100*(e/base-1),'full_makespan_us':float(r['makespan_us']),
            'dasatom_makespan_us':float(d['extended_makespan_us']),
            'full_end_to_end_seconds':float(r['total_seconds']),'dasatom_compile_only_seconds':float(d['compile_seconds']),
            'strict_cross_algorithm_timing_comparison':False})
        if d['seed']=='42' and cases[d['case']]['circuit']['num_qubits']==6:
            proof=verify_original(load_trace(ROOT/d['output']/'trace'),ROOT/cases[d['case']]['original_path'])['comparison']
            assert proof['equivalent_up_to_global_phase']
            proofs.append({'case':d['case'],'algorithm':'dasatom_corrected',**proof})
    fields=list(dict.fromkeys(k for row in pairs for k in row))
    with (out/'new_primary_pairs.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(pairs)
    groups=[]
    for family in ['qaoa','quantum_volume']:
        group=[r for r in pairs if r['family']==family and r['status']=='ok']
        groups.append({'family':family,'planned':sum(r['family']==family for r in pairs),'paired':len(group),
            'circuits':len({r['case'] for r in group}), 'better':sum(r['delta_E']<-1e-12 for r in group),
            'tie':sum(abs(r['delta_E'])<=1e-12 for r in group),'worse':sum(r['delta_E']>1e-12 for r in group),
            'mean_relative_E_percent':statistics.mean(r['relative_E_percent'] for r in group) if group else None})
    parking=[]
    for case in cases.values():
        if case['family']!='quantum_volume':continue
        for seed in [41,42,43,44,45]:
            sample=next(r for r in ext if r['case']==case['case_id'] and r['seed']==str(seed) and r['repeat']=='0' and r['variant']=='L1A1R0')
            compilation=read(ROOT/sample['final_bundle_directory']/'compilation.json')
            parking.append({'case':case['case_id'],'seed':seed,'parking_calls':compilation['statistics']['parking_calls'],
                            'eviction_calls':compilation['statistics']['eviction_calls']})
    assert all(r['parking_calls']==r['eviction_calls']==0 for r in parking)
    write(out/'summary.json',{'groups':groups,'semantic_proofs':proofs,'qv_parking_mechanism':parking,
        'all_new_primary_outputs_independently_replayed':True,'source_sha256':{
            'primary_results':sha(study/'primary_baselines/results.csv'),'factorial_results':sha(study/'campaign/results.csv')},
        'script_sha256':sha(Path(__file__))})
    print(json.dumps({'groups':groups,'semantic_proofs':len(proofs),'qv_zero_parking_cases':len(parking)}))
if __name__=='__main__':main()
