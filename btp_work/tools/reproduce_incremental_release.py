"""Small CPU-only release reproduction, runnable from any working directory."""
import argparse
import csv
from importlib import metadata
import json
import os
from pathlib import Path
import site
import sys
import time

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output required under btp_work')
    out.mkdir(parents=True);(out/'tmp').mkdir();(out/'mpl_config').mkdir()
    os.environ['TEMP']=os.environ['TMP']=str(out/'tmp')
    os.environ['MPLCONFIGDIR']=str(out/'mpl_config')
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS']:os.environ[key]='1'
    os.environ['QISKIT_PARALLEL']='FALSE'
    from phase07_extension import factorial_replay_scope,read,write,sha
    from implementation.repair.fixtures import development_cases
    import implementation.repair.search as search
    from implementation.assignment.costs import load_options as assignment_options
    from implementation.lookahead.potential import load_options as parking_options
    from implementation.repair.config import load_options as repair_options
    from implementation.movement_error.profiles import load_profile
    from implementation.movement_error.evaluator import evaluate
    from implementation.validation.full_circuit import verify_original
    from implementation.repair.evaluation import total_E
    from implementation.repair.artifacts import write_bundle
    started=time.perf_counter();case=development_cases()[0]
    profile=load_profile(ROOT/'configs/hardware/extended_no_cooling.json')
    rows=[];proofs=[]
    with factorial_replay_scope():
        for label,lookname,assignname,repairname in [
            ('corrected_control','legacy_exact','sum_distance_expanded','disabled'),
            ('full_small_budget','next_events_h4','composite_bottleneck_expanded','small')]:
            tick=time.perf_counter()
            result=search.repair(case,
                parking_options(ROOT/('configs/variants/lookahead.'+lookname+'.json')),
                assignment_options(ROOT/('configs/variants/assignment.'+assignname+'.json')),profile,
                repair_options(ROOT/('configs/variants/repair.'+repairname+'.json')),seed=42)
            elapsed=time.perf_counter()-tick
            value=result['incumbent'];assert value['evaluation']['accepted_schedule']
            fresh=evaluate(value['evaluation']['schedule'],include_audit=False)
            assert fresh['budget']==value['evaluation']['result']['budget'] and fresh['valid_for_comparison']
            proof=verify_original(value['evaluation']['trace'],ROOT/'benchmarks/current_baseline_v1/raw/fig4_qft/qft_5.qasm')['comparison']
            assert proof['equivalent_up_to_global_phase'] and proof['basis_states']==32
            proofs.append({'variant':label,**proof})
            write_bundle(out/label,value)
            rows.append({'variant':label,'E':total_E(fresh),'makespan_us':fresh['makespan_us'],
                'end_to_end_seconds':elapsed,'candidate_evaluations':result['candidate_evaluations'],
                'accepted_repairs':len(result['accepted_history']),'schedule_sha256':result['final_schedule_sha256']})
    with (out/'comparison.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(6,3.5),layout='constrained')
    ax.bar([r['variant'].replace('_',' ') for r in rows],[r['E'] for r in rows],color=['#8197a1','#176f86'])
    ax.set_ylabel('Complete analytical E (lower is better)');ax.set_title('Fresh-environment QFT5 reproduction')
    fig.savefig(out/'comparison.png',dpi=160);fig.savefig(out/'comparison.svg');plt.close(fig)
    expected={}
    for line in (ROOT/'configs/environment/requirements-py313-win64.txt').read_text().splitlines():
        if '==' in line:
            name,version=line.split('==');expected[name]=version
    actual={name:metadata.version(name) for name in expected}
    assert actual==expected
    summary={'status':'ok','case':case['case_id'],'rows':rows,'semantic_proofs':proofs,
        'working_directory':str(Path.cwd()),'python':sys.executable,'sys_prefix':sys.prefix,
        'user_site_enabled':site.ENABLE_USER_SITE,'all_29_exact_packages_match':actual==expected,
        'package_versions':actual,'environment_lock_sha256':sha(ROOT/'configs/environment/requirements-py313-win64.lock'),
        'script_sha256':sha(Path(__file__)),'wall_seconds':time.perf_counter()-started,
        'independent_replay_performed':True,'figure_generated':True,'command':sys.argv}
    write(out/'verification.json',summary)
    print(json.dumps({'status':'ok','rows':rows,'exact_packages':len(actual),'wall_seconds':summary['wall_seconds']}))
    return 0


if __name__=='__main__':raise SystemExit(main())
