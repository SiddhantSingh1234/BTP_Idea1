"""Regenerate bounded completion-study statistics, tables, figures and Markdown.

Routing seeds are paired repetitions, not independent circuits. QAOA graph and
QV generator identities remain clustered across depth. Censored timings are
kept separately and are never substituted for completed runtimes or quality.
"""
import argparse
from collections import Counter, defaultdict
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools'), str(ROOT/'analysis')]
sys.dont_write_bytecode = True
import numpy as np
from phase08_incremental import read, rows, write, csvsave
from audit_idea1_completion import sha

STUDY = ROOT/'runs/remaining_experiments_6h_v2'
FOLLOWUP = ROOT/'runs/idea1_completion_followup_v1'
HARDWARE = ROOT/'reports/phase_08/hardware_counterfactual_02'


def clustered_summary(pairs):
    """Average depths and routing seeds inside generator; bootstrap generators."""
    if not pairs: return {'paired_rows': 0}
    grouped = defaultdict(list)
    for p in pairs: grouped[p['cluster']].append(p)
    values = np.array([statistics.mean(p['relative_E_percent'] for p in g) for g in grouped.values()])
    rng = np.random.default_rng(81031)
    indices = rng.integers(0, len(values), size=(10000, len(values)))
    lo, hi = np.quantile(values[indices].mean(axis=1), [.025, .975])
    return {'paired_rows': len(pairs), 'circuit_ids': len({p['case_id'] for p in pairs}),
            'generator_clusters': len(grouped), 'better': sum(p['delta_E'] < -1e-12 for p in pairs),
            'tie': sum(abs(p['delta_E']) <= 1e-12 for p in pairs), 'worse': sum(p['delta_E'] > 1e-12 for p in pairs),
            'equal_generator_mean_relative_E_percent': float(values.mean()),
            'cluster_bootstrap95_low': float(lo), 'cluster_bootstrap95_high': float(hi),
            'summed_E_change_percent': 100*sum(p['delta_E'] for p in pairs)/sum(p['control_E'] for p in pairs),
            'bootstrap_replicates': 10000, 'bootstrap_seed': 81031,
            'uncertainty_scope': 'descriptive selected-corpus stability; 2 generators per new family is too few for population inference; no model/device uncertainty'}


def cluster_for(case):
    generator, family = case.get('generator', {}), case['family']
    if family == 'qaoa': return f"qaoa:N{case['circuit']['num_qubits']}:graph{generator['graph_seed']}"
    if family == 'quantum_volume':
        seed = generator.get('generator_seed', generator.get('seed'))
        assert seed is not None
        return f"qv:N{case['circuit']['num_qubits']}:generator{seed}"
    return family + ':' + case['case_id']


def pair(row, control, case, comparison):
    new, base = float(row['extended_E']), float(control['extended_E'])
    assert row['case_id'] == control['case_id'] and row['seed'] == control['seed']
    assert row['normalized_sha256'] == control['normalized_sha256']
    if row.get('grid') and control.get('grid'): assert row['grid'] == control['grid']
    if row.get('profile_sha256') and control.get('profile_sha256'):
        assert row['profile_sha256'] == control['profile_sha256']
    result={'comparison': comparison, 'case_id': row['case_id'], 'family': case['family'],
            'cluster': cluster_for(case), 'seed': row['seed'], 'control_E': base, 'new_E': new,
            'delta_E': new-base, 'relative_E_percent': 100*(new/base-1),
            'new_id': row['id'], 'control_id': control['id']}
    terms=['E_native_gate','E_transfer','E_heating_gate','E_movement_loss','E_cooling_gate','E_decoherence']
    if all(row.get(k) and control.get(k) for k in terms):
        for key in terms:result['delta_'+key]=float(row[key])-float(control[key])
        assert abs(result['delta_E_native_gate'])<1e-9
        assert abs(sum(result['delta_'+k] for k in terms)-result['delta_E'])<1e-9
    return result


def summarize_groups(pairs, key='comparison'):
    output = []
    for value in sorted({p[key] for p in pairs}):
        selected = [p for p in pairs if p[key] == value]
        for family in ['all'] + sorted({p['family'] for p in selected}):
            group = selected if family == 'all' else [p for p in selected if p['family'] == family]
            output.append({key: value, 'family': family, **clustered_summary(group)})
    return output


