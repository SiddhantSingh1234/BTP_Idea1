"""Short bounded Phase05 case/seed worker. No baseline controller is invoked."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from implementation.assignment.integration import compile_schedule
from implementation.assignment.costs import load_options
from implementation.lookahead.potential import load_options as load_lookahead
from implementation.lookahead.evaluation import evaluate_compilation
from implementation.trace.model import save_trace, fingerprint
from implementation.movement_error.profiles import load_profile


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True, help='Frozen case request JSON')
    parser.add_argument('--grid', type=int, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh worker output inside btp_work')
    out.mkdir(parents=True)
    request = json.loads(args.input.read_text(encoding='utf-8'))
    case = request['case']
    if args.grid != case['geometry']['rows'] or args.seed != request['seed']:
        raise ValueError('Case/worker controls differ')
    profile = load_profile(ROOT / 'configs/hardware/extended_no_cooling.json')
    rows = []
    for variant in request['variants']:
        directory = out / variant
        directory.mkdir()
        try:
            name = 'phase04_reference' if variant == 'original_legacy' else variant
            options = load_options(ROOT / 'configs/variants' / ('assignment.' + name + '.json'))
            parking = 'legacy_exact' if variant == 'original_legacy' else 'next_events_h4'
            lookahead = load_lookahead(ROOT / 'configs/variants' / ('lookahead.' + parking + '.json'))
            samples, first = [], None
            for repeat in range(request['timing_repeats']):
                started = time.perf_counter()
                compiled = compile_schedule(case['schedule'], case['circuit']['num_qubits'],
                    case['layout'], case['geometry'], case['baseline_options'], lookahead, options,
                    profile, circuit=case['circuit'], routing_seed=args.seed)
                elapsed = time.perf_counter() - started
                digest = hashlib.sha256(compiled['instructions'].encode()).hexdigest()
                if first is None:
                    first, first_hash = compiled, digest
                elif first_hash != digest:
                    raise AssertionError('Fixed-seed timing repeat changed instructions')
                samples.append({'repeat': repeat, 'planner_seconds': compiled['planner_seconds'],
                                'wrapper_seconds': elapsed, 'instructions_sha256': digest,
                                'not_independent_quality_sample': True})
            started = time.perf_counter()
            evaluated = evaluate_compilation(first, case['circuit'], case['geometry'], profile)
            scoring_seconds = time.perf_counter() - started
            result = evaluated['result']
            prefix_matches = True
            if 'final_n_by_physical_atom' in result:
                for q, n in first['statistics']['predicted_prefix_n_by_qubit'].items():
                    prefix_matches &= abs(n - result['final_n_by_physical_atom'][result['final_physical_carriers'][q]]) < 1e-12
            else:
                prefix_matches = False
            (directory / 'instructions.txt').write_text(first['instructions'], encoding='utf-8', newline='\n')
            write(directory / 'compilation.json', first)
            save_trace(directory / 'trace', evaluated['trace'])
            for name, data in [('schedule', evaluated['schedule']), ('evaluation', result),
                               ('validation', evaluated['source_validation']), ('metrics', evaluated['metrics'])]:
                write(directory / (name + '.json'), data)
            budget = result.get('budget') or {}
            predictions = []
            for number, assignment in enumerate(first['assignment_records']):
                routes = [r for r in first['route_prefix_records'] if r['assignment_record_index'] == number]
                predictions.append({'assignment_index': number, 'maximum_matrix_cost': assignment.get('maximum_cost'),
                    'sum_matrix_cost': assignment.get('sum_cost'),
                    'sum_row_predicted_transport_us': sum(s['predicted']['duration_us'] for s in assignment.get('selected', [])),
                    'actual_full_placement_transport_us': sum(r['duration_us'] + 2 * profile['noise']['transfer_duration_us'] for r in routes),
                    'actual_full_placement_move_batches': len(routes),
                    'scope': 'prediction covers row endpoints/optional displaced estimate; actual includes all committed and eviction/cycle moves'})
            write(directory / 'predictor_vs_actual.json', predictions)
            row = {'case': case['case_id'], 'variant': variant, 'seed': args.seed,
                'status': result['status'], 'accepted_schedule': evaluated['accepted_schedule'],
                'E': budget.get('total_E'), 'E_infinite': budget.get('total_E_infinite'),
                'F_proxy': budget.get('fidelity_proxy'), 'makespan_us': result.get('makespan_us'),
                'moved_atom_events': evaluated['metrics']['moved_atom_events'],
                'routing_batches': evaluated['metrics']['routing_batches'],
                'transfer_atom_events': result.get('counts', {}).get('transfer_atom_events'),
                'sum_atom_distance_um': evaluated['metrics']['sum_atom_distance_um'],
                'planner_median_seconds': statistics.median(s['planner_seconds'] for s in samples),
                'wrapper_median_seconds': statistics.median(s['wrapper_seconds'] for s in samples),
                'timing_sample_count': len(samples), 'scoring_seconds': scoring_seconds,
                'assignment_solves': first['statistics']['assignment_solves'],
                'candidate_seconds': first['statistics']['assignment_candidate_seconds'],
                'cost_seconds': first['statistics']['assignment_cost_seconds'],
                'matching_seconds': first['statistics']['assignment_matching_seconds'],
                'event_index_bytes': first['statistics']['event_index_reachable_bytes'],
                'prefix_heating_matches_full_evaluator': prefix_matches,
                'instructions_sha256': first_hash, 'input_circuit_sha256': fingerprint(case['circuit']),
                'layout_sha256': fingerprint(case['layout']), 'profile_sha256': result['profile_sha256'],
                'raw_directory': str(directory.relative_to(ROOT)), 'model_geometry_only': True,
                'assignment_options': options, 'parking_options': lookahead, 'timing_samples': samples}
            row.update(budget.get('terms', {}))
            if not prefix_matches:
                row.update(status='error', accepted_schedule=False, error='prefix/full-evaluator heating disagreement')
        except Exception as exc:
            row = {'case': case['case_id'], 'variant': variant, 'seed': args.seed, 'status': 'error',
                   'accepted_schedule': False, 'E': None, 'raw_directory': str(directory.relative_to(ROOT)),
                   'error': {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}}
            write(directory / 'failure.json', row)
        rows.append(row)
        write(out / 'rows.json', rows)
    result = {'status': 'ok' if all(row['accepted_schedule'] for row in rows) else 'invalid',
              'rows': rows, 'hash_seed': os.environ.get('PYTHONHASHSEED'), 'threads': 1}
    write(out / 'result.json', result)
    print(json.dumps({'case': case['case_id'], 'seed': args.seed, 'rows': len(rows), 'status': result['status']}))
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
