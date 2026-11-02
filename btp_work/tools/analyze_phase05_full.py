"""Read-only integrity checks and paired interpretation of completed Phase05."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import model_comparison as service

PAIRS = [('sum_distance', 'phase04_reference'),
    ('bottleneck_distance', 'sum_distance'), ('bottleneck_time', 'sum_distance'),
    ('composite_sum', 'sum_distance'), ('composite_bottleneck', 'sum_distance'),
    ('sum_distance_expanded', 'sum_distance'),
    ('composite_bottleneck_expanded', 'sum_distance_expanded'),
    ('composite_bottleneck_expanded', 'sum_distance'),
    ('composite_bottleneck_expanded', 'phase04_reference'),
    ('composite_no_conflict', 'composite_bottleneck'),
    ('composite_no_future', 'composite_bottleneck'),
    ('phase04_reference', 'legacy_exact'),
    ('composite_bottleneck_expanded', 'legacy_exact')]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def csvsave(path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def compare(group, variant, control, label):
    records = []
    for target, values in group.items():
        v, c = values[variant], values[control]
        delta = float(v['extended_E']) - float(c['extended_E'])
        records.append({'target_id': target, 'group': label, 'variant': variant, 'control': control,
            'delta_E': delta, 'relative_E_percent': 100 * delta / float(c['extended_E']),
            'fidelity_ratio': math.exp(-delta),
            'makespan_ratio': float(v['extended_makespan_us']) / float(c['extended_makespan_us']),
            'compile_ratio': float(v['compile_seconds']) / float(c['compile_seconds'])})
    summary = {'group': label, 'variant': variant, 'control': control, 'n': len(records),
        'better': sum(x['delta_E'] < -1e-12 for x in records),
        'tie': sum(abs(x['delta_E']) <= 1e-12 for x in records),
        'worse': sum(x['delta_E'] > 1e-12 for x in records)}
    for field in ['relative_E_percent', 'fidelity_ratio', 'makespan_ratio', 'compile_ratio']:
        values = [x[field] for x in records]
        summary['median_' + field] = statistics.median(values)
        summary['mean_' + field] = statistics.mean(values)
        summary['min_' + field] = min(values)
        summary['max_' + field] = max(values)
    return summary, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh analysis output under btp_work')
    lock = service.acquire(ROOT / 'runs/model_comparison_execution.lock')
    if lock is None:
        raise ValueError('Wait until timed comparison is idle before analysis')
    try:
        study = ROOT / 'runs/phase05_matched_benchmark_v1'
        manifest = service.verify(study, runtime=True)
        source_hash = sha(study / 'results.csv')
        with (study / 'results.csv').open(encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle))
        checks = {}
        expected = {'original_phase3', 'legacy_exact', *manifest['variants']}
        by_target = defaultdict(dict)
        for row in rows:
            assert row['variant'] not in by_target[row['target_id']], 'Duplicate matrix row'
            by_target[row['target_id']][row['variant']] = row
        checks['complete_66_by_12_matrix'] = (len(rows) == 792 and len(by_target) == 66
            and all(set(v) == expected for v in by_target.values())
            and read(study / 'summary.json')['matrix_complete'])
        checks['all_rows_accepted'] = all(r['status'] == 'ok' and r['accepted_schedule'] == 'True'
            and r['attempt_status'] == 'ok' for r in rows)
        checks['common_profile'] = len({r['profile_sha256'] for r in rows}) == 1
        checks['matched_geometry_and_input'] = all(len({r['geometry_sha256'] for r in v.values()}) == 1
            and len({r['normalized_sha256'] for r in v.values()}) == 1 for v in by_target.values())
        checks['unchanged_controls_exact_instructions_and_rng'] = all(
            v['legacy_exact']['legacy_exact_instructions'] == 'True'
            and v['legacy_exact']['legacy_exact_rng'] == 'True'
            and float(v['legacy_exact']['extended_E']) == float(v['original_phase3']['extended_E'])
            for v in by_target.values())
        checks['all_594_assignment_prefix_heating_checks'] = sum(
            r['prefix_heating_matches_full_evaluator'] == 'True' for r in rows) == 594
        checks['all_660_variant_instruction_files_match'] = all(
            sha(ROOT / r['output'] / 'instructions.txt') == r['instructions_sha256']
            for r in rows if r['variant'] in manifest['variants'])
        checks['fixed_h4_and_gamma'] = all(r['h'] == '4' and float(r['gamma']) == .9
            for r in rows if r['variant'] in manifest['variants'])
        phase4 = ROOT / 'runs/phase04_matched_benchmark_v2'
        service.verify(phase4)
        with (phase4 / 'results.csv').open(encoding='utf-8', newline='') as handle:
            phase4_h4 = {r['target_id']: r for r in csv.DictReader(handle) if r['variant'] == 'next_events_h4'}
        checks['all_66_phase04_references_match_completed_phase04_h4'] = all(
            phase4_h4[target]['accepted_schedule'] == 'True'
            and phase4_h4[target]['profile_sha256'] == values['phase04_reference']['profile_sha256']
            and phase4_h4[target]['geometry_sha256'] == values['phase04_reference']['geometry_sha256']
            and float(phase4_h4[target]['extended_E']) == float(values['phase04_reference']['extended_E'])
            and sha(ROOT / phase4_h4[target]['output'] / 'instructions.txt') == values['phase04_reference']['instructions_sha256']
            for target, values in by_target.items())
        terms = ['E_native_gate', 'E_transfer', 'E_heating_gate', 'E_movement_loss', 'E_cooling_gate', 'E_decoherence']
        checks['all_error_budgets_add_up'] = all(math.isclose(sum(float(r[k]) for k in terms),
            float(r['extended_E']), rel_tol=1e-12, abs_tol=1e-12) for r in rows)
        checks['all_fidelity_proxies_equal_exp_minus_E'] = all(math.isclose(
            math.exp(-float(r['extended_E'])), float(r['extended_fidelity']), rel_tol=1e-12) for r in rows)
        record_checks = []
        for job in manifest['jobs']:
            accepted = [(p, r) for p, r in service.records(study, job['target_id']) if r['status'] == 'ok']
            assert len(accepted) == 1
            path, record = accepted[0]
            raw = record['result']['rows']
            assert len(raw) == 12
            for row in raw:
                saved = by_target[job['target_id']][row['variant']]
                for key in ['extended_E', 'extended_fidelity', 'extended_makespan_us', 'compile_seconds']:
                    assert float(row[key]) == float(saved[key]), (job['target_id'], row['variant'], key)
            record_checks.append({'record': str(path.relative_to(ROOT)), 'sha256': sha(path)})
        checks['all_csv_scores_and_timings_match_committed_worker_rows'] = len(record_checks) == 66
        assert all(checks.values()), checks
        summaries, comparisons = [], []
        groups = {'all': by_target}
        for field in ['grid', 'family']:
            for value in sorted({r[field] for r in rows}):
                groups[field + '=' + value] = {k: v for k, v in by_target.items()
                    if next(iter(v.values()))[field] == value}
        for label, group in groups.items():
            for variant, control in PAIRS:
                summary, records = compare(group, variant, control, label)
                summaries.append(summary)
                if label == 'all':
                    comparisons.extend(records)
        out.mkdir(parents=True)
        (out / 'analysis_script.py').write_bytes(Path(__file__).read_bytes())
        csvsave(out / 'paired_summary.csv', summaries)
        csvsave(out / 'paired_cases.csv', comparisons)
        csvsave(out / 'all_792_results.csv', rows)
        totals = []
        for variant in sorted(expected):
            subset = [v[variant] for v in by_target.values()]
            totals.append({'variant': variant, 'n': len(subset),
                'median_compile_seconds': statistics.median(float(r['compile_seconds']) for r in subset),
                'sum_compile_seconds': sum(float(r['compile_seconds']) for r in subset),
                'median_E': statistics.median(float(r['extended_E']) for r in subset),
                'median_fidelity': statistics.median(float(r['extended_fidelity']) for r in subset),
                'median_makespan_us': statistics.median(float(r['extended_makespan_us']) for r in subset),
                **{'sum_' + k: sum(float(r[k]) for r in subset) for k in terms}})
        csvsave(out / 'variant_statistics.csv', totals)
        full = [s for s in summaries if s['group'] == 'all']
        table = '| Variant | Control | Better / tie / worse | Median E change | Mean E change | Median compile ratio |\n| --- | --- | --- | --- | --- | --- |\n'
        for s in full:
            table += (f"| {s['variant']} | {s['control']} | {s['better']} / {s['tie']} / {s['worse']} | "
                f"{s['median_relative_E_percent']:+.3f}% | {s['mean_relative_E_percent']:+.3f}% | {s['median_compile_ratio']:.3f}x |\n")
        report = '''# Completed Phase 5 full benchmark interpretation

All 66 matched RFT targets and all 792 configured rows completed and were accepted. These are 66 case/grid targets (27 distinct circuits), not 792 independent circuits or repeated timing samples. The 12 rows per target are the saved original rescored under Phase 3, a fresh unchanged RFT timing control, the Phase 4 h4 reference, and nine assignment controls/variants. DasAtom was not recompiled.

## What the metrics mean

Every policy uses the frozen extended_no_cooling.v1 Phase 3 model and the same declared geometry for that target. E is the sum of negative-log error terms; lower is better. The fidelity proxy F = exp(-E) is higher when E is lower. A 1% decrease in E is not a one-percentage-point fidelity increase. Makespan is modeled circuit execution time in microseconds; compilation is classical CPU time in seconds. The common native-gate term is fixed by the circuit, so total-E percentages include an irreducible term that placement cannot improve.

Better/tie/worse uses an absolute E tolerance of 1e-12. Relative E changes are computed per matched target before taking their median/mean. Compilation ratios use fresh controls from the same attempt; the saved historical original compiler time is not used to infer speedups. Each new variant has one timed sample in fixed order, with warmup, so small time differences are descriptive and have no confidence-interval claim.

## Paired results

''' + table + '''
## Conclusions supported by the complete matrix

1. The corrected sum-distance pipeline improves E in 39/66 cases against Phase 4 h4, with median E change -0.536% and median compile cost 1.470x. This is the whole corrected pipeline, including orientation and prefix accounting; it does not isolate a novel composite objective.
2. Expanded composite versus Phase 4 improves 42, ties 2 and worsens 22. Median E changes by -0.745%, median fidelity ratio is 1.01358 (about 1.36% relative proxy improvement), median makespan ratio is 0.96062 (about 3.94% shorter), and median compile ratio is 1.526. These are separate paired medians, not a representative single circuit.
3. The objective comparison must hold candidate expansion fixed. Expanded composite versus expanded sum improves 30, ties 9 and worsens 27; median E change is zero and mean relative change is -0.514%. This is a modest, uneven average improvement, with nearly as many regressions as wins. It does not establish a universal advantage of the composite objective.
4. Expanding sum-distance candidates alone yields 30 improvements, 14 ties and 22 regressions against unexpanded sum. Candidate expansion is a separate contribution; the full expanded-composite gain cannot all be attributed to its cost formula.
5. Pure bottleneck distance and bottleneck time each win 21, tie 5 and lose 40 against corrected sum-distance. Locally reducing the largest assigned movement does not reliably minimize full-circuit error: subsequent parking, routing, batching and exposure still matter.
6. Composite at the original candidate budget is also mixed. Composite sum wins 18/ties 18/loses 30; composite bottleneck wins 20/ties 19/loses 27 against corrected sum. Fixed local surrogate costs do not guarantee full-E improvements.
7. Removing the conflict term improves 26, ties 23 and worsens 17 against full composite bottleneck, so that fixed conflict weighting is not consistently helpful here. Removing future cost improves 14, ties 33 and worsens 19, suggesting some benefit from the future term on this matrix, without proving it is always useful. These ablations use the original candidate budget and cannot directly establish the contribution inside the expanded variant.

Phase 5 supports keeping both corrected sum-distance and expanded composite as Phase 6 starting controls. Phase 6 tests whether bounded full-replay repair can retain only strict full-E improvements while accounting for all rejected work. Its two starting policies and repair caps were already declared in the completed Phase 6 pilot; this analysis does not tune them on these outcomes.

## Scope and evidence

The integrity audit verifies the complete matrix, all 66 exact unchanged instruction/RNG controls, all 66 Phase 4 reference instructions/scores against the completed Phase 4 h4 matrix, shared profiles and per-target geometry/input, all 594 assignment prefix-heating checks, all 660 newly compiled variant instruction hashes, additive error budgets, F = exp(-E), and CSV score/timing equality with the 66 committed successful worker records. This is an artifact/record consistency audit; it does not independently rerun 792 full physical validations. Failed/interrupted historical attempts remain preserved in the study.

These are analytical scores for normalized CZ skeletons, under declared two-plane geometry and uncalibrated noise assumptions. They do not demonstrate measured quantum-device fidelity, full original-circuit one-qubit timing, exact reproduction of the paper, or statistical generalization. The paper remains a separate original-model baseline comparison; it has no direct Phase 5 rows under this new model. Grid 20 contains only QFT cases, while grids 11 and 35 also contain Table II cases; cross-grid aggregate medians are not pure grid-size effects.

Files: paired_summary.csv includes overall, per-grid and per-family statistics; paired_cases.csv preserves each paired outcome; variant_statistics.csv contains all variant medians/totals and error terms; all_792_results.csv is the immutable source snapshot; verification.json and evidence.json bind this report to its inputs. paired_results.png/.svg/.pdf provide exportable figures. Original completed datasets and previous acceptance receipts are untouched.
'''
        (out / 'report.md').write_text(report, encoding='utf-8')
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        selected = full[:9]
        fig, axes = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={'width_ratios': [1.25, 1]})
        labels = [s['variant'] + '\nvs ' + s['control'] for s in selected]
        for index, s in enumerate(selected):
            axes[0].barh(index, s['better'], color='#23856b', label='Lower E' if index == 0 else None)
            axes[0].barh(index, s['tie'], left=s['better'], color='#aab2bd', label='Tie' if index == 0 else None)
            axes[0].barh(index, s['worse'], left=s['better'] + s['tie'], color='#c85b59', label='Higher E' if index == 0 else None)
        axes[0].set_yticks(range(len(labels)), labels, fontsize=8)
        axes[0].invert_yaxis()
        axes[0].set_xlim(0, 66)
        axes[0].set_xlabel('Matched targets (66 total; tolerance 1e-12 E)')
        axes[0].legend(loc='lower left', bbox_to_anchor=(0, 1), ncol=3, fontsize=8)
        points = [r for r in comparisons if r['variant'] == 'composite_bottleneck_expanded' and r['control'] == 'sum_distance_expanded']
        axes[1].scatter([r['relative_E_percent'] for r in points], [r['compile_ratio'] for r in points], s=25, alpha=.7, color='#275ea0')
        axes[1].axvline(0, color='grey', lw=.8)
        axes[1].axhline(1, color='grey', lw=.8)
        axes[1].set_xlabel('E change vs expanded sum-distance (%)\nLeft = lower modeled error')
        axes[1].set_ylabel('Compile time ratio (single sample)')
        axes[1].set_title('Expanded composite: objective-only comparison', fontsize=10)
        fig.suptitle('Phase 5: complete matched paper matrix, common Phase 3 model', fontsize=13)
        fig.tight_layout()
        for suffix in ['png', 'svg', 'pdf']:
            fig.savefig(out / ('paired_results.' + suffix), dpi=180, bbox_inches='tight')
        plt.close(fig)
        checks['source_csv_unchanged_during_analysis'] = sha(study / 'results.csv') == source_hash
        save(out / 'verification.json', {'passed': all(checks.values()), 'checks': checks,
            'scope': 'Artifact consistency and paired analysis; no new full physical replay'})
        save(out / 'evidence.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
            'study': str(study), 'manifest_sha256': sha(study / 'manifest.json'),
            'results_sha256': source_hash, 'attempt_records': record_checks,
            'phase04_results_sha256': sha(phase4 / 'results.csv'),
            'analysis_script_sha256': sha(__file__), 'fixed_model': next(iter({r['profile_sha256'] for r in rows}))})
        save(out / 'artifact_sha256.json', {p.name: sha(p) for p in out.iterdir() if p.is_file()})
        print(json.dumps({'passed': all(checks.values()), 'targets': len(by_target), 'rows': len(rows), 'report': str(out / 'report.md')}))
    finally:
        service.release(lock)


if __name__ == '__main__':
    main()
