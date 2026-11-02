"""Read-only audit and detailed Phase 4/5 interpretation. --write saves a new report only."""
import base64,csv,hashlib,html,io,json,math,statistics as st,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=(Path.cwd()/'btp_work').resolve()
OUT=ROOT/'reports/phase_04_05_detailed_analysis_01'
SAVE='--write' in sys.argv
TERMS=['E_native_gate','E_transfer','E_heating_gate','E_movement_loss','E_cooling_gate','E_decoherence']
S4=ROOT/'runs/phase04_matched_benchmark_v2'; S5=ROOT/'runs/phase05_matched_benchmark_v1'
P5=ROOT/'reports/phase_05/full_analysis_02'; OLD=ROOT/'reports/final_benchmark_analysis_01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))
def grouped(rr):
    g=defaultdict(dict)
    for r in rr:
        assert r['variant'] not in g[r['target_id']], 'duplicate target/variant'
        g[r['target_id']][r['variant']]=r
    return dict(g)
checks={}
for name,folder in [('previous_phase5',P5),('previous_phase134',OLD)]:
    checks[name+'_artifacts_unchanged']=all(sha(folder/k)==v for k,v in read(folder/'artifact_sha256.json').items())
checks['previous_phase5_verification_passed']=read(P5/'verification.json')['passed']
checks['previous_final_gate_passed']=read(OLD/'final_gate.json')['passed']
sources={str(p.relative_to(ROOT)):sha(p) for s in [S4,S5] for p in [s/'manifest.json',s/'results.csv',s/'summary.json']}
checks['phase4_source_matches_prior_audit']=sha(S4/'results.csv')==read(OLD/'evidence.json')['phase4_results_sha256']
checks['phase5_source_matches_prior_audit']=sha(S5/'results.csv')==read(P5/'evidence.json')['results_sha256']
checks['frozen_manifests_match']=all(sha(s/'manifest.json')==(s/'manifest.sha256').read_text().strip() for s in [S4,S5])
r4,r5=rows(S4/'results.csv'),rows(S5/'results.csv')
g4,g5=grouped(r4),grouped(r5)
v4=['next_events_h1','next_events_h2','next_events_h4','next_events_h8']
expected4={'original_phase3','legacy_exact',*v4}
expected5={'original_phase3','legacy_exact',*read(S5/'manifest.json')['variants']}
checks['complete_phase4_matrix']=len(r4)==396 and len(g4)==66 and all(set(v)==expected4 for v in g4.values()) and read(S4/'summary.json')['matrix_complete']
checks['complete_phase5_matrix']=len(r5)==792 and len(g5)==66 and all(set(v)==expected5 for v in g5.values()) and read(S5/'summary.json')['matrix_complete']
checks['all_inline_schedules_accepted']=all(r['status']=='ok' and r['accepted_schedule']=='True' and r['attempt_status']=='ok' for r in r4+r5)
checks['same_targets']=set(g4)==set(g5)
checks['common_profile']=len({r['profile_sha256'] for r in r4+r5})==1
checks['same_input_geometry_layout_per_target']=all(all(len({r[k] for r in list(g4[t].values())+list(g5[t].values()) if r[k]})==1 for k in ['normalized_sha256','geometry_sha256','layout_sha256']) for t in g4)
checks['budgets_and_fidelity']=all(math.isclose(sum(float(r[k]) for k in TERMS),float(r['extended_E']),rel_tol=1e-12,abs_tol=1e-12) and math.isclose(math.exp(-float(r['extended_E'])),float(r['extended_fidelity']),rel_tol=1e-12,abs_tol=0) for r in r4+r5)
checks['unchanged_control_instructions_rng_and_scores']=all(g['legacy_exact']['legacy_exact_instructions']=='True' and g['legacy_exact']['legacy_exact_rng']=='True' and float(g['legacy_exact']['extended_E'])==float(g['original_phase3']['extended_E']) for gg in [g4,g5] for g in gg.values())
checks['phase5_all_660_instruction_hashes']=all(sha(ROOT/r['output']/'instructions.txt')==r['instructions_sha256'] for r in r5 if r['variant'] in read(S5/'manifest.json')['variants'])
checks['phase4_h4_matches_phase5_reference']=all(float(g4[t]['next_events_h4']['extended_E'])==float(g5[t]['phase04_reference']['extended_E']) and sha(ROOT/g4[t]['next_events_h4']['output']/'instructions.txt')==g5[t]['phase04_reference']['instructions_sha256'] for t in g4)
checks['phase5_all594_prefix_heating_checks']=sum(r['prefix_heating_matches_full_evaluator']=='True' for r in r5)==594
record_count=0; record_hashes={}
for study,rr in [(S4,r4),(S5,r5)]:
    byrecord=defaultdict(list)
    for r in rr:byrecord[r['attempt_record']].append(r)
    for rel,items in byrecord.items():
        path=study/rel;record=read(path); assert record['status']=='ok'
        raw={r['variant']:r for r in record['result']['rows']}
        for r in items:
            for k in ['extended_E','extended_fidelity','extended_makespan_us','compile_seconds']:
                assert float(r[k])==float(raw[r['variant']][k]),(rel,k)
        record_hashes[str(path.relative_to(ROOT))]=sha(path);record_count+=1
