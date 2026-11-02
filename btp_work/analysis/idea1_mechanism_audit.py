"""Explain null ablations using saved matrices and decisions; no new compilation."""
import argparse
from collections import Counter, defaultdict
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'analysis'),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from phase08_incremental import read, rows, write, csvsave
from audit_idea1_completion import sha, locations


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output required')
    out.mkdir(parents=True)
    study=ROOT/'runs/remaining_experiments_6h_v2';data=rows(study/'results.csv');by={r['id']:r for r in data}
    selected=[];matrix=[];decisions=[];refs={}
    for row in data:
        if row['status']=='reused_quality':
            path=ROOT/row['final_bundle']/'compilation.json';compiled=read(path);refs[row['id']]=compiled
            for index,record in enumerate(compiled['assignment_records']):
                for choice in record.get('selected',[]):
                    selected.append({'reference_id':row['id'],'case_id':row['case_id'],'seed':row['seed'],
                        'assignment_index':index,'row':choice['row'],'column':choice['column'],
                        'missing_anchor_events':choice['missing_anchor_events'],**choice['components']})
    for row in data:
        if row['suite']!='assignment':continue
        parent=refs[row['reference_id']];new=read(ROOT/row['final_bundle']/'compilation.json')
        same=parent['instructions']==new['instructions']
        if row['variant']!='without_conflict': assert same, row['id']
        decisions.append({'id':row['id'],'case_id':row['case_id'],'seed':row['seed'],'term':row['variant'][8:],
                          'instructions_identical':same,'E_identical':float(row['extended_E'])==float(by[row['reference_id']]['extended_E'])})
        if not same:continue
        assert len(parent['assignment_records'])==len(new['assignment_records'])
        for index,(a,b) in enumerate(zip(parent['assignment_records'],new['assignment_records'])):
            if not a.get('selected'):continue
            assert a['pairs']==b['pairs'] and a['candidate_slots']==b['candidate_slots']
            deltas=[x-y for ar,br in zip(a['cost_matrix'],b['cost_matrix']) for x,y in zip(ar,br) if x is not None and y is not None]
            assert deltas
            matrix.append({'id':row['id'],'term':row['variant'][8:],'assignment_index':index,
                'min_cost_change':min(deltas),'max_cost_change':max(deltas),
                'matrix_uniform_shift':max(deltas)-min(deltas)<1e-12,
                'matrix_unchanged':max(abs(x) for x in deltas)<1e-12,
                'qualification':'same realized trajectory only; cost minima include orientation re-selection; not an oracle of all possible traces'})
    summaries=[]
    for term in ['distance','conflict','future','heating','transfer']:
        values=[float(r[term]) for r in selected]
        summaries.append({'term':term,'selected_edges':len(values),'positive_selected_edges':sum(v>1e-12 for v in values),
            'max_selected_component':max(values),'mean_selected_component':sum(values)/len(values)})
    matrixsummary=[]
    for term in ['conflict','future','heating','transfer']:
        group=[r for r in matrix if r['term']==term]
        matrixsummary.append({'term':term,'aligned_same_decision_matrices':len(group),
            'matrix_unchanged':sum(r['matrix_unchanged'] for r in group),
            'matrix_uniform_shift':sum(r['matrix_uniform_shift'] for r in group),
            'nonuniform_change':sum(not r['matrix_uniform_shift'] for r in group),
            'identical_final_instructions':sum(r['instructions_identical'] for r in decisions if r['term']==term),
            'compared_case_seeds':sum(r['term']==term for r in decisions)})
    csvsave(out/'selected_components.csv',selected);csvsave(out/'selected_component_summary.csv',summaries)
    csvsave(out/'aligned_matrix_changes.csv',matrix);csvsave(out/'matrix_summary.csv',matrixsummary);csvsave(out/'instruction_identity.csv',decisions)
    write(out/'verification.json',{'status':'ok','results_sha256':sha(study/'results.csv'),'script_sha256':sha(__file__),
        'reference_case_seeds':len(refs),'selected_component_summary':summaries,'matrix_summary':matrixsummary,
        'scope':'No compiler reruns; records on observed trajectories; null output does not prove a term is irrelevant outside this corpus'})
    print(matrixsummary,flush=True)


if __name__=='__main__':main()
