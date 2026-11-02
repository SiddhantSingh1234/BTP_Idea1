"""Fixed development/evaluation Phase05 pilot with isolated serial bounded workers."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from collections import Counter

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from implementation.assignment.fixtures import development_cases, evaluation_cases
from implementation.trace.model import fingerprint
import run_paper_focus as bounded


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--split', choices=['development', 'evaluation'], default='evaluation')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use a fresh pilot directory under btp_work')
    out.mkdir(parents=True)
    started = time.perf_counter()
    cases = development_cases() if args.split == 'development' else evaluation_cases()
    protocol = read(ROOT / 'configs/studies/phase05_pilot_v1.json')
    expected_cases = protocol[args.split + '_cases']
    if {c['case_id']: fingerprint(c['circuit']) for c in cases} != expected_cases:
        raise ValueError('Frozen pilot case set changed')
    for name, digest in protocol['configuration_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen assignment config changed: ' + name)
    variants = ['original_legacy', 'phase04_reference', 'sum_distance', 'bottleneck_distance',
        'bottleneck_time', 'composite_sum', 'composite_bottleneck', 'sum_distance_expanded',
        'composite_bottleneck_expanded', 'sum_distance_all', 'composite_bottleneck_all',
        'composite_no_conflict', 'composite_no_future', 'composite_with_displacements']
    seeds = [42] if args.split == 'development' else [42, 43]
    code = list((ROOT / 'implementation/assignment').glob('*.py')) + list((ROOT / 'configs/variants').glob('assignment.*.json'))
    code += list((ROOT / 'implementation/lookahead').glob('*.py')) + list((ROOT / 'implementation/movement_error').glob('*.py'))
    code += [ROOT / 'configs/hardware/extended_no_cooling.json', ROOT / 'tools/phase05_worker.py', ROOT / 'configs/studies/phase05_pilot_v1.json', Path(__file__).resolve()]
    manifest = {'schema': 'assignment_pilot.phase05.v1', 'split': args.split, 'cases': cases, 'variants': variants,
        'seeds': seeds, 'timing_repeats': '2 at seed42, 1 at seed43; timing repetitions are not quality seeds',
        'parking': 'fixed h4 gamma .9 for corrected/new variants; original_legacy is separately labelled',
        'weights': 'frozen untrained 1/1/1/1/.25, normalizers15um/1conflict/4transfers/.01E; expansion2',
        'tuning': 'No benchmark-driven weight tuning or best-k selection. Development seeds100-103; evaluation seeds200-204 and named frozen inputs.',
        'comparison': 'Use corrected sum_distance for objective gains; original_legacy/phase04_reference expose corrections separately',
        'input_hashes': {case['case_id']: fingerprint(case['circuit']) for case in cases},
        'artifact_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in code},
        'baseline_controllers_invoked': False, 'command': sys.argv}
    write(out / 'manifest.json', manifest)
    rows = []
    for case in cases:
        for seed in seeds:
            name = case['case_id'] + '__s' + str(seed)
            request_path = out / 'requests' / (name + '.json')
            write(request_path, {'case': case, 'seed': seed, 'variants': variants,
                                'timing_repeats': 2 if seed == 42 else 1})
            # Existing bounded runner accepts an immutable input file; here that
            # input is a normalized case request JSON, not a QASM. Its hash is
            # separate from each row's normalized input-circuit hash.
            job = {'target_id': name, 'grid': case['geometry']['rows'], 'seed': seed,
                   'expected_normalized_sha256': hashlib.sha256(request_path.read_bytes()).hexdigest()}
            attempt = bounded.bounded_job(job, 180, output_root=out / 'raw',
                worker_path=ROOT / 'tools/phase05_worker.py',
                router_path=ROOT / 'implementation/assignment/integration.py', input_path=request_path)
            if attempt['status'] in ('ok', 'invalid') and attempt.get('result'):
                rows.extend(attempt['result']['rows'])
            else:
                for variant in variants:
                    rows.append({'case': case['case_id'], 'variant': variant, 'seed': seed,
                                 'status': attempt['status'], 'accepted_schedule': False, 'E': None,
                                 'attempt_record': attempt['record_path']})
            write(out / 'progress.json', {'completed_rows': len(rows), 'planned_rows': len(cases) * len(seeds) * len(variants),
                                         'last_case': case['case_id'], 'last_seed': seed})
            print(json.dumps({'case': case['case_id'], 'seed': seed, 'completed_rows': len(rows)}), flush=True)
    lookup = {(r['case'], r['seed'], r['variant']): r for r in rows}
    for row in rows:
        for variant, label in [('sum_distance', 'corrected_sum_distance'), ('phase04_reference', 'phase04'),
                               ('original_legacy', 'legacy')]:
            other = lookup[(row['case'], row['seed'], variant)]
            row['delta_E_vs_' + label] = (row['E'] - other['E'] if row['accepted_schedule'] and other['accepted_schedule']
                    and row['E'] is not None and other['E'] is not None else None)
    simple_rows = [{key: value for key, value in row.items()
                    if key not in ('assignment_options', 'parking_options', 'timing_samples', 'error')} for row in rows]
    fields = sorted({key for row in simple_rows for key in row})
    with (out / 'pilot_results.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(simple_rows)
    outcomes = {}
    for variant in variants:
        comparisons = [r.get('delta_E_vs_corrected_sum_distance') for r in rows if r['variant'] == variant]
        outcomes[variant] = {'better': sum(x is not None and x < -1e-12 for x in comparisons),
                             'tie': sum(x is not None and abs(x) <= 1e-12 for x in comparisons),
                             'worse': sum(x is not None and x > 1e-12 for x in comparisons),
                             'unavailable': sum(x is None for x in comparisons)}
    result = {'schema': 'assignment_pilot_result.phase05.v1', 'split': args.split,
        'attempts': len(rows), 'status_counts': dict(Counter(r['status'] for r in rows)),
        'all_accepted': all(r['accepted_schedule'] for r in rows),
        'timing_samples': sum(r.get('timing_sample_count', 0) for r in rows),
        'wall_seconds': time.perf_counter() - started, 'outcomes_vs_corrected_sum_distance': outcomes,
        'rows': rows, 'artifact_sha256': manifest['artifact_sha256'], 'best_variant_selected': False,
        'native_physical_validity_claimed': False, 'phase01_results_modified': False}
    write(out / 'pilot_results.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'artifact_sha256')}))
    return 0 if result['all_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
