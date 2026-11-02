"""Audit/replay immutable Phase05 pilot evidence and export honest comparisons."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from implementation.movement_error.evaluator import evaluate
from implementation.validation.checker import line_compatible


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def comparison(rows, variant, control):
    lookup = {(r['case'], r['seed'], r['variant']): r for r in rows}
    values = []
    for row in rows:
        if row['variant'] != variant:
            continue
        other = lookup[row['case'], row['seed'], control]
        if row['accepted_schedule'] and other['accepted_schedule'] and row['E'] is not None and other['E'] is not None:
            values.append((row['E'] - other['E'], 100 * (row['E'] / other['E'] - 1)))
    return {'variant': variant, 'control': control, 'compared': len(values),
            'better': sum(d < -1e-12 for d, _ in values), 'tie': sum(abs(d) <= 1e-12 for d, _ in values),
            'worse': sum(d > 1e-12 for d, _ in values),
            'mean_relative_E_change_percent': statistics.mean(p for _, p in values),
            'minimum_relative_E_change_percent': min(p for _, p in values),
            'maximum_relative_E_change_percent': max(p for _, p in values)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh audit directory under btp_work')
    out.mkdir(parents=True)
    started = time.perf_counter()
    sources = [ROOT / 'runs/phase_05/development_01', ROOT / 'runs/phase_05/pilot_01']
    replay = []
    oriented = 0
    exact_matrix_optima = 0
    mutual_conflict_batches = 0
    resource_peaks = []
    dimensions = []
    raw_bytes = 0
    artifact_hashes = {}
    for source in sources:
        result = read(source / 'pilot_results.json')
        for name, expected in result['artifact_sha256'].items():
            if sha(ROOT / name) != expected:
                raise AssertionError('Compiled artifact changed: ' + name)
        for record_path in sorted((source / 'raw').glob('*/attempt_*/attempt_record.json')):
            record = read(record_path)
            if record['status'] != 'ok':
                raise AssertionError('Worker failed: ' + str(record_path))
            resource_peaks.append(record['peak_working_set_bytes'])
            for name, expected in record['worker_artifact_sha256'].items():
                path = record_path.parent / name
                if sha(path) != expected:
                    raise AssertionError('Raw artifact changed: ' + str(path))
                raw_bytes += path.stat().st_size
            artifact_hashes[str(record_path.relative_to(ROOT))] = sha(record_path)
        for row in result['rows']:
            directory = ROOT / row['raw_directory']
            old = read(directory / 'evaluation.json')
            schedule = read(directory / 'schedule.json')
            fresh = evaluate(schedule, include_audit=False)
            if fresh['status'] != 'ok' or fresh['budget'] != old['budget']:
                raise AssertionError('Full replay differs')
            compilation = read(directory / 'compilation.json')
            batches = {(batch['logical_layer'], tuple(batch['active_gate_ids'])): batch for batch in compilation['batches']}
            for assignment in compilation['assignment_records']:
                if not assignment.get('rows_assigned'):
                    continue
                costs = assignment['cost_matrix']
                m, s = len(costs), len(costs[0])
                dimensions.append([m, s])
                batch = batches[assignment['logical_layer'], tuple(assignment['active_gate_ids'])]
                targets = batch['committed_active_targets']
                current = batch['current_positions']
                chosen_values = []
                row_moves = []
                for entry in assignment['selected']:
                    pair = assignment['pairs'][entry['row']]
                    slot = assignment['candidate_slots'][entry['column']]
                    scored_targets = slot if entry['orientation'] == 0 else slot[::-1]
                    if entry['targets'] != scored_targets:
                        raise AssertionError('Stored/scored orientation disagrees')
                    if [targets[str(q)] for q in pair] != scored_targets:
                        raise AssertionError('Applied orientation disagrees')
                    if not assignment['legal_mask'][entry['row']][entry['column']]:
                        raise AssertionError('Forbidden edge selected')
                    if costs[entry['row']][entry['column']] != entry['cost']:
                        raise AssertionError('Materialized cost differs')
                    chosen_values.append(entry['cost'])
                    row_moves.append([(current[str(q)], dest) for q, dest in zip(pair, scored_targets)
                                      if str(q) in current and current[str(q)] != dest])
                    oriented += 1
                mutual = sum(not line_compatible(a, b, c, d)
                    for i, moves in enumerate(row_moves) for other in row_moves[i + 1:]
                    for a, b in moves for c, d in other)
                mutual_conflict_batches += int(mutual > 0)
                if m <= 6 and s <= 8:
                    # Independent permutations over the ACTUAL frozen matrix.
                    optimum = None
                    objective = compilation['assignment_options']['objective']
                    for columns in itertools.permutations(range(s), m):
                        values = [costs[i][c] for i, c in enumerate(columns)]
                        if any(x is None for x in values):
                            continue
                        key = (max(values), math.fsum(values)) if objective == 'bottleneck_sum' else (math.fsum(values),)
                        if optimum is None or key < optimum:
                            optimum = key
                    actual = (max(chosen_values), math.fsum(chosen_values)) if objective == 'bottleneck_sum' else (math.fsum(chosen_values),)
                    if optimum is None or any(abs(a - b) > 1e-10 for a, b in zip(actual, optimum)):
                        raise AssertionError('Actual matrix assignment not optimal')
                    exact_matrix_optima += 1
            replay.append({'case': row['case'], 'variant': row['variant'], 'seed': row['seed'],
                'split': result['split'], 'status': fresh['status'], 'budget_identical': True,
                'schedule_sha256': sha(directory / 'schedule.json'),
                'compilation_sha256': sha(directory / 'compilation.json'),
                'raw_directory': row['raw_directory']})
    final = read(sources[1] / 'pilot_results.json')
    rows = final['rows']
    pairs = [('composite_sum', 'sum_distance'), ('bottleneck_distance', 'sum_distance'),
             ('bottleneck_time', 'sum_distance'), ('composite_bottleneck', 'sum_distance'),
             ('composite_bottleneck_expanded', 'sum_distance_expanded'),
             ('composite_bottleneck_all', 'sum_distance_all'),
             ('composite_bottleneck_expanded', 'sum_distance'),
             ('composite_bottleneck_expanded', 'phase04_reference'),
             ('composite_bottleneck_expanded', 'original_legacy'),
             ('sum_distance', 'phase04_reference')]
    comparisons = [comparison(rows, a, b) for a, b in pairs]
    legacy = read(ROOT / 'runs/phase_04/pilot_03/pilot_results.json')
    previous = {(r['case'], r['seed'], r['variant']): r for r in legacy['rows']}
    legacy_checks = []
    for row in rows:
        old_variant = {'original_legacy': 'legacy_exact', 'phase04_reference': 'next_events_h4'}.get(row['variant'])
        if old_variant is None or (row['case'], row['seed'], old_variant) not in previous:
            continue
        old = previous[row['case'], row['seed'], old_variant]
        equal = row['instructions_sha256'] == old['instructions_sha256']
        if not equal:
            raise AssertionError('Historical control changed')
        legacy_checks.append({'case': row['case'], 'variant': row['variant'], 'seed': row['seed'], 'exact_instructions': equal})
    value = {'status': 'ok', 'replayed_schedules': len(replay), 'all_budgets_identical': True,
        'fresh_compile_attempts': 0, 'actual_matrix_optima_checked': exact_matrix_optima,
        'applied_orientations_checked': oriented, 'batches_with_unmodeled_new_new_conflicts': mutual_conflict_batches,
        'historical_exact_controls': legacy_checks, 'comparisons': comparisons,
        'maximum_observed_process_family_peak_bytes': max(resource_peaks), 'raw_artifact_bytes': raw_bytes,
        'maximum_real_rows': max(m for m, _ in dimensions), 'maximum_candidate_columns': max(s for _, s in dimensions),
        'worker_attempt_sha256': artifact_hashes, 'records': replay,
        'replay_wall_seconds': time.perf_counter() - started, 'best_default_selected': False}
    write(out / 'audit.json', value)
    # Export the existing measurement files unchanged, not new timing samples.
    destination = ROOT / 'reports/phase_05'
    for name in ['pilot_results.csv', 'pilot_results.json']:
        if (destination / name).exists():
            if (destination / name).read_bytes() != (sources[1] / name).read_bytes():
                raise ValueError('Existing measurement export differs')
        else:
            shutil.copyfile(sources[1] / name, destination / name)
    os.environ['MPLCONFIGDIR'] = str(out / 'matplotlib_config')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    case_names = list(dict.fromkeys(row['case'] for row in rows))
    shown = [('composite_sum', 'sum_distance'), ('composite_bottleneck', 'sum_distance'),
             ('composite_bottleneck_expanded', 'sum_distance_expanded'),
             ('composite_bottleneck_all', 'sum_distance_all')]
    lookup = {(r['case'], r['seed'], r['variant']): r for r in rows}
    data = np.array([[statistics.mean(100 * (lookup[case, seed, variant]['E'] /
                     lookup[case, seed, control]['E'] - 1) for seed in (42, 43))
                     for variant, control in shown] for case in case_names])
    limit = max(abs(data.min()), abs(data.max()), 1)
    fig, ax = plt.subplots(figsize=(10, 7))
    plot = ax.imshow(data, cmap='RdBu_r', vmin=-limit, vmax=limit, aspect='auto')
    ax.set_xticks(range(len(shown)), ['Composite\nsum\nCoM', 'Composite\nbottleneck\nCoM',
                                     'Composite\nbottleneck\nExpanded', 'Composite\nbottleneck\nAll slots'])
    ax.set_yticks(range(len(case_names)), case_names)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f'{data[i, j]:+.1f}', ha='center', va='center', fontsize=8)
    ax.set_title('Phase05: error change versus corrected distance-sum at SAME candidate policy\nMean over two routing seeds; negative is better; analytical CZ-skeleton pilot')
    fig.colorbar(plot, ax=ax, label='Relative change in E (%)')
    fig.tight_layout()
    for suffix in ['png', 'svg']:
        fig.savefig(destination / ('pilot_results.' + suffix), dpi=160)
    plt.close(fig)
    # The measured context timing is diagnostic; do not present it as a speedup.
    lines = ['# Phase 05 fixed routed pilot', '',
        '[Protocol](../../configs/studies/phase05_pilot_v1.json), [CSV](pilot_results.csv), [JSON](pilot_results.json), '
        '[plot](pilot_results.png), [SVG](pilot_results.svg), [audit/replay](../../' + str(out.relative_to(ROOT)).replace('\\', '/') + '/audit.json).', '',
        'All **308 evaluation schedules** (11 cases x 2 routing seeds x 14 variants) pass the common independent validator and Phase03 evaluator. '
        'The separate development split has 56/56 accepted schedules. There are 462 evaluation timing samples and 112 development samples; '
        'same-seed timing repeats are not independent quality trials. Evaluation wall time was %.2fs. No weights were changed after development/evaluation outcomes.' % final['wall_seconds'], '',
        'The set includes QFT5/10/15, the full-register Table-II smoke, eviction/serialization fixtures, four unseen matching-layer circuits and '
        'one explicitly labelled static-assignment adversary. These are 11 instances, not 22 independent circuits or the final paper matrix.', '',
        '| Variant | Matched control | Better / tie / worse | Mean relative E change |', '| --- | --- | ---: | ---: |']
    for item in comparisons:
        lines.append('| ' + item['variant'] + ' | ' + item['control'] + ' | ' +
            str(item['better']) + ' / ' + str(item['tie']) + ' / ' + str(item['worse']) +
            ' | %+.3f%% |' % item['mean_relative_E_change_percent'])
    lines += ['', 'Candidate expansion and objective effects must be separated. The expanded composite objective improves 10/22 and worsens 4/22 '
        'relative to expanded distance-sum, with about 1.8% lower mean relative E. Against the original CoM corrected distance-sum it is mixed '
        '(6 better, 8 tied, 8 worse). The all-slot diagnostic has a larger candidate budget and is not a selected production default. '
        'The CoM-only composite variants show no consistent aggregate gain. Bottleneck distance/time alone is worse in 14/22 comparisons.',
        '', 'Orientation repair is not counted as a novel-objective improvement. Both original legacy and Phase04 h4 controls remain separate; '
        'all corrected/new controls share the repair. QFT5 expanded-composite E=0.157730453169 versus corrected CoM E=0.164059155294; '
        'QFT15 is worse (1.861377837613 versus 1.812963783085). Both examples and every negative result remain in the CSV.',
        '', 'The replay independently rechecks %d actual frozen-matrix optima and %d applied orientations, and all %d schedules replay with identical budgets. '
        '%d actual placement batches have new-new move conflicts outside the frozen linear proxy. This confirms the proxy limitation; it is not an exact routing optimum.'
        % (exact_matrix_optima, oriented, len(replay), mutual_conflict_batches),
        '', 'The largest actual pilot matrix has %d real rows and %d candidate columns. Maximum observed worker-family peak working set was %.2f MiB; '
        'this combines imports and all variants in a case worker, not per-variant memory. Raw artifacts occupy %.2f MiB. Python index bytes and candidate/cost/matching clocks '
        'are in the raw records. Diagnostics are retained, so sparse-index space is not a whole-wrapper memory bound.'
        % (value['maximum_real_rows'], value['maximum_candidate_columns'], max(resource_peaks) / 1024**2, raw_bytes / 1024**2),
        '', 'Timing includes two separate narrow planner/wrapper clocks and stage breakdown. It is not comparable directly with Phase01 full compilation and does not establish speedup. '
        'Every placement prediction file compares local row time with actual full-placement transport, which includes committed/eviction/cycle moves; these scopes differ explicitly.',
        '', 'No best k, weight setting or variant is selected from the evaluation set. These are analytical two-plane, no-cooling CZ-skeleton results, '
        'not calibrated-device fidelity or a completed final benchmark claim. The frozen Phase01/03/04 benchmark studies are unchanged.', '']
    (destination / 'pilot_results.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k: v for k, v in value.items() if k not in ('records', 'worker_attempt_sha256', 'historical_exact_controls')}))


if __name__ == '__main__':
    main()