def table_markdown(data, keys):
    def cell(v): return f'{v:.4f}' if isinstance(v, float) else str(v)
    return '\n'.join(['| '+' | '.join(keys)+' |', '| '+' | '.join(['---']*len(keys))+' |']+
                     ['| '+' | '.join(cell(r.get(k, '')) for k in keys)+' |' for r in data])


def plots(out, weighting, assignment, hardware, scaling):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figures = out/'figures'; figures.mkdir()
    plt.rcParams.update({'font.size': 9, 'svg.fonttype': 'none', 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, data, title in zip(axes, [weighting, assignment, hardware],
                               ['Weighting / gamma controls', 'Remove one assignment term', 'Replan under matched hardware profile']):
        subset = [r for r in data if r['family']=='all']
        ys = list(range(len(subset)))
        mid = np.array([r['equal_generator_mean_relative_E_percent'] for r in subset])
        low = np.array([r['cluster_bootstrap95_low'] for r in subset])
        high = np.array([r['cluster_bootstrap95_high'] for r in subset])
        ax.errorbar(mid, ys, xerr=np.vstack((np.maximum(0, mid-low), np.maximum(0, high-mid))), fmt='o', capsize=3)
        ax.set_yticks(ys, [r['comparison'].replace('critical_vs_uniform_', '').replace('without_', '') for r in subset])
        ax.axvline(0, color='grey', lw=.8); ax.invert_yaxis(); ax.set_title(title)
        ax.set_xlabel('Change in E (%)')
        ax.grid(axis='x', alpha=.2)
    fig.suptitle('Equal circuit/generator means; 95% descriptive cluster-bootstrap intervals', fontsize=10)
    fig.tight_layout(rect=(0,0,1,.95))
    for ext in ['svg', 'pdf', 'png']: fig.savefig(figures/f'controlled_effects.{ext}', dpi=220, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    colors = dict(zip(['rft_snapshot','rft_corrected','proposed_small','dasatom_corrected'], ['#555555','#0072B2','#D55E00','#009E73']))
    for label, color in colors.items():
        for outcome, marker in [('ok','o'),('timeout','^')]:
            subset = [r for r in scaling if r['variant']==label and r['status']==outcome]
            if subset:
                axes[0].scatter([int(r['N']) + (.2 if r['seed']=='43' else -.2) for r in subset],
                                [float(r['process_wall_seconds']) for r in subset], color=color, marker=marker,
                                facecolors=color if outcome=='ok' else 'none', label=label+(' completed' if outcome=='ok' else ' censored'), s=24)
                axes[1].scatter([int(r['N']) for r in subset], [float(r['observed_family_peak_bytes'])/(1024**3) for r in subset], color=color,
                                marker=marker,facecolors=color if outcome=='ok' else 'none',label=label+(' completed' if outcome=='ok' else ' censored'),s=24)
    axes[0].set_ylabel('Observed process-family wall seconds\nTriangles = right-censored, not completed runtime')
    axes[1].set_ylabel('Observed family peak working set (GiB)')
    for ax in axes: ax.set_xlabel('QFT qubits, fixed 11×11 geometry'); ax.grid(alpha=.2)
    axes[0].set_yscale('log'); axes[0].legend(fontsize=6); axes[1].legend(fontsize=7)
    fig.suptitle('Initial predeclared limits; follow-up outcomes are kept in a separate table')
    fig.tight_layout()
    for ext in ['svg','pdf','png']: fig.savefig(figures/f'scaling_censoring.{ext}', dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--initial-only', action='store_true', help='Interim analysis, never a final completion receipt')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT): raise ValueError('Fresh analysis output required')
    out.mkdir(parents=True)
    data, manifest = rows(STUDY/'results.csv'), read(STUDY/'manifest.json')
    assert len(data)==529 and all(r['status'] in {'ok','reused_quality','unsupported','timeout'} for r in data)
    assert read(HARDWARE/'verification.json')['results_sha256'] == sha(STUDY/'results.csv')
    jobs = {j['id']:j for j in manifest['jobs']}; by = {r['id']:r for r in data}
    cases = {j['case_id']:read(ROOT/j['case_path']) for j in manifest['jobs'] if j.get('case_path')}
    weighting, assignments = [], []
    for r in data:
        if r['suite']=='weighting':
            job = jobs[r['id']]
            if job['weight_mode']=='critical_remaining_depth':
                gamma = job['gamma']
                control = by[r['reference_id']] if gamma==.9 else by[f"weighting__{r['case_id']}__s{r['seed']}__uniform_gamma{gamma}"]
                weighting.append(pair(r, control, cases[r['case_id']], f'critical_vs_uniform_gamma{gamma}'))
            else:
                weighting.append(pair(r, by[r['reference_id']], cases[r['case_id']], f"uniform_gamma{job['gamma']}_vs0.9"))
        elif r['suite']=='assignment':
            assignments.append(pair(r, by[r['reference_id']], cases[r['case_id']], r['variant']))
    weight_summary, assignment_summary = summarize_groups(weighting), summarize_groups(assignments)
    hwpairs = rows(HARDWARE/'profile_matched_pairs.csv')
    for r in hwpairs:
        r.update(family=cases[r['case_id']]['family'], cluster=cluster_for(cases[r['case_id']]), comparison=r['variant'])
        for k in ['control_E','new_E','delta_E','relative_E_percent']: r[k]=float(r[k])
    hardware_summary = summarize_groups(hwpairs)
    for r in hardware_summary:
        selected = [p for p in hwpairs if p['comparison']==r['comparison'] and (r['family']=='all' or p['family']==r['family'])]
        r['decision_sequences_changed'] = sum(p['decision_sequence_changed'].lower()=='true' for p in selected)
    workload = [r for r in data if r['suite']=='workloads']; wb = {(r['case_id'],r['seed'],r['variant']):r for r in workload}
    primary = []
    for case, seed in sorted({(r['case_id'],r['seed']) for r in workload}):
        for new, control in [('proposed_small','rft_snapshot'), ('proposed_small','rft_corrected'),
                             ('proposed_small','dasatom_corrected'), ('rft_corrected','rft_snapshot')]:
            primary.append(pair(wb[case,seed,new], wb[case,seed,control], cases[case], new+'_vs_'+control))
    primary_summary = summarize_groups(primary)
    stages=[]
    for r in data:
        if r['status']!='ok': continue
        stages.append({'measurement_cohort':'initial',**{k:r[k] for k in ['id','suite','case_id','variant','seed','N','CZ','process_wall_seconds',
                      'compile_validate_repair_seconds','observed_family_peak_bytes','event_index_build_seconds',
                      'event_index_reachable_bytes','legacy_RFT_build_seconds','legacy_RFT_reachable_bytes',
                      'assignment_candidate_seconds','assignment_cost_seconds','assignment_matching_seconds',
                      'candidate_evaluations','accepted_repairs','timing_scope']}})
    initialscale = [dict(r, N=cases[r['case_id']]['circuit']['num_qubits']) for r in data if r['suite']=='scale']
    follow = []
    finalscale = initialscale[:]
    if not args.initial_only:
        follow = rows(FOLLOWUP/'results.csv')
        assert len(follow)==30 and all(r['status'] in {'ok','timeout','unsupported','error','out_of_memory','invalid'} for r in follow)
        assert {r['id'] for r in follow} == {r['id'] for r in initialscale if r['status']=='timeout'}
        fby = {r['id']:r for r in follow}
        finalscale = [dict(fby.get(r['id'],r), N=r['N'], initial_status=r['status'],
                           completion_source='followup' if r['id'] in fby else 'initial') for r in initialscale]
        csvsave(out/'scale_cap_followup.csv', follow)
        for r in follow:
            if r['status']=='ok':
                stages.append({**{k:r.get(k,'') for k in stages[0]},'measurement_cohort':'cap_only_followup'})
    csvsave(out/'scale_initial_ledger.csv', initialscale);csvsave(out/'scale_final_ledger.csv', finalscale)
    scale_summary=[]
    for scope, table in [('initial_caps',initialscale),('after_cap_only_followup',finalscale)]:
        for variant in sorted({r['variant'] for r in table}):
            selected=[r for r in table if r['variant']==variant]; good=[r for r in selected if r['status']=='ok']
            scale_summary.append({'scope':scope,'variant':variant,'planned':len(selected),
                'ok':0,'timeout':0,'out_of_memory':0,
                **dict(Counter(r['status'] for r in selected)),
                'completed_median_wall_seconds':statistics.median(float(r['process_wall_seconds']) for r in good) if good else None,
                'completed_max_observed_peak_GiB':max(float(r['observed_family_peak_bytes'])/(1024**3) for r in good) if good else None,
                'all_attempts_max_observed_peak_GiB':max(float(r['observed_family_peak_bytes'])/(1024**3) for r in selected),
                'min_cap_seconds':min(float(r['timeout']) for r in selected),'max_cap_seconds':max(float(r['timeout']) for r in selected),
                'qualification':'completed-only timing; different method caps; no equal-cap solved-rate or uncensored runtime claim'})
    scale_pairs=[]; sb={(r['case_id'],r['seed'],r['variant']):r for r in finalscale}
    for case,seed in sorted({(r['case_id'],r['seed']) for r in finalscale}):
        for new,control in [('proposed_small','rft_snapshot'),('proposed_small','rft_corrected'),('proposed_small','dasatom_corrected')]:
            a,b=sb[case,seed,new],sb[case,seed,control]
            if a['status']==b['status']=='ok': scale_pairs.append(pair(a,b,cases[case],new+'_vs_'+control))
    scale_quality_summary=summarize_groups(scale_pairs)
    storage=[]
    for r in initialscale:
        worker=(ROOT/r['record_path']).parent/'worker'
        for label in ['baseline','final']:
            path=worker/label/'compilation.json'
            if path.exists(): storage.append({'id':r['id'],'N':r['N'],'seed':r['seed'],'variant':r['variant'],
                'status':r['status'],'artifact':label+'/compilation.json','bytes':path.stat().st_size,
                'meaning':'serialized diagnostic/prefix snapshot size, not minimal compiler space complexity'})
    for name,table in [('weighting_pairs',weighting),('weighting_summary',weight_summary),('assignment_term_pairs',assignments),
                       ('assignment_term_summary',assignment_summary),('hardware_summary',hardware_summary),
                       ('new_workload_pairs',primary),('new_workload_summary',primary_summary),('runtime_stages',stages),
                       ('scale_summary',scale_summary),('scale_quality_pairs',scale_pairs),('scale_quality_summary',scale_quality_summary),
                       ('snapshot_storage',storage)]: csvsave(out/(name+'.csv'),table)
    budgets=[]
    for cohort,table in [('initial',data),('cap_only_followup',follow)]:
        for r in table:
            if r['status']!='ok':continue
            E=float(r['extended_E'])
            entry={k:r.get(k,'') for k in ['id','suite','case_id','variant','seed','N','CZ','grid','extended_E','makespan_us',
                'E_native_gate','E_transfer','E_heating_gate','E_movement_loss','E_cooling_gate','E_decoherence']}
            entry.update(measurement_cohort=cohort,native_gate_share_percent=100*float(r['E_native_gate'])/E,
                         transport_sensitive_E=E-float(r['E_native_gate']))
            budgets.append(entry)
    csvsave(out/'error_budget_rows.csv',budgets)
    cooling=rows(HARDWARE/'finite_cooling_cases.csv');csvsave(out/'finite_cooling_cases.csv',cooling)
    park=[]
    for r in data:
        if r['status']=='ok' and r['parking_calls']:
            park.append({'id':r['id'],'family':cases[r['case_id']]['family'], 'suite':r['suite'],
                         'parking_calls':int(r['parking_calls']), 'eviction_calls':int(r['eviction_calls'])})
    csvsave(out/'parking_opportunities.csv',park)
    summary={'status':'initial_analysis_only' if args.initial_only else 'ok', 'script_sha256':sha(__file__),
        'input_sha256': {str(p.relative_to(ROOT)):sha(p) for p in [STUDY/'manifest.json',STUDY/'results.csv',HARDWARE/'profile_matched_pairs.csv',HARDWARE/'finite_cooling_cases.csv']},
        'initial_status_counts':dict(Counter(r['status'] for r in data)), 'followup_status_counts':dict(Counter(r['status'] for r in follow)),
        'weighting':weight_summary,'assignment_terms':assignment_summary,'hardware':hardware_summary,
        'new_workloads':primary_summary,'scale':scale_summary,'scale_quality':scale_quality_summary,
        'new_workload_units':{'case_ids':8,'paired_case_seeds':24,'generator_clusters':4,'per_family_generator_clusters':2,'routing_seeds':[41,42,43]},
        'cooling_status_counts':dict(Counter(r['status'] for r in cooling)),
        'complete_scope':'finite, predeclared analytical benchmark; terminal censored/unsupported cells remain results; no population/device generalization'}
    if follow: summary['input_sha256'][str((FOLLOWUP/'results.csv').relative_to(ROOT))]=sha(FOLLOWUP/'results.csv')
    write(out/'summary.json',summary)
    plots(out,weight_summary,assignment_summary,hardware_summary,initialscale)
    contents=['# Bounded completion-study analysis',
        'This analysis preserves the initial caps and all outcomes. Lower E is better. E is the negative log of an analytical success proxy on the normalized CZ skeleton, not measured device fidelity.',
        'Status: '+summary['status']+'. Original campaign: '+str(summary['initial_status_counts'])+'. Cap-only follow-up: '+str(summary['followup_status_counts'])+'.',
        '## Weighting and discount controls',
        'Critical-depth weights are compared with uniform weights at the same gamma; discount controls use uniform gamma=.9. Means average routing seeds within generator/circuit first. Intervals describe this small selected corpus and are not confirmatory multi-comparison significance tests.',
        table_markdown([r for r in weight_summary if r['family']=='all'], ['comparison','paired_rows','generator_clusters','better','tie','worse','equal_generator_mean_relative_E_percent','cluster_bootstrap95_low','cluster_bootstrap95_high']),
        '## Assignment terms',
        'Each term is removed separately. A positive change means its removal worsened E; a negative change means removal helped. No winner is substituted into the frozen proposed method.',
        table_markdown([r for r in assignment_summary if r['family']=='all'], ['comparison','paired_rows','better','tie','worse','equal_generator_mean_relative_E_percent','cluster_bootstrap95_low','cluster_bootstrap95_high']),
        '## Profile-driven replanning',
        'The control decisions are retimed and rescored under exactly the same changed profile and geometry as the replanned result. Grid20/35 expands parking area with the same six static slots. Cooling is a separate finite-resource transform of a fixed synthetic route.',
        table_markdown([r for r in hardware_summary if r['family']=='all'], ['comparison','paired_rows','decision_sequences_changed','better','tie','worse','equal_generator_mean_relative_E_percent']),
        '## Larger/deeper genuine QAOA and QV inputs',
        'N=10/12; QAOA p=2/4 with graph seed900+N; QV depth8/16 with generator seed1000+N; routing seeds41–43. Depth variants share a generator and remain in one cluster. There are only two generator identities per family, four overall; intervals cannot support broad population claims.',
        table_markdown(primary_summary, ['comparison','family','paired_rows','generator_clusters','better','tie','worse','equal_generator_mean_relative_E_percent','cluster_bootstrap95_low','cluster_bootstrap95_high']),
        '## QFT65–100 scaling and censoring',
        'Eight sizes, two paired routing seeds, four methods, fixed11×11 geometry. A timeout contributes no final quality or completed runtime. Partial baseline snapshots are not relabelled completed proposed runs. Follow-up selection includes every initial timeout, with unchanged scientific source and larger declared caps; original timing evidence is retained.',
        table_markdown(scale_summary,['scope','variant','planned','ok','timeout','out_of_memory','completed_median_wall_seconds','all_attempts_max_observed_peak_GiB','min_cap_seconds','max_cap_seconds']),
        'Cross-method process wall includes imports/validation/artifacts, whose scope and snapshot sizes differ. It is descriptive operational cost, not a fair isolated algorithm speedup. Method-specific inner timers are not divided into cross-method speedup ratios.',
        'Quality below is conditional on both methods finishing; it is not a bound on censored cases.',
        table_markdown(scale_quality_summary,['comparison','paired_rows','better','tie','worse','equal_generator_mean_relative_E_percent']),
        '## Finite cooling resources',
        table_markdown(cooling,['banks','threshold','status','without_cooling_E','cooling_E','delta_E','cooling_episodes','without_cooling_makespan_us','cooling_makespan_us']),
        'All five unsupported outcomes exhaust prepared cold banks; no implicit refill is introduced. Successful cooling pays its added CZ/H, registration, preparation, transfer, carrier handoff and elapsed-time costs. This synthetic stress test is not evidence of general compiler or hardware advantage.',
        '## Regeneration and evidence',
        'All numeric tables are CSV beside this Markdown. Profile counterfactual recipes and hashes are in reports/phase_08/hardware_counterfactual_02. Independent schedule replay/provenance receipts are in reports/phase_07/completion_audit_02 and the follow-up audit. See runtime_stages.csv and snapshot_storage.csv for stage and storage evidence.',
        'Figures are exported as SVG/PDF/PNG under figures/. Scientific assumptions and source-literature limits remain those documented in the Idea1 claims ledger.']
    (out/'analysis.md').write_text('\n\n'.join(contents)+'\n',encoding='utf-8')
    print('Analysis saved to '+str(out.relative_to(ROOT)),flush=True)


if __name__=='__main__': main()