checks['all132_committed_worker_records_match']=record_count==132
checks['phase5_previous_record_hashes_match']=all(sha(ROOT/item['record'])==item['sha256'] for item in read(P5/'evidence.json')['attempt_records'])
checks['phase4_previous_record_hashes_match']=all(sha(S4/k)==v for k,v in read(OLD/'evidence.json')['phase4_record_sha256'].items())
assert all(checks.values()),checks
pairs5=[
('sum_distance','phase04_reference'),('bottleneck_distance','sum_distance'),
('bottleneck_time','sum_distance'),('composite_sum','sum_distance'),
('composite_bottleneck','sum_distance'),('sum_distance_expanded','sum_distance'),
('composite_bottleneck_expanded','sum_distance_expanded'),
('composite_bottleneck_expanded','sum_distance'),
('composite_bottleneck_expanded','phase04_reference'),
('composite_no_conflict','composite_bottleneck'),
('composite_no_future','composite_bottleneck'),
('phase04_reference','legacy_exact'),('composite_bottleneck_expanded','legacy_exact')]
def compare(phase,g,v,c):
    result=[]
    for target,d in g.items():
        x,y=d[v],d[c];de=float(x['extended_E'])-float(y['extended_E'])
        a={'phase':phase,'target_id':target,'case':x['case'],'family':x['family'],'grid':int(x['grid']),'variant':v,'control':c,
           'baseline_E':float(y['extended_E']),'variant_E':float(x['extended_E']),'delta_E':de,
           'relative_E_percent':100*de/float(y['extended_E']),'baseline_F':float(y['extended_fidelity']),'variant_F':float(x['extended_fidelity']),
           'fidelity_ratio':math.exp(-de),'fidelity_delta_pp':100*(float(x['extended_fidelity'])-float(y['extended_fidelity'])),
           'baseline_makespan_ms':float(y['extended_makespan_us'])/1000,'variant_makespan_ms':float(x['extended_makespan_us'])/1000,
           'makespan_ratio':float(x['extended_makespan_us'])/float(y['extended_makespan_us']),
           'baseline_compile_seconds':float(y['compile_seconds']),'variant_compile_seconds':float(x['compile_seconds']),
           'compile_ratio':float(x['compile_seconds'])/float(y['compile_seconds']),
           'baseline_moved_atom_events':int(y['moved_atom_events']),'variant_moved_atom_events':int(x['moved_atom_events']),
           'baseline_routing_batches':int(y['routing_batches']),'variant_routing_batches':int(x['routing_batches']),
           'atom_distance_delta_um':float(x['sum_atom_distance_um'])-float(y['sum_atom_distance_um']),
           'outcome':'better' if de<-1e-12 else 'worse' if de>1e-12 else 'tie'}
        for t in TERMS:a['delta_'+t]=float(x[t])-float(y[t])
        assert math.isclose(sum(a['delta_'+t] for t in TERMS),de,rel_tol=1e-10,abs_tol=1e-12)
        result.append(a)
    return result
comparisons={(4,v,'legacy_exact'):compare(4,g4,v,'legacy_exact') for v in v4}
comparisons.update({(5,v,c):compare(5,g5,v,c) for v,c in pairs5})
def summarize(key,aa,group='all'):
    phase,v,c=key
    a={'phase':phase,'variant':v,'control':c,'group':group,'n':len(aa),
       'better':sum(x['outcome']=='better' for x in aa),'tie':sum(x['outcome']=='tie' for x in aa),'worse':sum(x['outcome']=='worse' for x in aa)}
    for field in ['relative_E_percent','fidelity_ratio','fidelity_delta_pp','makespan_ratio','compile_ratio','variant_compile_seconds','baseline_compile_seconds']:
        vals=[x[field] for x in aa]
        for label,fn in [('median',st.median),('mean',st.mean),('min',min),('max',max)]:a[label+'_'+field]=fn(vals)
    for t in TERMS:a['mean_delta_'+t]=st.mean(x['delta_'+t] for x in aa)
    a['sum_delta_E']=sum(x['delta_E'] for x in aa)
    a['variable_error_mean_relative_percent']=st.mean(100*x['delta_E']/(x['baseline_E']-float((g4 if phase==4 else g5)[x['target_id']][c]['E_native_gate'])) for x in aa)
    return a
