"""Audited paper, Phase03-model and matched Phase04 analysis. No compiler reruns."""
import argparse,csv,hashlib,json,math,statistics,sys,time
from collections import Counter
from decimal import Decimal
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
import model_comparison as service

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def rows(p):return list(csv.DictReader(Path(p).open(newline='',encoding='utf-8-sig')))
def csvwrite(p,data):
    fields=list(dict.fromkeys(k for r in data for k in r))
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
def med(v):return statistics.median(v)
def fmt(v):
    if v is None:return '-'
    if isinstance(v,int):return str(v)
    return f'{v:.5g}' if isinstance(v,float) else str(v)
def table(data,columns):
    return '| '+' | '.join(label for key,label in columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+'\n'.join('| '+' | '.join(fmt(r.get(key)) for key,label in columns)+' |' for r in data)+'\n'
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-280)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Use fresh output under btp_work')
    audit1=ROOT/'reports/phase_01/final_dataset_audit_02';audit3=ROOT/'reports/phase_03/full_dataset_audit_02'
    assert read(audit1/'summary.json')['passed'] and read(audit3/'summary.json')['passed']
    lock=None
    while lock is None:
        lock=service.acquire(ROOT/'runs/model_comparison_execution.lock')
        if lock is None:print('Waiting for timed comparison before final analysis',flush=True);time.sleep(3)
    try:
        s1=ROOT/'runs/phase01_frozen_baseline_v1';s3=ROOT/'runs/phase03_matched_benchmark_v1';s4=ROOT/'runs/phase04_matched_benchmark_v2'
        m1=service.baseline_service.verify(s1,runtime=True);m3=service.verify(s3,runtime=True);m4=service.verify(s4,runtime=True)
        assert read(s4/'summary.json')['matrix_complete']
        a=rows(s1/'results.csv');b=rows(s3/'results.csv');c=rows(s4/'results.csv')
        assert len(a)==len(b)==132 and len(c)==396
        by1={r['target_id']:r for r in a};by3={r['target_id']:r for r in b}
        reference_dir=ROOT/'reports/phase_01/paper_reference_01';reference=rows(reference_dir/'paper_reference.csv')
        assert sha(reference_dir/'paper_reference.csv')==read(reference_dir/'verification.json')['reference_sha256']
        paper={(r['family'],r['case'],int(r['grid']),r['algorithm']):r for r in reference}
        out.mkdir(parents=True);comp=[];stats=[];changes=[];phase4=[]
        terms=['E_native_gate','E_transfer','E_heating_gate','E_movement_loss','E_cooling_gate','E_decoherence']
        for r in a:
            ref=paper[(r['family'],r['case'],int(r['grid']),r['algorithm'])]
            d={**r,**{k:v for k,v in ref.items() if k.startswith('paper_') or k.startswith('source_')}}
            d.update(compile_measured_to_paper=float(r['compile_seconds'])/float(ref['paper_compile_seconds']),
                movement_delta=int(r['movement_batches'])-int(ref['paper_movement_batches']),
                movement_exact_match=int(r['movement_batches'])==int(ref['paper_movement_batches']),
                fidelity_delta_pp=100*(float(r['legacy_fidelity'])-float(ref['paper_fidelity'])),
                fidelity_ratio=float(r['legacy_fidelity'])/float(ref['paper_fidelity']),
                legacy_E_delta=-math.log(float(r['legacy_fidelity']))+math.log(float(ref['paper_fidelity'])),
                exact_manuscript_configuration_established=False,unqualified_algorithm_speedup_claimed=False)
            if ref['source_kind']=='printed_Table_II':
                tolerance=.5*10**Decimal(ref['paper_fidelity_literal']).as_tuple().exponent
                match=abs(float(r['legacy_fidelity'])-float(ref['paper_fidelity']))<=tolerance+1e-15
            else:match=abs(math.log10(float(r['legacy_fidelity']))-math.log10(float(ref['paper_fidelity'])))<=float(ref['fidelity_log10_uncertainty'])
            d['fidelity_within_reference_precision']=match;runtime_match=True
            if ref['paper_runtime_us']:
                d['runtime_measured_to_paper']=float(r['runtime_us'])/float(ref['paper_runtime_us'])
                runtime_match=abs(float(r['runtime_us'])-float(ref['paper_runtime_us']))<=float(ref['runtime_abs_uncertainty'])
            d['quality_numerically_consistent']=d['movement_exact_match'] and match and runtime_match
            d['verdict']='quality_numerically_consistent_configuration_unresolved' if d['quality_numerically_consistent'] else 'numerical_mismatch_configuration_unresolved'
            comp.append(d)
        for algorithm in ['rft','dasatom']:
            for grid in [11,20,35]:
                group=[r for r in a if r['algorithm']==algorithm and int(r['grid'])==grid]
                d={'algorithm':algorithm,'grid':grid,'targets':len(group)}
                for key in ['compile_seconds','runtime_us','movement_batches','legacy_fidelity']:
                    values=[float(r[key]) for r in group]
                    for label,value in [('min',min(values)),('median',med(values)),('max',max(values))]:d[key+'_'+label]=value
                d['sum_target_compile_seconds']=sum(float(r['compile_seconds']) for r in group)
                d['timing_samples']=sum(int(r['compile_sample_count']) for r in group)
                d['median_compile_cv']=med([float(r['compile_cv']) for r in group]) if algorithm=='rft' else None
                stats.append(d)
        for r in b:
            original=by1[r['target_id']]
            assert close(r['compile_seconds'],original['compile_seconds']) and int(r['routing_batches'])==int(original['movement_batches'])
            d={k:r[k] for k in ['target_id','algorithm','family','case','grid','profile_sha256','geometry_sha256']}
            d.update(original_fidelity=float(original['legacy_fidelity']),extended_fidelity=float(r['extended_fidelity']),
                fidelity_retention=float(r['extended_fidelity'])/float(original['legacy_fidelity']),
                fidelity_delta_pp=100*(float(r['extended_fidelity'])-float(original['legacy_fidelity'])),
                original_E=-math.log(float(original['legacy_fidelity'])),extended_E=float(r['extended_E']),
                delta_E=float(r['extended_E'])+math.log(float(original['legacy_fidelity'])),
                original_runtime_us=float(original['runtime_us']),extended_runtime_us=float(r['extended_makespan_us']),
                runtime_ratio=float(r['extended_makespan_us'])/float(original['runtime_us']),compilation_unchanged=True,movement_choices_unchanged=True)
            for term in terms:d[term]=float(r[term])
            assert close(sum(d[t] for t in terms),d['extended_E'])
            for term in terms:
                d[term+'_share']=d[term]/d['extended_E'];d['fidelity_without_'+term]=math.exp(-(d['extended_E']-d[term]))
            changes.append(d)
        model_summary=[]
        for algorithm in ['rft','dasatom']:
            group=[r for r in changes if r['algorithm']==algorithm]
            d={'algorithm':algorithm,'targets':len(group),'fidelity_decreases':sum(r['fidelity_retention']<1 for r in group),
                'median_fidelity_retention':med([r['fidelity_retention'] for r in group]),'median_runtime_ratio':med([r['runtime_ratio'] for r in group]),
                'median_delta_E':med([r['delta_E'] for r in group]),'nonzero_movement_loss_targets':sum(r['E_movement_loss']>0 for r in group)}
            total=sum(r['extended_E'] for r in group)
            for term in terms:d[term+'_aggregate_share']=sum(r[term] for r in group)/total
            model_summary.append(d)
        phase4_records={}
        for job in m4['jobs']:
            p,record=next((p,read(p)) for p in sorted((s4/'measurements'/job['target_id']).glob('attempt_*/attempt_record.json')) if read(p)['status']=='ok')
            assert not record.get('timing_contaminated')
            assert record['worker_sha256']==sha(s4/'frozen/tools/model_comparison_worker.py')
            for name,expected in record['worker_artifact_sha256'].items():assert sha(p.parent/name)==expected
            compat=read(p.parent/'worker/compatibility.json');assert compat['instructions_exact'] and compat['rng_after_exact']
            csvgroup=[r for r in c if r['target_id']==job['target_id']];assert len(csvgroup)==6
            for row in record['result']['rows']:
                assert row['status']=='ok' and row['accepted_schedule'] and row['normalized_sha256']==job['expected_normalized_sha256']
                assert close(sum(row[t] for t in terms),row['extended_E']) and close(math.exp(-row['extended_E']),row['extended_fidelity'])
                base=by3[row['target_id']];assert row['profile_sha256']==base['profile_sha256'] and row['geometry_sha256']==base['geometry_sha256']
                rr=next(x for x in csvgroup if x['variant']==row['variant'])
                for field in ['compile_seconds','extended_E','extended_fidelity','extended_makespan_us','routing_batches']:assert close(rr[field],row[field])
                if row['variant'] in ['original_phase3','legacy_exact']:assert close(row['extended_E'],base['extended_E'])
                else:
                    e=read(p.parent/'worker'/row['variant']/'evaluation.json');assert e['status']=='ok' and e['valid_for_comparison'] and e['validation']['status']=='ok'
                    assert close(e['budget']['total_E'],row['extended_E'])
                    metadata=read(p.parent/'worker'/row['variant']/'trace/metadata.json')
                    assert metadata['events_sha256']==sha(p.parent/'worker'/row['variant']/'trace/events.jsonl')
            phase4_records[str(p.relative_to(s4))]=sha(p)
        bases4={r['target_id']:r for r in c if r['variant']=='legacy_exact'}
        for r in c:
            base=bases4[r['target_id']]
            d={**r,'delta_E_vs_matched_original':float(r['extended_E'])-float(base['extended_E']),
                'E_change_percent':100*(float(r['extended_E'])/float(base['extended_E'])-1),
                'fidelity_ratio_vs_matched_original':float(r['extended_fidelity'])/float(base['extended_fidelity']),
                'runtime_ratio_vs_matched_original':float(r['extended_makespan_us'])/float(base['extended_makespan_us']),
                'compile_ratio_vs_matched_original':float(r['compile_seconds'])/float(base['compile_seconds']),
                'movement_delta_vs_matched_original':int(r['routing_batches'])-int(base['routing_batches'])}
            d['quality_outcome']='better' if d['delta_E_vs_matched_original'] < -1e-12 else 'worse' if d['delta_E_vs_matched_original']>1e-12 else 'tie'
            phase4.append(d)
        lookahead_summary=[]
        for variant in m4['variants']:
            group=[r for r in phase4 if r['variant']==variant];counts=Counter(r['quality_outcome'] for r in group)
            lookahead_summary.append({'variant':variant,'targets':len(group),'better':counts['better'],'tie':counts['tie'],'worse':counts['worse'],
                'median_E_change_percent':med([r['E_change_percent'] for r in group]),'median_compile_ratio':med([r['compile_ratio_vs_matched_original'] for r in group]),
                'median_runtime_ratio':med([r['runtime_ratio_vs_matched_original'] for r in group])})
        table_summary=[]
        for algorithm in ['rft','dasatom']:
            for grid in [11,35]:
                group=[r for r in comp if r['family']=='tableII' and r['algorithm']==algorithm and int(r['grid'])==grid]
                table_summary.append({'algorithm':algorithm,'grid':grid,'targets':15,'median_time_measured_to_paper':med([r['compile_measured_to_paper'] for r in group]),
                    'movement_exact_matches':sum(r['movement_exact_match'] for r in group),'fidelity_rounding_matches':sum(r['fidelity_within_reference_precision'] for r in group),
                    'median_abs_fidelity_difference_pp':med([abs(r['fidelity_delta_pp']) for r in group])})
        tableII=[]
        for case in sorted({r['case'] for r in a if r['family']=='tableII'}):
            d={'circuit':case}
            for metric,key in [('compile_s','compile_seconds'),('fidelity','legacy_fidelity'),('moves','movement_batches')]:
                for grid in [11,35]:
                    for algorithm in ['dasatom','rft']:
                        rr=next(r for r in a if r['family']=='tableII' and r['case']==case and int(r['grid'])==grid and r['algorithm']==algorithm)
                        d[f'{metric}_{grid}_{algorithm}']=int(rr[key]) if metric=='moves' else float(rr[key])
            tableII.append(d)
        attempts=[read(p) for p in (s1/'measurements').glob('*/attempt_*/attempt_record.json')];accepted=[r for r in attempts if r['status']=='ok']
        stage_totals={key:sum(r['result']['stage_seconds'].get(key,0) for r in accepted) for key in ['grid','partition','embeddings','native_route_proposals','gate_groups','corrected_routing']}
        success_time=sum(r['result']['corrected_compile_seconds'] for r in accepted);rftcv=[float(r['compile_cv']) for r in a if r['algorithm']=='rft']
        evidence={'created_utc':datetime.now(timezone.utc).isoformat(),'analysis_source_sha256':sha(__file__),
            'phase1_results_sha256':sha(s1/'results.csv'),'phase3_results_sha256':sha(s3/'results.csv'),'phase4_results_sha256':sha(s4/'results.csv'),
            'phase1_audit_sha256':sha(audit1/'summary.json'),'phase3_audit_sha256':sha(audit3/'summary.json'),'paper_reference_sha256':sha(reference_dir/'paper_reference.csv'),
            'phase4_record_sha256':phase4_records,'phase4_full_independent_physics_replay':False,
            'phase4_checks':'All record/artifact hashes, exact control instructions/RNG, inputs/profile/geometry, inline validation, CSV and budget algebra; no additional full physical replay'}
        summary={'phase1_targets':132,'phase1_rft_samples':198,'phase1_dasatom_successes':66,'phase1_attempt_statuses':dict(Counter(r['status'] for r in attempts)),
            'dasatom_success_compile_seconds_sum':success_time,'dasatom_stage_totals_seconds':stage_totals,'dasatom_partition_share':stage_totals['partition']/success_time,
            'observed_max_dasatom_family_peak_MiB':max(r['peak_working_set_bytes'] for r in accepted)/1024**2,
            'median_RFT_compile_CV':med(rftcv),'RFT_CV_above_20_percent':sum(v>.2 for v in rftcv),'phase1_stats':stats,
            'tableII_comparison_summary':table_summary,'phase3_model_summary':model_summary,'phase4_summary':lookahead_summary,
            'paper_exact_reproduction_claimed':False,'calibrated_hardware_fidelity_claimed':False}
        for name,data in [('phase1_all_results',a),('paper_comparison_all132',comp),('phase1_group_statistics',stats),('tableII_measured',tableII),
                          ('phase3_model_change_all132',changes),('phase3_error_budget',changes),('phase4_matched_comparison_all396',phase4)]:csvwrite(out/(name+'.csv'),data)
        write(out/'summary.json',summary);write(out/'evidence.json',evidence)
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
        pdf=PdfPages(out/'benchmark_figures.pdf')
        def save(fig,name):
            fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=170,bbox_inches='tight');fig.savefig(out/(name+'.svg'),bbox_inches='tight');pdf.savefig(fig);plt.close(fig)
        metrics=[('compile_seconds','paper_compile_seconds','Compilation time (s)',True),('runtime_us','paper_runtime_us','Modeled runtime (us)',False),
                 ('movement_batches','paper_movement_batches','Movement batches',False),('legacy_fidelity','paper_fidelity','Legacy fidelity proxy',True)]
        colors={11:'#1f77b4',20:'#ff7f0e',35:'#2ca02c'}
        fig,axes=plt.subplots(2,2,figsize=(12,8))
        for ax,(metric,_,label,log) in zip(axes.flat,metrics):
            for algorithm in ['dasatom','rft']:
                for grid in [11,20,35]:
                    group=sorted([r for r in a if r['family']=='fig4_qft' and r['algorithm']==algorithm and int(r['grid'])==grid],key=lambda r:int(r['case'].split('_')[1]))
                    ax.plot([int(r['case'].split('_')[1]) for r in group],[float(r[metric]) for r in group],
                        label=('Corrected DasAtom' if algorithm=='dasatom' else 'RFT')+' '+str(grid),color=colors[grid],linestyle='-' if algorithm=='dasatom' else '--',marker='o',markersize=3)
            ax.set(xlabel='QFT qubits',ylabel=label)
            if log:ax.set_yscale('log')
        axes[0,0].legend(fontsize=7,ncol=2);fig.suptitle('Phase 1 measured QFT scaling (compilation axis intentionally logarithmic)',fontsize=12)
        save(fig,'figure4_phase1_regenerated')
        fig,axes=plt.subplots(4,3,figsize=(14,14))
        for row,(metric,papermetric,label,log) in enumerate(metrics):
            for col,grid in enumerate([11,20,35]):
                ax=axes[row,col]
                for algorithm,color in [('dasatom','#1f77b4'),('rft','#d62728')]:
                    group=sorted([r for r in comp if r['family']=='fig4_qft' and r['algorithm']==algorithm and int(r['grid'])==grid],key=lambda r:int(r['case'].split('_')[1]))
                    x=[int(r['case'].split('_')[1]) for r in group]
                    ax.plot(x,[float(r[metric]) for r in group],color=color,label=algorithm+' measured',marker='o',markersize=2)
                    ax.plot(x,[float(r[papermetric]) for r in group],color=color,linestyle='--',label=algorithm+' paper')
                ax.set(xlabel='QFT qubits',ylabel=label,title=str(grid)+' x '+str(grid) if row==0 else '')
                if log:ax.set_yscale('log')
        axes[0,0].legend(fontsize=7);fig.suptitle('Paper Figure 4 vector reconstruction versus pinned-source measurements',fontsize=12)
        save(fig,'figure4_paper_vs_measured')
        fig,axes=plt.subplots(1,3,figsize=(16,4.7))
        for algorithm,color in [('rft','#d62728'),('dasatom','#1f77b4')]:
            group=[r for r in changes if r['algorithm']==algorithm]
            axes[0].scatter([r['original_fidelity'] for r in group],[r['extended_fidelity'] for r in group],label=algorithm,s=16,alpha=.65,color=color)
            axes[1].scatter([r['original_runtime_us'] for r in group],[r['extended_runtime_us'] for r in group],label=algorithm,s=16,alpha=.65,color=color)
        for ax in axes[:2]:
            ax.set_xscale('log');ax.set_yscale('log');lo=min(ax.get_xlim()[0],ax.get_ylim()[0]);hi=max(ax.get_xlim()[1],ax.get_ylim()[1]);ax.plot([lo,hi],[lo,hi],color='black',linestyle=':',linewidth=1)
        axes[0].set(xlabel='Phase 1 legacy fidelity',ylabel='Phase 3 fidelity');axes[0].legend()
        axes[1].set(xlabel='Legacy runtime (us)',ylabel='Phase 3 makespan (us)')
        bottom=[0.,0.]
        for term in terms:
            values=[r[term+'_aggregate_share']*100 for r in model_summary]
            axes[2].bar(['RFT','DasAtom'],values,bottom=bottom,label=term.replace('E_',''));bottom=[x+y for x,y in zip(bottom,values)]
        axes[2].set(ylabel='Share of summed model E (%)');axes[2].legend(fontsize=6,loc='upper right')
        fig.suptitle('Same compiler decisions: model/timing change and Phase 3 error budget',fontsize=12)
        save(fig,'phase3_model_comparison')
        fig,axes=plt.subplots(1,3,figsize=(15,4.8));labels=[r['variant'].replace('next_events_','') for r in lookahead_summary]
        axes[0].bar(labels,[r['better'] for r in lookahead_summary],label='better',color='#2ca02c');bottom=[r['better'] for r in lookahead_summary]
        axes[0].bar(labels,[r['tie'] for r in lookahead_summary],bottom=bottom,label='tie',color='#aaaaaa');bottom=[x+r['tie'] for x,r in zip(bottom,lookahead_summary)]
        axes[0].bar(labels,[r['worse'] for r in lookahead_summary],bottom=bottom,label='worse',color='#d62728');axes[0].set(ylabel='Targets out of 66');axes[0].legend(fontsize=8)
        axes[1].bar(labels,[r['median_compile_ratio'] for r in lookahead_summary],color='#1f77b4');axes[1].axhline(1,color='black',linestyle=':');axes[1].set(ylabel='Median paired compilation-time ratio')
        axes[2].boxplot([[r['E_change_percent'] for r in phase4 if r['variant']==v] for v in m4['variants']],tick_labels=labels,showfliers=True);axes[2].axhline(0,color='black',linestyle=':');axes[2].set(ylabel='Model E change (%)')
        fig.suptitle('Phase 4 versus fresh matched unchanged RFT; lower E/time is better',fontsize=12)
        save(fig,'phase4_matched_results')
        fig,ax=plt.subplots(figsize=(17,7));ax.axis('off');fields=list(tableII[0]);data=[[fmt(r[f]) for f in fields] for r in tableII]
        rendered=ax.table(cellText=data,colLabels=[f.replace('_','\n') for f in fields],loc='center',cellLoc='right');rendered.auto_set_font_size(False);rendered.set_fontsize(7);rendered.scale(1,1.5)
        fig.suptitle('Regenerated Table II: pinned RFT median times and corrected DasAtom',fontsize=12)
        save(fig,'tableII_phase1_regenerated');pdf.close()
        host=read(ROOT/'reports/phase_01/host_snapshot_20261029.json')
        q60=[r for r in comp if r['case']=='qft_60']
        selected=[r for r in changes if (r['case']=='qft_5' and int(r['grid'])==11) or (r['case']=='qft_60' and int(r['grid'])==35)]
        alltime_rft=sum(float(r['compile_seconds']) for r in a if r['algorithm']=='rft')
        report=f"""# Phase 1, Phase 3 and matched Phase 4 results

Generated {evidence['created_utc']}. No compiler was rerun for this analysis.

## Accepted scope and independent evidence

Phase 1 has all 132 configured results: 66 pinned native RFT targets (198 retained timing samples) and 66 freshly measured corrected DasAtom targets. Phase 3 has 132 accepted retimed/evaluated schedules. Phase 4 has 396 accepted rows on 66 targets.

The compiler-independent Phase 1 replay passes all 132 targets, matches CSV metrics and reconstructs the historical runtime/fidelity formulas. The Phase 3 audit reconstructs all 132 schedules and reproduces complete serialized evaluations exactly. Phase 4's 66 artifact sets, original-control instructions/RNG, common input/profile/geometry, inline independent-validation outputs and error-budget algebra were checked; its variants did not receive an additional full physical-checker replay in this analysis.

This closes the user-selected pinned-source baseline/data-analysis scope (D001/D005/D006), not exact historical paper reproduction. Original frozen sources and attempts are preserved. Native continuous-trajectory evidence, calibrated device fidelity and timing of omitted original one-qubit gates remain outside the accepted scope. Corrected DasAtom is not silently labelled native DasAtom.

## Phase 1 statistics

Statistics describe different configured circuits, not confidence intervals. RFT compilation values are medians of three samples; corrected DasAtom has one fresh accepted sample per target.

"""
        report+=table(stats,[('algorithm','Method'),('grid','Grid'),('targets','Targets'),('compile_seconds_median','Median compile s'),('compile_seconds_max','Maximum compile s'),('runtime_us_median','Median runtime us'),('movement_batches_median','Median moves'),('legacy_fidelity_median','Median fidelity')])
        report+=f"""
The sum of the 66 RFT target timing medians is {alltime_rft:.6g} s. Corrected DasAtom compilation times sum to {success_time:.6g} s ({success_time/3600:.3f} hours); {100*summary['dasatom_partition_share']:.2f}% was partitioning. These totals use different timer scopes and cannot establish controlled cross-algorithm speedup. Maximum observed DasAtom family working set was {summary['observed_max_dasatom_family_peak_MiB']:.2f} MiB; polling is not an allocation-proof peak measurement.

Retained DasAtom attempt states: {json.dumps(summary['phase1_attempt_statuses'])}. Earlier launch errors and sleep interruptions are not accepted samples. Median RFT timing CV is {100*summary['median_RFT_compile_CV']:.1f}%; {summary['RFT_CV_above_20_percent']}/66 targets exceed 20%. No blanket repetition was added. Small timing differences do not establish statistical significance.

Post-run host snapshot: {host['cpu']}, {host['ram_bytes']/1024**3:.2f} GiB RAM. The paper specifies an 8th-generation Core i5 and 8 GB RAM. No CPU-speed normalization or per-attempt historical power/temperature record exists.

![Phase 1 QFT scaling](figure4_phase1_regenerated.png)

## Comparison with the paper

All 180 printed Table II cells were independently checked against the PDF. All 288 Figure 4 metric values were recovered from vector paths and calibrated against the axes; these are not an author-supplied raw CSV. Conservative uncertainty floors: 1e-5 s, .01 us, .001 movement count and 1e-6 log10(F). Printed fidelities use half the last displayed digit as rounding tolerance.

The full 132-row CSV includes time/runtime ratios, movement deltas, fidelity percentage-point/log-error differences and per-target verdicts. Numerical mismatches retain unresolved historical configuration; no baseline tuning was used to force agreement.

Table II summary (timing ratios are descriptive across different hosts/scopes):

"""
        report+=table(table_summary,[('algorithm','Method'),('grid','Grid'),('median_time_measured_to_paper','Median measured/paper time'),('movement_exact_matches','Move matches /15'),('fidelity_rounding_matches','Fidelity rounding matches /15'),('median_abs_fidelity_difference_pp','Median absolute fidelity difference pp')])
        report+='\nQFT60 comparison; paper numbers are approximate PDF-vector reconstructions:\n\n'
        report+=table(q60,[('algorithm','Method'),('grid','Grid'),('compile_seconds','Our compile s'),('paper_compile_seconds','Paper compile s'),('movement_batches','Our moves'),('paper_movement_batches','Paper moves'),('legacy_fidelity','Our F'),('paper_fidelity','Paper F')])
        report+="""
Discrepancies and limits:

- Historical revision/options, original seeds/layouts and paper input identities remain unresolved. Our RFT control is ladder7; recovered table scripts refer to ladder8 filenames, which is not proof of the paper's exact configuration.
- Corrected DasAtom restores inactive declared qubits and repairs invalid native transitions. These changes can increase movement/runtime and alter fidelity. Original invalid/native records remain archived.
- RFT excludes preprocessing/offline layout/scoring from its timer; corrected DasAtom includes graph/partition/embedding/grouping/repair under a different documented scope. Cross-method or cross-host time ratios are not controlled algorithmic speedups.
- The compilation plot is linear despite its caption saying logarithmic. QFT60 RFT plot values reconstruct to approximately 2.79/2.56/3.28 s on grids 11/20/35, whereas the prose says under a second. This is a source inconsistency, not a reproduction tolerance.
- The historical transfer alias is four times the movement-batch count; it is not an observed transferred-atom count. Fidelity is an analytical proxy, not a measured quantum-state fidelity.

![Paper versus measured QFT](figure4_paper_vs_measured.png)

## Phase 3: same decisions, different timing/error model

Compilation time and ordered gate/movement choices remain unchanged for all 132 targets. Cubic timing, explicit transfers, heating/loss and per-qubit exposure change makespan/fidelity. Exposure and transfer-stage conventions also change: the whole original-to-extended difference is not a heating-only effect.

"""
        report+=table(model_summary,[('algorithm','Method'),('targets','Targets'),('fidelity_decreases','F decreases'),('median_fidelity_retention','Median Fnew/Fold'),('median_runtime_ratio','Median runtime ratio'),('median_delta_E','Median increase in E'),('nonzero_movement_loss_targets','Nonzero loss terms')])
        report+='\nRepresentative paired changes:\n\n'+table(selected,[('algorithm','Method'),('case','Circuit'),('grid','Grid'),('original_fidelity','Legacy F'),('extended_fidelity','Phase3 F'),('original_runtime_us','Legacy us'),('extended_runtime_us','Phase3 us')])
        report+="""
The budget CSV retains every additive E term, its share and fixed-transformed-schedule factor-removal diagnostics. Removing one factor is a conditional accounting diagnostic, not a different compiler/profile/trajectory experiment. Cooling contributes zero under the selected no-cooling profile.

![Phase 3 model comparison](phase3_model_comparison.png)

## Phase 4: matched algorithm comparison under Phase 3

All predefined horizons are retained. Better/tie/worse uses delta E tolerance 1e-12. Time ratios use a fresh unchanged RFT control in the SAME worker and original benchmark-runner region. Modified index/query/parking work is included. Warmups are excluded and measured-start RNG restored. Each variant has one timed sample, fixed order and no confidence interval. No best h is selected from these results.

"""
        report+=table(lookahead_summary,[('variant','Variant'),('better','Better'),('tie','Tie'),('worse','Worse'),('median_E_change_percent','Median E change %'),('median_compile_ratio','Median compile ratio'),('median_runtime_ratio','Median runtime ratio')])
        report+="""
There is no universal lookahead improvement: every horizon worsens some targets, and more lookahead need not improve quality. Algorithm effects are compared against the matched Phase 3-scored control, not a Phase 1 legacy-model score.

![Matched Phase 4 results](phase4_matched_results.png)

## Artifacts

- `phase1_all_results.csv`: all measured targets.
- `paper_comparison_all132.csv`: complete paper comparison and per-target verdicts.
- `tableII_measured.csv` and `tableII_phase1_regenerated.png`: regenerated Table II.
- `phase1_group_statistics.csv`: descriptive compile/runtime/movement/fidelity statistics.
- `phase3_model_change_all132.csv`, `phase3_error_budget.csv`: paired model changes and error factors.
- `phase4_matched_comparison_all396.csv`: all lookahead results, including negative outcomes.
- `summary.json`, `evidence.json`: summaries, evidence scope and input hashes.
- `benchmark_figures.pdf`, PNG and SVG exports.
- `../phase_01/final_dataset_audit_02`: independent Phase 1 replay.
- `../phase_03/full_dataset_audit_02`: independent Phase 3 reconstruction/evaluation.
- `../phase_01/paper_reference_01`: PDF vector coordinates/calibration and verified references.

Phase 5 is not reported as a completed full benchmark here. Exact manuscript provenance and native physical evidence remain explicit limits.
"""
        (out/'report.md').write_text(report,encoding='utf-8')
        html='<!doctype html><meta charset="utf-8"><title>Benchmark analysis</title><style>body{font:16px system-ui;max-width:1450px;margin:32px auto;padding:0 20px}img{max-width:100%}a{color:#1558ad}</style><h1>Phase 1 / Phase 3 / Phase 4 benchmark analysis</h1><p><a href="report.md">Full report</a> | <a href="summary.json">Summary</a>. Scores are analytical; historical manuscript identity remains unresolved.</p>'
        for name in ['figure4_phase1_regenerated','figure4_paper_vs_measured','phase3_model_comparison','phase4_matched_results','tableII_phase1_regenerated']:
            html+='<h2>'+name.replace('_',' ')+'</h2><a href="'+name+'.svg"><img src="'+name+'.png"></a>'
        html+='<h2>Data exports</h2>'+''.join('<p><a href="'+p.name+'">'+p.name+'</a></p>' for p in sorted(out.glob('*.csv')))
        (out/'report.html').write_text(html,encoding='utf-8')
        write(out/'artifact_sha256.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})
        print(json.dumps({'phase1_targets':132,'phase3_targets':132,'phase4_rows':396,'output':str(out),'phase3_summary':model_summary,'phase4_summary':lookahead_summary}),flush=True)
    finally:service.release(lock)

if __name__=='__main__':main()
