"""Fixed Phase06 development/evaluation pilot; serial isolated bounded workers."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
from collections import Counter

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from implementation.repair.fixtures import development_cases, evaluation_cases
from implementation.repair.artifacts import write
from implementation.trace.model import fingerprint
import run_paper_focus as bounded


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['development', 'evaluation'], default='evaluation')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh pilot output under btp_work')
    out.mkdir(parents=True)
    started = time.perf_counter()
    cases = development_cases() if args.split == 'development' else evaluation_cases()
    protocol = read(ROOT / 'configs/studies/phase06_pilot_v1.json')
    if {case['case_id']: fingerprint(case['circuit']) for case in cases} != protocol[args.split + '_cases']:
        raise ValueError('Frozen repair case set changed')
    for name, digest in protocol['configuration_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen pipeline/repair configuration changed')
    seeds = [42] if args.split == 'development' else [42, 43]
    assignments = ['sum_distance', 'composite_bottleneck_expanded']
    budgets = ['disabled', 'zero', 'small', 'standard']
    code = list((ROOT / 'implementation/repair').glob('*.py'))
    code += list((ROOT / 'implementation/assignment').glob('*.py'))
    code += list((ROOT / 'implementation/lookahead').glob('*.py'))
    code += list((ROOT / 'implementation/movement_error').glob('*.py'))
    code += [ROOT / 'tools/phase06_worker.py', Path(__file__).resolve(),
             ROOT / 'configs/studies/phase06_pilot_v1.json']
    manifest = {'schema': 'repair_pilot.phase06.v1', 'split': args.split, 'cases': cases,
        'assignments': assignments, 'repair_budgets': budgets, 'routing_seeds': seeds,
        'input_hashes': {case['case_id']: fingerprint(case['circuit']) for case in cases},
        'artifact_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in code},
        'tuning': 'Deterministic operation caps frozen before evaluation; no held-out outcome-based settings',
        'timing': 'Every full trial, rejection, local-prefix score and repair overhead is charged; one quality run per seed, no speedup claim',
        'worker_caps': {'wall_seconds': 240, 'observed_process_family_bytes': 4294967296},
        'baseline_controllers_invoked': False, 'command': sys.argv}
    write(out / 'manifest.json', manifest)
    rows, audits = [], []
    for case in cases:
        for seed in seeds:
            label = case['case_id'] + '__s' + str(seed)
            request = out / 'requests' / (label + '.json')
            write(request, {'case': case, 'seed': seed, 'assignments': assignments, 'repair_budgets': budgets})
            job = {'target_id': label, 'seed': seed, 'grid': case['geometry']['rows'],
                'expected_normalized_sha256': hashlib.sha256(request.read_bytes()).hexdigest()}
            record = bounded.bounded_job(job, 240, output_root=out / 'raw',
                worker_path=ROOT / 'tools/phase06_worker.py',
                router_path=ROOT / 'implementation/repair/search.py', input_path=request)
            if record.get('result') and record['status'] in ('ok', 'invalid'):
                fresh = record['result']['rows']
            else:
                fresh = [{'case': case['case_id'], 'seed': seed, 'preceding_assignment': assignment,
                          'repair': budget, 'status': record['status'], 'accepted_schedule': False,
                          'attempt_record': record['record_path']}
                         for assignment in assignments for budget in budgets]
            rows.extend(fresh)
            for row in fresh:
                if row.get('raw_result'):
                    raw = read(ROOT / row['raw_result'])
                    for entry in raw['audit']:
                        audits.append({**entry, 'case': row['case'], 'seed': seed,
                            'preceding_assignment': row['preceding_assignment'], 'repair_budget': row['repair'],
                            'parent_run': row['raw_result']})
            write(out / 'progress.json', {'completed_final_schedules': len(rows),
                'planned_final_schedules': len(cases) * len(seeds) * len(assignments) * len(budgets)})
            print(json.dumps({'case': case['case_id'], 'seed': seed, 'completed': len(rows)}), flush=True)
    fields = sorted({key for row in rows for key in row if key != 'error'})
    with (out / 'pilot_results.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    audit_fields = ['case', 'seed', 'preceding_assignment', 'repair_budget', 'parent_run',
        'candidate_id', 'boundary_key', 'boundary_order', 'kind', 'selection_reason',
        'predicted_local_E', 'parent_full_E', 'actual_full_E', 'local_E_delta',
        'valid', 'prefix_unchanged', 'accepted', 'decision', 'evaluation_seconds',
        'compile_seconds', 'validation_scoring_seconds', 'prefix_scoring_seconds',
        'changed_targets', 'changed_events', 'before_event_count', 'after_event_count', 'locally_better_globally_worse', 'incumbent_unchanged_after_trial',
        'caller_rng_restored_after_trial']
    with (out / 'repair_audit.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_fields, extrasaction='ignore')
        writer.writeheader()
        for entry in audits:
            view = dict(entry)
            view['predicted_local_E'] = entry['predicted_score']['optimistic_one_batch_E']
            view['changed_targets'] = json.dumps(entry['proposal']['targets'], sort_keys=True)
            writer.writerow(view)
    stats = {}
    for assignment in assignments:
        for budget in budgets:
            selected = [row for row in rows if row['preceding_assignment'] == assignment and row['repair'] == budget]
            stats[assignment + '/' + budget] = {
                'better': sum(row.get('delta_E', 0) < -1e-12 for row in selected),
                'tie': sum(row.get('delta_E') is not None and abs(row['delta_E']) <= 1e-12 for row in selected),
                'worse': sum(row.get('delta_E', 0) > 1e-12 for row in selected),
                'unavailable': sum(row['status'] != 'ok' for row in selected)}
    result = {'schema': 'repair_pilot_result.phase06.v1', 'split': args.split,
        'final_schedules': len(rows), 'all_accepted': all(row['accepted_schedule'] for row in rows),
        'status_counts': dict(Counter(row['status'] for row in rows)),
        'candidate_evaluations': len(audits), 'accepted_repairs': sum(entry['accepted'] for entry in audits),
        'local_global_traps_rejected': sum(entry.get('locally_better_globally_worse', False) and not entry['accepted'] for entry in audits),
        'outcomes': stats, 'rows': rows, 'artifact_sha256': manifest['artifact_sha256'],
        'wall_seconds': time.perf_counter() - started, 'baseline_controllers_modified_or_restarted': False,
        'best_default_selected_from_evaluation': False, 'native_physical_validity_claimed': False}
    write(out / 'pilot_results.json', result)
    print(json.dumps({key: value for key, value in result.items() if key not in ('rows', 'artifact_sha256')}))
    return 0 if result['all_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