summaries=[]
for key,aa in comparisons.items():
    groups={'all':aa}
    for grid in [11,20,35]:groups['grid='+str(grid)]=[x for x in aa if x['grid']==grid]
    for family in ['fig4_qft','tableII']:groups['family='+family]=[x for x in aa if x['family']==family]
    for grid in [11,20,35]:
        for family in ['fig4_qft','tableII']:
            groups['grid='+str(grid)+';family='+family]=[x for x in aa if x['grid']==grid and x['family']==family]
    groups['posthoc_baseline_F_ge_0.5']=[x for x in aa if x['baseline_F']>=.5]
    for name,ss in groups.items():
        if ss:summaries.append(summarize(key,ss,name))
def get(phase,v,c,group='all'):return next(s for s in summaries if (s['phase'],s['variant'],s['control'],s['group'])==(phase,v,c,group))
old5={(r['variant'],r['control'],r['group']):r for r in rows(P5/'paired_summary.csv')}
checks['phase5_all_previous_summaries_recomputed']=all(all(math.isclose(float(s[k]),float(old5[(s['variant'],s['control'],s['group'])][k]),rel_tol=1e-10,abs_tol=1e-12) for k in ['better','tie','worse','median_relative_E_percent','mean_relative_E_percent','median_fidelity_ratio','median_makespan_ratio','median_compile_ratio']) for s in summaries if s['phase']==5 and (s['variant'],s['control'],s['group']) in old5)
variant_stats=[]
for phase,rr in [(4,r4),(5,r5)]:
    for v in sorted({r['variant'] for r in rr}):
        aa=[r for r in rr if r['variant']==v]
        s={'phase':phase,'variant':v,'n':len(aa)}
        for k in ['extended_E','extended_fidelity','extended_makespan_us','compile_seconds','moved_atom_events','routing_batches','sum_atom_distance_um']:
            s['median_'+k]=st.median(float(r[k]) for r in aa)
        for t in TERMS:s['sum_'+t]=sum(float(r[t]) for r in aa)
        for k in ['assignment_solves','assignment_candidate_seconds','assignment_cost_seconds','assignment_matching_seconds']:
            ss=[float(r[k]) for r in aa if r.get(k)]
            if ss:s['median_'+k]=st.median(ss);s['sum_'+k]=sum(ss)
        variant_stats.append(s)
p6=ROOT/'runs/phase06_matched_benchmark_v1/progress.json'
p6v2=ROOT/'runs/phase06_matched_benchmark_v2/progress.json'
phase6status={'v1':read(p6),'v2':read(p6v2)}
assert all(checks.values()),checks
if not SAVE:
    print(json.dumps({'checks':checks,'phase4_summary':[get(4,v,'legacy_exact') for v in v4],
       'phase5_main':get(5,'composite_bottleneck_expanded','phase04_reference'),
       'phase5_clean':get(5,'composite_bottleneck_expanded','sum_distance_expanded'),
       'output_exists':OUT.exists(),'phase6_full_status':phase6status},indent=2))
    sys.exit(0)
