"""Hand-oracle checks of statistical units and matched-comparison safeguards."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'analysis'),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from idea1_final_analysis import cluster_for, clustered_summary, pair
from phase08_incremental import write


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output required')
    checks=[]
    base=[dict(cluster='a',case_id='a-depth1',relative_E_percent=-10.,control_E=100.,delta_E=-10.),
          dict(cluster='b',case_id='b-depth1',relative_E_percent=10.,control_E=100.,delta_E=10.)]
    unequal=[base[0]]*9+[base[1]]
    small=clustered_summary(base);large=clustered_summary(unequal)
    assert small['equal_generator_mean_relative_E_percent']==large['equal_generator_mean_relative_E_percent']==0.
    assert small['cluster_bootstrap95_low']==large['cluster_bootstrap95_low']==-10.
    assert small['cluster_bootstrap95_high']==large['cluster_bootstrap95_high']==10.
    assert large['summed_E_change_percent']==-8.
    checks.append('Repeated routing observations do not inflate generator weights; aggregate weighting reversal retained')
    a={'family':'qaoa','case_id':'depth2','circuit':{'num_qubits':10},'generator':{'graph_seed':910,'p':2}}
    b={**a,'case_id':'depth4','generator':{'graph_seed':910,'p':4}}
    c={**a,'generator':{'graph_seed':911}}
    assert cluster_for(a)==cluster_for(b)!=cluster_for(c)
    checks.append('QAOA depth variants retain graph identity')
    a={'family':'quantum_volume','case_id':'depth8','circuit':{'num_qubits':10},'generator':{'generator_seed':1010,'depth':8}}
    b={**a,'case_id':'depth16','generator':{'generator_seed':1010,'depth':16}}
    c={**a,'generator':{'seed':1010}}
    assert cluster_for(a)==cluster_for(b)==cluster_for(c)
    checks.append('QV depths and historical seed schema retain generator identity')
    case={'family':'qft','case_id':'qft_5'}
    control={'extended_E':'10','case_id':'qft_5','seed':'42','normalized_sha256':'same','profile_sha256':'p','grid':'11','id':'c'}
    new={**control,'extended_E':'9','id':'n'}
    result=pair(new,control,case,'oracle')
    assert result['delta_E']==-1 and abs(result['relative_E_percent']+10)<1e-12
    for key,bad in [('case_id','other'),('seed','43'),('normalized_sha256','other'),('profile_sha256','other'),('grid','35')]:
        try:pair({**new,key:bad},control,case,'must_fail')
        except AssertionError:pass
        else:raise AssertionError('Unmatched comparison accepted: '+key)
    checks.append('Five mismatch guards and signed paired-effect hand oracle')
    assert clustered_summary([])=={'paired_rows':0}
    checks.append('Empty successful subset remains empty; no invented zero-quality comparison')
    write(out/'result.json',{'status':'ok','groups_passed':len(checks),'checks':checks})
    print('Five analysis acceptance groups passed.')


if __name__=='__main__':main()
