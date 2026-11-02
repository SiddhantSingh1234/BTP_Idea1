"""New circuit-cluster uncertainty, transport budgets, Pareto and sensitivity analysis.

Preserves all original reports. Aggregates timing repeats within an instance and
resamples distinct circuit identities, never treating grids as independent cases.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
import numpy as np


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path):return list(csv.DictReader(Path(path).open(encoding='utf-8-sig',newline='')))
def num(row,key):return float(row[key])
def write(path,data):
    from implementation.repair.artifacts import write as save
    save(path,data)
def csvsave(path,data):
    data=list(data);path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for r in data for k in r))
    with path.open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(data)


def paired_statistics(pairs,reps=10000):
    # Equal circuit weighting first; every circuit's grid observations stay together.
    grouped=defaultdict(list)
    for row in pairs:grouped[(row['family'],row['case'])].append(row)
    values=np.array([statistics.mean(r['relative_E_percent'] for r in group) for group in grouped.values()])
    rng=np.random.default_rng(81031)
    draw=rng.integers(0,len(values),size=(reps,len(values)))
    means=values[draw].mean(axis=1)
    absolute=np.array([sum(r['delta_E'] for r in g) for g in grouped.values()])
    baseline=np.array([sum(r['control_E'] for r in g) for g in grouped.values()])
    aggregate=100*absolute[draw].sum(axis=1)/baseline[draw].sum(axis=1)
    lo,hi=np.quantile(means,[.025,.975]);alo,ahi=np.quantile(aggregate,[.025,.975])
    return {'paired_targets':len(pairs),'independent_circuit_clusters':len(grouped),
        'better':sum(r['delta_E']<-1e-12 for r in pairs),'tie':sum(abs(r['delta_E'])<=1e-12 for r in pairs),
        'worse':sum(r['delta_E']>1e-12 for r in pairs),
        'target_mean_relative_E_percent':statistics.mean(r['relative_E_percent'] for r in pairs),
        'target_median_relative_E_percent':statistics.median(r['relative_E_percent'] for r in pairs),
        'equal_circuit_mean_relative_E_percent':float(values.mean()),
        'circuit_cluster_bootstrap95_low':float(lo),'circuit_cluster_bootstrap95_high':float(hi),
        'summed_E_change_percent':100*sum(r['delta_E'] for r in pairs)/sum(r['control_E'] for r in pairs),
        'summed_E_cluster_bootstrap95_low':float(alo),'summed_E_cluster_bootstrap95_high':float(ahi),
        'bootstrap_replicates':reps,'bootstrap_seed':81031,
        'uncertainty_scope':'conditional stability across this fixed benchmark corpus, not hardware/model calibration or population generalization'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--extension',type=Path);args=ap.parse_args();out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh analysis output required under btp_work')
    out.mkdir(parents=True)
    sources={4:ROOT/'runs/phase04_matched_benchmark_v2/results.csv',
             5:ROOT/'runs/phase05_matched_benchmark_v1/results.csv',
             6:ROOT/'runs/phase06_matched_benchmark_v2/results.csv',
             3:ROOT/'runs/phase03_matched_benchmark_v1/results.csv'}
    data={k:rows(v) for k,v in sources.items()}
    for source,record in read(ROOT/'reports/phase_07/reused_studies.json').items():
        assert sha(ROOT/source)==record['sha256'],source
    for phase,table in data.items():
        assert len({(r['target_id'],r['variant']) for r in table})==len(table)
        assert all(r['status']=='ok' and r['accepted_schedule'].lower()=='true' for r in table)
    by={phase:{(r['target_id'],r['variant']):r for r in table} for phase,table in data.items()}
    p4,p5,p6=by[4],by[5],by[6]
    targets=sorted({r['target_id'] for r in data[6]})
    comparisons=[];pairs=[]
    definitions=[('lookahead_h1',4,'next_events_h1',4,'legacy_exact'),
        ('lookahead_h4',4,'next_events_h4',4,'legacy_exact'),
        ('lookahead_h8',4,'next_events_h8',4,'legacy_exact'),
        ('assignment_objective_fixed_candidates',5,'composite_bottleneck_expanded',5,'sum_distance_expanded'),
        ('candidate_expansion_fixed_distance',5,'sum_distance_expanded',5,'sum_distance'),
        ('small_repair_matched',6,'composite_bottleneck_expanded__small',6,'composite_bottleneck_expanded__disabled'),
        ('standard_repair_matched',6,'composite_bottleneck_expanded__standard',6,'composite_bottleneck_expanded__disabled'),
        ('final_vs_original',6,'composite_bottleneck_expanded__standard',5,'original_phase3')]
    for label,phase,variant,controlphase,control in definitions:
        selected=[]
        for target in targets:
            a,b=by[phase][target,variant],by[controlphase][target,control]
            for field in ['normalized_sha256','geometry_sha256','profile_sha256']:assert a[field]==b[field],(label,target,field)
            e,ce=num(a,'extended_E'),num(b,'extended_E')
            row={'comparison':label,'target_id':target,'family':a['family'],'case':a['case'],'grid':int(a['grid']),
                'E':e,'control_E':ce,'delta_E':e-ce,'relative_E_percent':100*(e/ce-1)}
            selected.append(row);pairs.append(row)
        comparisons.append({'comparison':label,**paired_statistics(selected)})
        for family in sorted({r['family'] for r in selected}):
            comparisons.append({'comparison':label,'subset':family,**paired_statistics([r for r in selected if r['family']==family])})
    csvsave(out/'clustered_comparisons.csv',comparisons);csvsave(out/'paired_effects.csv',pairs)

    transport=[];pareto=[];cost=[];sens=[];crossings=[];grids=[]
    for target in targets:
        original=p5[target,'original_phase3'];final=p6[target,'composite_bottleneck_expanded__standard']
        native=num(original,'E_native_gate');baseE=num(original,'extended_E');finalE=num(final,'extended_E')
        assert abs(native-num(final,'E_native_gate'))<1e-10
        reducible=baseE-native
        transport.append({'target_id':target,'family':original['family'],'case':original['case'],'grid':int(original['grid']),
            'native_gate_E':native,'original_total_E':baseE,'final_total_E':finalE,'original_transport_sensitive_E':reducible,
            'native_gate_share':native/baseE,'total_E_reduction_percent':100*(baseE-finalE)/baseE,
            'transport_sensitive_E_reduction_percent':100*(baseE-finalE)/reducible if reducible else 0.})
        choices=[p6[target,v] for v in sorted({r['variant'] for r in data[6]}) if not v.endswith('__zero')]
        for choice in choices:
            dominated=any(num(other,'extended_E')<=num(choice,'extended_E')+1e-12 and
                num(other,'end_to_end_compile_validate_repair_seconds')<=num(choice,'end_to_end_compile_validate_repair_seconds') and
                (num(other,'extended_E')<num(choice,'extended_E')-1e-12 or
                 num(other,'end_to_end_compile_validate_repair_seconds')<num(choice,'end_to_end_compile_validate_repair_seconds'))
                for other in choices if other is not choice)
            pareto.append({'target_id':target,'family':choice['family'],'case':choice['case'],'grid':choice['grid'],
                'variant':choice['variant'],'E':num(choice,'extended_E'),
                'total_seconds':num(choice,'end_to_end_compile_validate_repair_seconds'),'dominated':dominated,
                'scope':'six fixed observed Phase06 choices, same end-to-end scope; single noisy timing sample'})
        for policy in ['sum_distance','composite_bottleneck_expanded']:
            disabled=p6[target,policy+'__disabled'];small=p6[target,policy+'__small'];standard=p6[target,policy+'__standard']
            for budget,current in [('small',small),('standard',standard)]:
                gain=num(disabled,'extended_E')-num(current,'extended_E')
                dt=num(current,'end_to_end_compile_validate_repair_seconds')-num(disabled,'end_to_end_compile_validate_repair_seconds')
                cost.append({'target_id':target,'family':current['family'],'case':current['case'],'grid':current['grid'],
                    'policy':policy,'budget':budget,'gain_E':gain,'extra_seconds':dt,
                    'E_saved_per_extra_second':gain/dt if dt>0 else None,
                    'time_ratio_same_scope':num(current,'end_to_end_compile_validate_repair_seconds')/num(disabled,'end_to_end_compile_validate_repair_seconds'),
                    'evaluations':int(current['candidate_evaluations']),'accepted_repairs':int(current['accepted_repairs'])})
        # Fixed-trace model sensitivity: no layout, algorithm or trajectory changes.
        # Transfer and T2 are exactly separable for these no-cooling schedules.
        for transfer in [.9999,.999,.99]:
            for t2 in [150000.,1500000.,15000000.]:
                adjusted={}
                for label,row in [('original',original),('final',final),('dasatom',by[3][target.replace('__rft__7_dynamic_slot_01q_move__native','__dasatom__standalone__native'),'original_phase3'])]:
                    ntransfer=num(row,'E_transfer')/-math.log(.999)
                    assert abs(ntransfer-round(ntransfer))<1e-6
                    adjusted[label]=num(row,'extended_E')-num(row,'E_transfer')-num(row,'E_decoherence')+round(ntransfer)*-math.log(transfer)+num(row,'E_decoherence')*1500000/t2
                sens.append({'target_id':target,'family':original['family'],'case':original['case'],'grid':original['grid'],
                    'f_transfer':transfer,'T2_us':t2,**adjusted,'final_minus_original_E':adjusted['final']-adjusted['original'],
                    'final_minus_dasatom_E':adjusted['final']-adjusted['dasatom'],
                    'scope':'fixed decisions and physical timings; scorer sensitivity only, no replanning'})
        def components(row):
            return (num(row,'extended_E')-num(row,'E_transfer')-num(row,'E_decoherence'),
                    num(row,'E_transfer')/-math.log(.999),num(row,'E_decoherence')*1500000)
        a,b=components(final),components(original)
        dconst,dtrans,dexpo=[x-y for x,y in zip(a,b)]
        denominator=dconst+dtrans*-math.log(.999)
        crossover=-dexpo/denominator if abs(denominator)>1e-15 else -1
        crossings.append({'target_id':target,'case':original['case'],'grid':original['grid'],
            'coherence_crossover_T2_us':crossover if crossover>0 else None,
            'delta_transfer_atom_events':dtrans,'delta_weighted_exposure_us':dexpo,
            'delta_other_E':dconst,'interpretation':'positive root solves equal final/original E at fixed transfer=.999; no root means no positive crossing'})
    csvsave(out/'transport_budget.csv',transport);csvsave(out/'repair_cost_effectiveness.csv',cost)
    csvsave(out/'pareto_choices.csv',pareto);csvsave(out/'fixed_trace_sensitivity.csv',sens);csvsave(out/'ranking_crossovers.csv',crossings)
    sensitivity=[]
    for ft,t2 in sorted({(r['f_transfer'],r['T2_us']) for r in sens}):
        selected=[r for r in sens if r['f_transfer']==ft and r['T2_us']==t2]
        sensitivity.append({'f_transfer':ft,'T2_us':t2,'targets':len(selected),
            'final_better_than_original':sum(r['final_minus_original_E']<-1e-12 for r in selected),
            'final_worse_than_original':sum(r['final_minus_original_E']>1e-12 for r in selected),
            'final_better_than_dasatom':sum(r['final_minus_dasatom_E']<-1e-12 for r in selected),
            'summed_E_change_percent':100*(sum(r['final'] for r in selected)/sum(r['original'] for r in selected)-1)})
    csvsave(out/'sensitivity_summary.csv',sensitivity)
    # Matched same-circuit grids remove the different grid-family composition.
    grouped=defaultdict(dict)
    for r in transport:grouped[(r['family'],r['case'])][r['grid']]=r
    for (family,case),g in grouped.items():
        if 11 in g and 35 in g:
            grids.append({'family':family,'case':case,'grid11_original_E':g[11]['original_total_E'],
                'grid35_original_E':g[35]['original_total_E'],'grid35_minus_grid11_E':g[35]['original_total_E']-g[11]['original_total_E'],
                'grid11_final_gain_percent':g[11]['total_E_reduction_percent'],'grid35_final_gain_percent':g[35]['total_E_reduction_percent']})
    csvsave(out/'matched_grid_effect.csv',grids)
    # Independent full evaluator check of the closed-form fixed-trace transformation.
    from implementation.movement_error.profiles import validate_profile
    from implementation.movement_error.schedule import make_schedule
    from implementation.movement_error.evaluator import evaluate
    base=next(r for r in data[6] if r['case']=='qft_5' and r['grid']=='11' and r['variant']=='composite_bottleneck_expanded__standard')
    schedule=read(ROOT/base['final_bundle_directory']/'schedule.json')
    profile=deepcopy(schedule['profile']);profile['noise']['f_transfer']=.99;profile['exposure']['T2_us']=150000.
    modified=make_schedule(schedule['source_trace'],validate_profile(profile),'retime')
    fresh=evaluate(modified,include_audit=False)
    prediction=next(r['final'] for r in sens if r['target_id']==base['target_id'] and r['f_transfer']==.99 and r['T2_us']==150000.)
    assert fresh['status']=='ok' and fresh['valid_for_comparison'] and abs(fresh['budget']['total_E']-prediction)<1e-10

    factorial=[];extensionsummary={}
    if args.extension:
        ext=rows(args.extension/'campaign/results.csv')
        valid=[r for r in ext if r['status']=='ok']
        quality=[r for r in valid if r['quality_sample'].lower()=='true']
        table={(r['case'],int(r['seed']),int(r['L']),int(r['A']),int(r['R'])):num(r,'E') for r in quality}
        for case,seed in sorted({(r['case'],int(r['seed'])) for r in quality}):
            if not all((case,seed,L,A,R) in table for L,A,R in itertools_product()):continue
            cube={(L,A,R):table[case,seed,L,A,R] for L,A,R in itertools_product()}
            # Contrasts use 0/1 finite differences, averaged over untouched factors.
            baseline=cube[0,0,0]
            main={name:statistics.mean(cube[tuple(list(x)[:i]+[1]+list(x)[i+1:])]-cube[tuple(list(x)[:i]+[0]+list(x)[i+1:])]
                    for x in itertools_product() if x[i]==0) for i,name in enumerate(['L','A','R'])}
            interactions={}
            for i,j,name in [(0,1,'LA'),(0,2,'LR'),(1,2,'AR')]:
                values=[]
                for x in itertools_product():
                    if x[i] or x[j]:continue
                    def get(a,b):
                        y=list(x);y[i]=a;y[j]=b;return cube[tuple(y)]
                    values.append(get(1,1)-get(1,0)-get(0,1)+get(0,0))
                interactions[name]=statistics.mean(values)
            triple=sum((1 if sum(x)%2 else -1)*cube[x] for x in itertools_product())
            family=next(r['family'] for r in quality if r['case']==case)
            factorial.append({'case':case,'family':family,'seed':seed,'baseline_E':baseline,
                'full_E':cube[1,1,1],'full_relative_E_percent':100*(cube[1,1,1]/baseline-1),
                **{k+'_effect_E':v for k,v in main.items()},**{k+'_interaction_E':v for k,v in interactions.items()},'LAR_interaction_E':triple})
        csvsave(out/'factorial_effects.csv',factorial)
        fam=[]
        for family in sorted({r['family'] for r in factorial}):
            selected=[r for r in factorial if r['family']==family]
            fam.append({'family':family,'circuits':len({r['case'] for r in selected}),'paired_circuit_seeds':len(selected),
                **{key:statistics.mean(r[key] for r in selected) for key in selected[0] if key.endswith('_E') or key.endswith('_percent')}})
        csvsave(out/'factorial_by_family.csv',fam)
        repeats=[]
        timed=defaultdict(list)
        for r in valid:
            if r['seed']=='42':timed[r['case'],r['variant']].append(num(r,'total_seconds'))
        for (case,variant),v in timed.items():
            repeats.append({'case':case,'variant':variant,'samples':len(v),'median_seconds':statistics.median(v),
                'CV_percent':100*statistics.stdev(v)/statistics.mean(v) if len(v)>1 else None})
        csvsave(out/'timing_repeat_variability.csv',repeats)
        extensionsummary={'planned_rows':len(ext),'accepted_rows':len(valid),'quality_rows':len(quality),
            'timing_only_rows':len(valid)-len(quality),'complete_factorial_circuit_seeds':len(factorial),'families':fam}

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    summary=[r for r in comparisons if 'subset' not in r]
    labels=[r['comparison'].replace('_',' ') for r in summary]
    means=np.array([r['equal_circuit_mean_relative_E_percent'] for r in summary])
    lower=np.array([r['circuit_cluster_bootstrap95_low'] for r in summary]);upper=np.array([r['circuit_cluster_bootstrap95_high'] for r in summary])
    ax.errorbar(means,np.arange(len(means)),xerr=[means-lower,upper-means],fmt='o',color='#186b8a',capsize=3)
    ax.set_yticks(range(len(means)),labels);ax.axvline(0,color='#999',lw=1)
    ax.set_xlabel('Equal-circuit mean change in E (%) with circuit-cluster bootstrap 95% interval')
    ax.set_title('27 circuits, not 66 independent grid targets');ax.invert_yaxis()
    export(fig,out,'cluster_uncertainty')
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for policy,color in [('sum_distance','#e5943a'),('composite_bottleneck_expanded','#186b8a')]:
        c=[r for r in cost if r['policy']==policy and r['budget']=='standard']
        axes[0].scatter([r['extra_seconds'] for r in c],[r['gain_E'] for r in c],s=20,alpha=.7,label=policy,color=color)
    axes[0].set_xscale('symlog',linthresh=.1);axes[0].set_xlabel('Additional repair seconds vs disabled (same timer scope)');axes[0].set_ylabel('Absolute E saved');axes[0].legend(fontsize=7)
    axes[1].scatter([r['total_E_reduction_percent'] for r in transport],[r['transport_sensitive_E_reduction_percent'] for r in transport],c=[r['grid'] for r in transport],cmap='viridis',s=25)
    axes[1].axhline(0,color='#aaa',lw=.6);axes[1].axvline(0,color='#aaa',lw=.6)
    axes[1].set_xlabel('Total E reduction (%)');axes[1].set_ylabel('Transport-sensitive E reduction (%)')
    export(fig,out,'repair_economics_and_error_floor')
    fig,ax=plt.subplots(figsize=(7.5,4),layout='constrained')
    matrix=np.array([[next(r['summed_E_change_percent'] for r in sensitivity if r['f_transfer']==ft and r['T2_us']==t2) for t2 in [150000.,1500000.,15000000.]] for ft in [.9999,.999,.99]])
    im=ax.imshow(matrix,cmap='RdBu_r');ax.set_xticks(range(3),['0.15','1.5','15']);ax.set_yticks(range(3),['0.9999','0.999','0.99'])
    for (i,j),value in np.ndenumerate(matrix):ax.text(j,i,f'{value:+.2f}%',ha='center',va='center')
    ax.set_xlabel('T2 (seconds)');ax.set_ylabel('Per-atom transfer fidelity');ax.set_title('Final vs original: fixed-trace summed E change');fig.colorbar(im,ax=ax,label='Change in E (%)')
    export(fig,out,'fixed_trace_model_sensitivity')
    if factorial:
        fig,ax=plt.subplots(figsize=(8.5,4.2),layout='constrained')
        families=extensionsummary['families'];names=['L_effect_E','A_effect_E','R_effect_E','LA_interaction_E','LR_interaction_E','AR_interaction_E','LAR_interaction_E']
        mat=np.array([[100*r[k]/r['baseline_E'] for k in names] for r in families])
        limit=max(abs(mat).max(),.01);im=ax.imshow(mat,cmap='RdBu_r',vmin=-limit,vmax=limit,aspect='auto')
        ax.set_xticks(range(7),['L','A','R','L×A','L×R','A×R','L×A×R']);ax.set_yticks(range(len(families)),[r['family'] for r in families])
        ax.set_title('New four-family factorial: effects normalized by mean baseline E')
        for (i,j),value in np.ndenumerate(mat):ax.text(j,i,f'{value:+.2f}',ha='center',va='center',fontsize=8,
            color='white' if abs(value)>limit*.55 else '#111111')
        fig.colorbar(im,ax=ax,label='E contrast / baseline E (%)');export(fig,out,'factorial_interactions')
    totalbase=sum(r['original_total_E'] for r in transport);totalfinal=sum(r['final_total_E'] for r in transport)
    dynamic=sum(r['original_transport_sensitive_E'] for r in transport)
    result={'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources.values()},
        'analysis_script_sha256':sha(Path(__file__)),'comparisons':comparisons,
        'native_gate_share_of_summed_original_E':sum(r['native_gate_E'] for r in transport)/totalbase,
        'final_summed_total_E_reduction_percent':100*(totalbase-totalfinal)/totalbase,
        'final_summed_transport_sensitive_E_reduction_percent':100*(totalbase-totalfinal)/dynamic,
        'observed_phase06_dominated_choices':sum(r['dominated'] for r in pareto),'observed_phase06_choices':len(pareto),
        'standard_composite_dominated_targets':sum(r['dominated'] for r in pareto if r['variant']=='composite_bottleneck_expanded__standard'),
        'sensitivity':sensitivity,'sensitivity_formula_independently_replayed':True,
        'positive_T2_crossovers':sum(r['coherence_crossover_T2_us'] is not None for r in crossings),
        'extension':extensionsummary,'command':sys.argv}
    write(out/'summary.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','comparisons','sensitivity','extension']}))


def itertools_product():
    import itertools
    return list(itertools.product([0,1],repeat=3))


def export(fig,out,name):
    import matplotlib.pyplot as plt
    for ext in ['png','svg','pdf']:fig.savefig(out/(name+'.'+ext),dpi=180)
    plt.close(fig)


if __name__=='__main__':main()