assert not OUT.exists(),'Fresh output directory required'
assert OUT.is_relative_to(ROOT/'reports')
OUT.mkdir()
(OUT/'analysis.py').write_text(globals().get('ANALYSIS_SOURCE',Path(__file__).read_text(encoding='utf-8') if '__file__' in globals() else ''),encoding='utf-8')
def savecsv(name,data):
    fields=list(dict.fromkeys(k for r in data for k in r))
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
savecsv('paired_cases.csv',[r for aa in comparisons.values() for r in aa])
savecsv('paired_summary.csv',summaries);savecsv('variant_statistics.csv',variant_stats)
for s,name in [(S4,'phase4_all396.csv'),(S5,'phase5_all792.csv')]: (OUT/name).write_bytes((s/'results.csv').read_bytes())
import os
os.environ['MPLCONFIGDIR']=str(OUT/'plot_config')
import ctypes
if os.name=='nt': ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x40)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':130})
GREEN='#21866b';RED='#c65d4b';GRAY='#b7bdc4';BLUE='#3d6f9e'
def figure(phase,keys,title,filename):
    ss=[get(*k) for k in keys];labels=[s['variant'].replace('next_events_','').replace('composite_bottleneck_expanded','expanded composite').replace('sum_distance_expanded','expanded sum').replace('sum_distance','corrected sum').replace('bottleneck_distance','bottleneck distance').replace('bottleneck_time','bottleneck time')+'\nvs '+s['control'].replace('phase04_reference','Phase 4 h4').replace('sum_distance_expanded','expanded sum').replace('sum_distance','corrected sum').replace('legacy_exact','original') for s in ss]
    fig,ax=plt.subplots(2,2,figsize=(15,10),layout='constrained');x=list(range(len(ss)))
    b=[s['better'] for s in ss];t=[s['tie'] for s in ss];w=[s['worse'] for s in ss]
    ax[0,0].bar(x,b,color=GREEN,label='Better');ax[0,0].bar(x,t,bottom=b,color=GRAY,label='Tie');ax[0,0].bar(x,w,bottom=[i+j for i,j in zip(b,t)],color=RED,label='Worse')
    ax[0,0].set(title='Paired outcomes (66 circuit/grid targets)',ylabel='Target count',ylim=(0,73));ax[0,0].legend(ncol=3,fontsize=8)
    for i in x:ax[0,0].text(i,67,f'{b[i]}/{t[i]}/{w[i]}',ha='center',fontsize=8)
    for i,s in enumerate(ss):
        vals=sorted(r['relative_E_percent'] for r in comparisons[keys[i]])
        ax[0,1].scatter([i]*len(vals),vals,alpha=.3,s=12,color=BLUE)
    ax[0,1].scatter(x,[s['median_relative_E_percent'] for s in ss],color='black',marker='_',s=170,label='Median')
    ax[0,1].axhline(0,color='gray',lw=.8);ax[0,1].set(title='Error change distribution; negative is better',ylabel='Relative E change (%)');ax[0,1].legend(fontsize=8)
    ax[1,0].bar([i-.18 for i in x],[s['median_compile_ratio'] for s in ss],width=.36,color=BLUE,label='Classical compile ratio')
    ax[1,0].bar([i+.18 for i in x],[s['median_makespan_ratio'] for s in ss],width=.36,color=GREEN,label='Modeled execution ratio')
    ax[1,0].axhline(1,color='gray',lw=.8);ax[1,0].set(title='Paired median time ratios',ylabel='Variant / control');ax[1,0].legend(fontsize=8)
    for i,s in enumerate(ss):
        terms=[s['mean_delta_'+q] for q in ['E_transfer','E_heating_gate','E_decoherence']]
        for j,value in enumerate(terms):ax[1,1].bar(i+(j-1)*.23,value,width=.22,color=['#de934b','#8c78a9',BLUE][j],label=['Transfer','Heating-gate','Decoherence'][j] if i==0 else None)
    ax[1,1].axhline(0,color='gray',lw=.8);ax[1,1].set(title='Mean additive error changes; negative is better',ylabel='Delta E');ax[1,1].legend(fontsize=8)
    for a in ax.flat:a.set_xticks(x,labels,fontsize=8);a.grid(axis='y',alpha=.15)
    fig.suptitle(title+'\nSame Phase 3 no-cooling model; one measured timing sample per new variant',fontsize=15)
    for ext in ['png','svg','pdf']:fig.savefig(OUT/(filename+'.'+ext),bbox_inches='tight')
    return fig
fig4=figure(4,[(4,v,'legacy_exact') for v in v4],'Phase 4: future-aware parking','phase4_analysis')
keys5=[(5,'sum_distance','phase04_reference'),(5,'bottleneck_time','sum_distance'),(5,'sum_distance_expanded','sum_distance'),(5,'composite_bottleneck_expanded','sum_distance_expanded'),(5,'composite_bottleneck_expanded','phase04_reference')]
fig5=figure(5,keys5,'Phase 5: separate pipeline, candidate-budget and objective effects','phase5_analysis')
with PdfPages(OUT/'analysis_figures.pdf') as pdf:pdf.savefig(fig4);pdf.savefig(fig5)
plt.close('all')
md=[];web=[]
def heading(s,level=2):md.append('#'*level+' '+s+'\n');web.append(f'<h{level}>{html.escape(s)}</h{level}>')
def para(s):md.append(s+'\n');web.append('<p>'+html.escape(s)+'</p>')
def table(data,cols):
    md.append('| '+' | '.join(label for key,label in cols)+' |\n| '+' | '.join('---' for _ in cols)+' |\n'+'\n'.join('| '+' | '.join(str(r.get(k,'')) for k,l in cols)+' |' for r in data)+'\n')
    web.append('<div class="table"><table><thead><tr>'+''.join('<th>'+html.escape(l)+'</th>' for k,l in cols)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(k,'')))+'</td>' for k,l in cols)+'</tr>' for r in data)+'</tbody></table></div>')
def plot(name,caption):
    md.append('!['+caption+']('+name+'.png)\n')
    web.append('<figure><img alt="'+html.escape(caption)+'" src="data:image/png;base64,'+base64.b64encode((OUT/(name+'.png')).read_bytes()).decode()+'"><figcaption>'+html.escape(caption)+'</figcaption></figure>')
def compact(s):
    return {'variant':s['variant'],'control':s['control'],'n':s['n'],'btw':f"{s['better']}/{s['tie']}/{s['worse']}",'med':f"{s['median_relative_E_percent']:+.3f}%",'mean':f"{s['mean_relative_E_percent']:+.3f}%",'f':f"{s['median_fidelity_ratio']:.5f}",'run':f"{s['median_makespan_ratio']:.4f}x",'compile':f"{s['median_compile_ratio']:.3f}x"}
cols=[('variant','Variant'),('control','Control'),('btw','Better/tie/worse'),('med','Median E change'),('mean','Mean E change'),('f','Median F ratio'),('run','Median execution ratio'),('compile','Median compile ratio')]
heading('Detailed Phase 4 and Phase 5 benchmark analysis, with Phase 6 interpretation',1)
para('Prepared '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')+'. No compiler or benchmark was rerun. Both benchmark matrices and their earlier analysis artifacts were already complete; this report verifies and expands their interpretation without replacing them.')
heading('What is complete')
para('Phase 4: 66 matched circuit/grid targets, 396 accepted rows (saved original, fresh unchanged control, h=1/2/4/8). Phase 5: the same 66 targets, 792 accepted rows (saved original, fresh unchanged control, Phase 4 h4 reference, nine assignment controls/variants). There are 27 distinct circuit inputs, not 396 or 792 independent circuits.')
para('Both datasets use extended_no_cooling.v1, normalized CZ skeletons and the same declared geometry for each target. DasAtom is a previously saved anchor; these tracks modify RFT and do not recompile DasAtom.')
heading('How to read the comparisons')
para('E = -ln(F_proxy): lower E is better, higher F is better. Relative E change is 100*(E_variant-E_control)/E_control; a negative value is an improvement. F_variant/F_control = exp(-(E_variant-E_control)). A percentage reduction in E is not a percentage-point increase in F. Modeled execution time is makespan; classical compilation time is measured separately.')
para('All medians and means are calculated from per-target paired changes. Separate medians need not describe any single circuit. Native-gate error is fixed for a matched circuit; placement changes affect the remaining terms. All wins/losses use absolute E tolerance 1e-12. No per-target best horizon or assignment policy is selected.')
para('Compile ratios use the fresh unchanged reference or specified control from the same worker attempt and timed region. One measured sample per new variant, fixed order and machine variability prevent confidence-interval or small-speedup claims. Reused historical compilation times are not treated as fresh matched controls.')
heading('Phase 4: what changes and why')
para('Phase 4 changes initial idle placement and later idle-qubit eviction. It replaces the original parking rule with a sparse next-h-interaction-occurrence index, preserving repeated partners and excluding already executed/currently committed gates. h counts events, not layers. Candidate parking sites are ranked by sum gamma^delta * distance(site,partner anchor), with gamma=0.9 and equal event weights.')
para('An anchor is the already committed active destination when available, otherwise the current position. Future positions are unknown. The new policy has no immediate relocation-distance term. Local active placement, Hungarian assignment/orientation, candidate slots and router stay as in the original. Changing parking changes the positions those unchanged routines see later. h=1 is a new policy, not an exact reproduction of the original picker.')
table([compact(get(4,v,'legacy_exact')) for v in v4],cols)
para('h1 and h2 improve 41 of 66 targets each; h4 improves 37 and h8 improves 32. h8 has zero median E change and positive mean E change (+1.187%), while adding the largest median compilation overhead. More lookahead therefore does not reliably improve the complete modeled result.')
plot('phase4_analysis','Phase 4 paired quality, time and error-budget comparisons')
heading('Phase 4: workload and grid breakdown')
a=[]
for v in v4:
    for group in ['family=fig4_qft','family=tableII','grid=11','grid=20','grid=35']:
        s=get(4,v,'legacy_exact',group);a.append({'variant':v,'group':group,'n':s['n'],'btw':f"{s['better']}/{s['tie']}/{s['worse']}",'med':f"{s['median_relative_E_percent']:+.3f}%",'mean':f"{s['mean_relative_E_percent']:+.3f}%"})
table(a,[('variant','Policy'),('group','Subset'),('n','Targets'),('btw','Better/tie/worse'),('med','Median E change'),('mean','Mean E change')])
para('At h4, QFT has 16 wins/1 tie/19 losses; Table II has 21/3/6. At h8, QFT has 11/1/24 but Table II remains 21/3/6. The additional horizon is particularly unreliable on QFT here. At grid20, h4 loses 10/12 and h8 loses 11/12. Grid20 contains only QFT, while grids11/35 also contain Table II; cross-grid totals confound grid and workload mix. Exact family-by-grid summaries are in paired_summary.csv.')
heading('Phase 4: representative improvements and regressions')
examples4=[]
for v,case,grid in [('next_events_h1','bv_n16',35),('next_events_h1','4mod5-v1_22',11),('next_events_h4','qft_55',20),('next_events_h8','qft_35',11)]:
    x=next(r for r in comparisons[(4,v,'legacy_exact')] if r['case']==case and r['grid']==grid);examples4.append(x)
def example_rows(aa):
    return [{'case':r['case']+' / '+str(r['grid'])+'x'+str(r['grid']),'variant':r['variant'],'pct':f"{r['relative_E_percent']:+.3f}%",'F':f"{r['baseline_F']:.6g} -> {r['variant_F']:.6g}",'ms':f"{r['baseline_makespan_ms']:.4f} -> {r['variant_makespan_ms']:.4f}",'move':f"{r['baseline_moved_atom_events']} -> {r['variant_moved_atom_events']}",'batch':f"{r['baseline_routing_batches']} -> {r['variant_routing_batches']}"} for r in aa]
examplecols=[('case','Circuit / grid'),('variant','Policy'),('pct','E change'),('F','F before -> after'),('ms','Execution ms before -> after'),('move','Moved atom-events'),('batch','Routing batches')]
table(example_rows(examples4),examplecols)
para('The bv_n16 improvement reduces transfer and decoherence terms; its fidelity rises by 2.722 percentage points. The 4mod5 regression changes initial idle parking, increases moved-atom events and makespan, and lowers fidelity by 1.446 percentage points. It is not an eviction-only effect. Long-QFT regressions are dominated by added decoherence exposure. A lower future-distance surrogate does not prove lower full-circuit E.')
heading('Phase 5: what it adds')
para('Phase 5 replaces the unresolved pair-to-slot assignment block while retaining h4 parking. It evaluates both physical endpoint orientations and applies the orientation actually used in the selected cost. This repairs a cost/materialization mismatch in the pinned source; gains from that correction must be separated from gains of a new objective.')
para('The controls compare minimum-sum distance with lexicographic bottleneck-then-sum assignment. Bottleneck means minimizing the largest selected row cost first, then the sum among assignments meeting that minimum threshold. It is not a proof of minimum full routed makespan. Costs can be endpoint distance, local move time, or a composite surrogate.')
para('The composite includes normalized distance, conflicts with committed movements and within a row, transfer population, Phase 3 predicted heating/loss costs, and discounted future-distance potential. The prefix observer tracks already emitted heating. Composite weights are fixed at distance/conflict/transfer/heating=1 and future=0.25; normalizers are 15um, one conflict, four transfer atom-events and 0.01 E. Weights were not tuned on this benchmark.')
para('Expanded candidates allow up to twice the unresolved-pair count of nearby safe slots, rather than only that count. This changes the search space independently of the objective. Simultaneously chosen new rows can conflict with each other outside the fixed linear cost, and actual routing/evictions/suffix behavior can defeat local predictions. All-slot and optional displacement estimation are not part of the default full benchmark.')
table([compact(get(5,v,c)) for v,c in pairs5],cols)
plot('phase5_analysis','Phase 5 matched controls separate correction, expansion and composite-objective effects')
heading('Phase 5: conclusions that survive the matched controls')
para('Corrected sum-distance versus Phase 4: 39 improvements, 2 ties, 25 regressions; median E -0.536%, mean -0.323%, median compile ratio 1.470x. This is a corrected pipeline comparison, not a clean isolation of orientation alone or of a novel objective.')
para('Expanded composite versus Phase 4: 42 improvements, 2 ties, 22 regressions; median E -0.745%, mean -1.171%; median fidelity ratio 1.01358, modeled execution ratio 0.96062 and compile ratio 1.52607. Those correspond to about 1.36% relative fidelity-proxy improvement, 3.94% shorter modeled execution and 52.6% more compilation time at their separate paired medians.')
para('The clean composite-objective comparison holds the expanded candidate budget fixed: 30 wins/9 ties/27 losses versus expanded distance-sum, zero median E change, mean -0.514%. This is an uneven average benefit, with almost as many regressions as improvements. It does not establish general composite dominance.')
para('Candidate expansion by itself wins 30/ties14/loses22 versus unexpanded distance-sum, with zero median E change and mean -0.285%. The full expanded-composite gain cannot all be assigned to its cost formula.')
para('Pure bottleneck distance/time each win21/tie5/lose40 against corrected sum-distance. Optimizing a local largest move can worsen the complete circuit because serialization, evictions, future placements and heating remain coupled.')
para('At the original candidate budget, composite sum wins18/ties18/loses30 and composite bottleneck wins20/ties19/loses27. Removing the conflict term wins26/ties23/loses17 against full composite; that conflict proxy/weight is not consistently helpful. Removing future cost wins14/ties33/loses19; this suggests some future-term benefit here without proving universal value. These ablations use the original candidate budget, so they do not isolate terms inside expanded composite.')
heading('Phase 5: where expanded composite helps')
a=[]
for control in ['phase04_reference','sum_distance_expanded']:
    for group in ['family=fig4_qft','family=tableII','grid=11','grid=20','grid=35']:
        s=get(5,'composite_bottleneck_expanded',control,group);a.append({**compact(s),'group':group,'n':s['n']})
table(a,[('control','Control'),('group','Subset'),('n','Targets'),('btw','Better/tie/worse'),('med','Median E change'),('mean','Mean E change'),('run','Median execution ratio'),('compile','Median compile ratio')])
para('Against Phase 4, grid35 has 21/1/5 and median E -1.628%; grid11 has 13/1/13 and median zero. QFT has25/0/11; Table II has17/2/11. Against expanded sum, Table II splits12/6/12 with zero median change. The larger pipeline gain is more convincing than the isolated objective claim. Comparisons here are descriptive; the subgroups were not separate held-out experiments.')
heading('Phase 5: concrete positive and negative cases')
examples5=[]
for case,grid in [('qft_15',35),('4mod5-v1_22',35),('qft_60',35),('qft_50',35),('alu-v0_27',11)]:
    examples5.append(next(r for r in comparisons[(5,'composite_bottleneck_expanded','phase04_reference')] if r['case']==case and r['grid']==grid))
table(example_rows(examples5),examplecols)
para('QFT15 on35: fidelity 0.160865 -> 0.182031 and makespan39.076 ->30.808ms, with E -6.765%. QFT60 on35: the fidelity ratio is about39.8x, but both absolute proxies remain tiny (3.19e-18 ->1.27e-16); the ratio does not establish usable computation. QFT50 on35 is a clear regression: E +8.394% and makespan266.162 ->325.543ms. alu-v0_27 on11 also regresses in a high-proxy regime, from0.882063 to0.874331.')
heading('Where the modeled improvement comes from')
budgetkeys=[(4,'next_events_h1','legacy_exact'),(4,'next_events_h4','legacy_exact'),(4,'next_events_h8','legacy_exact'),(5,'sum_distance','phase04_reference'),(5,'composite_bottleneck_expanded','phase04_reference'),(5,'composite_bottleneck_expanded','sum_distance_expanded')]
br=[]
for k in budgetkeys:
    s=get(*k);r={'comparison':'P'+str(k[0])+' '+k[1]+' vs '+k[2]}
    for t in TERMS:r[t]=f"{s['mean_delta_'+t]:+.6g}"
    br.append(r)
table(br,[('comparison','Comparison')]+[(t,t.replace('E_','')) for t in TERMS])
para('Mean percentage change and mean additive change weight targets differently. Phase4 h4 has mean target-relative E -0.808%, yet sum delta E +10.571: large absolute regressions on long QFT circuits outweigh smaller-circuit gains in the summed-error view. This is not a contradiction, and a sum of E across separate circuits is not a measured joint success probability. Both views and all cases are retained.')
para('The native CZ term is unchanged for every matched target. Cooling is disabled and contributes zero. Movement-loss differences are below1e-170 in magnitude here and negligible; they are not a driver of gains. Most net E changes are due to modeled decoherence exposure, followed by transfer counts, with smaller heating-gate effects. These are additive accounting differences under this model, not isolated causal hardware experiments.')
heading('Phase 6: what it improves and what evidence exists')
para('Phase 5 chooses locally promising assignments; Phase 6 tries bounded repairs and accepts only a strict improvement in complete Phase 3 E. Candidate changes include pair orientation, another legal pair slot, a pair-slot exchange, and a different idle parking destination. It ranks costly transitions, regenerates the circuit, verifies that the chosen prefix is unchanged, validates and scores the complete result, and retains the existing schedule when a candidate is invalid, tied or worse.')
para('Small permits four full candidate evaluations; standard permits twelve, with explicit route and neighborhood limits. Rejected trials count toward time and budget. The implementation recompiles the entire circuit with checked prefix equivalence rather than claiming cheap snapshot resume. This can be substantially more expensive in time and memory.')
table([{'start':'corrected sum-distance','budget':'small','btw':'7/13/0','mean':'-0.1278%','time':'0.2459 s'},{'start':'corrected sum-distance','budget':'standard','btw':'12/8/0','mean':'-0.4919%','time':'0.6978 s'},{'start':'expanded composite','budget':'small','btw':'7/13/0','mean':'-0.4053%','time':'0.2516 s'},{'start':'expanded composite','budget':'standard','btw':'12/8/0','mean':'-0.7431%','time':'0.6973 s'}],[('start','Starting policy'),('budget','Pilot budget'),('btw','Better/tie/worse,20 pairs'),('mean','Mean E change'),('time','Median additional repair time')])
para('These Phase 6 numbers are the existing small pilot, not completed full-matrix results. Each row has20 case/seed pairs with10 evaluation circuits and two routing seeds; historical benchmark circuits in the pilot are regression cases. No worsening is a consequence of strict acceptance relative to its own starting policy, not a promise of an improvement or lower compilation cost.')
para('Saved full-run snapshot at report creation: Phase6 v1 has42 successful targets and24 out-of-memory targets under the monitored4GiB limit;336 of528 configured rows are accepted and the matrix is incomplete. Phase6 v2 state is '+str(phase6status['v2'].get('state'))+' as of '+str(phase6status['v2'].get('updated_utc'))+'. Its evolving results are not included in the Phase4/5 comparisons. No Phase6 benchmark was launched, resumed or changed for this analysis; the lightweight postprocessing process uses idle priority during plotting.')
heading('Validation performed for this report')
para('Rechecked all previous Phase5 and Phase1/3/4 analysis-artifact hashes, source CSV hashes against prior audits, frozen manifest digests, complete matrices, all inline acceptance fields, matched inputs/geometry/layout/profile, exact unchanged controls, all660 Phase5 variant instruction hashes,66 matching Phase4-h4/Phase5-reference instruction files and scores,594 prefix-heating checks, and132 committed worker records against CSV values. Every prior Phase5 summary was recomputed and agrees. This is an artifact and arithmetic audit, not another full physical validation replay of1188 rows.')
heading('Limits and next defensible comparisons')
para('The evaluation uses analytical uncalibrated independent-error factors, declared two-plane geometry, no cooling and normalized CZ skeleton timing. Original one-qubit timing, device measurements and exact manuscript reproduction are outside scope. Shared cases across grids and related QFT sizes are not independent workloads. Small timing differences have no statistical-significance claim. A larger F ratio on an already tiny F needs its absolute values shown.')
para('Retain corrected sum-distance and expanded composite as distinct starting controls. Judge composite versus distance at the same candidate budget. Judge repair against its exact own pre-repair schedule under the same evaluator, and include failures, all rejected work and memory limits. Do not select a per-circuit best horizon or variant and report that as a deployable compiler.')
heading('Files and reproducibility')
para('report.md and report.html contain this narrative. phase4_all396.csv and phase5_all792.csv retain every source row byte-for-byte. paired_cases.csv contains all1122 per-target comparison rows; paired_summary.csv includes overall, family, grid and family-by-grid summaries plus a clearly post-hoc baseline-F>=0.5 diagnostic. variant_statistics.csv records medians, aggregate error terms and assignment-stage timings. phase4_analysis and phase5_analysis are exported asPNG/SVG/PDF; analysis_figures.pdf combines the figures.')
para('Prior detailed Phase5 report: ../phase_05/full_analysis_02/report.md. Prior Phase1/3/4 report: ../final_benchmark_analysis_01/report.md. Phase6 pilot: ../phase_06/pilot_results.md. The existing reports and all frozen benchmark data are unchanged.')
(OUT/'report.md').write_text('\n'.join(md),encoding='utf-8')
style='body{font:16px/1.6 system-ui,sans-serif;color:#213044;background:#f7f8fa;margin:0}main{max-width:1250px;margin:32px auto;padding:40px;background:white;border-radius:12px}h1,h2{line-height:1.25;color:#16324f}h2{margin-top:38px}p{max-width:1100px}.table{overflow:auto;margin:20px 0}table{border-collapse:collapse;font-size:13px;width:100%}th,td{padding:9px 11px;border-bottom:1px solid #dce1e7;text-align:left;vertical-align:top}th{background:#edf2f7}tr:nth-child(even){background:#fafbfd}img{max-width:100%;height:auto}figure{margin:24px 0}figcaption{font-size:13px;color:#637083}@media print{body,main{background:white;margin:0;padding:10px}h2{break-after:avoid}.table,figure{break-inside:avoid}}'
(OUT/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase4/5 detailed benchmark analysis</title><style>'+style+'</style><main>'+''.join(web)+'</main></html>',encoding='utf-8')
checks['source_files_unchanged_after_analysis']=all(sha(ROOT/p)==v for p,v in sources.items())
checks['previous_reports_unchanged_after_analysis']=all(all(sha(folder/k)==v for k,v in read(folder/'artifact_sha256.json').items()) for folder in [P5,OLD])
checks['all1122_pair_rows_exported']=len(rows(OUT/'paired_cases.csv'))==1122
checks['source_csv_copies_exact']=sha(OUT/'phase4_all396.csv')==sha(S4/'results.csv') and sha(OUT/'phase5_all792.csv')==sha(S5/'results.csv')
assert all(checks.values()),checks
evidence={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sources,'committed_record_sha256':record_hashes,'previous_phase5_report':str(P5.relative_to(ROOT)),'phase6_status_snapshot':phase6status,'no_compiler_rerun':True,'no_full_physics_replay':True}
(OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
(OUT/'verification.json').write_text(json.dumps({'passed':True,'checks':checks,'phase4_rows':396,'phase5_rows':792,'paired_case_rows':1122,'summary_rows':len(summaries)},indent=2)+'\n',encoding='utf-8')
artifacts={str(p.relative_to(OUT)):sha(p) for p in OUT.iterdir() if p.is_file()}
(OUT/'artifact_sha256.json').write_text(json.dumps(artifacts,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'saved':str(OUT),'passed':True,'checks':len(checks),'phase4_rows':396,'phase5_rows':792,'paired_case_rows':1122,'summary_rows':len(summaries)},indent=2))
