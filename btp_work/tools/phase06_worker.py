"""Bounded Phase06 pilot worker: matched Phase05 controls and repair budgets."""
from copy import deepcopy
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from implementation.assignment.costs import load_options as assignment_options
from implementation.lookahead.potential import load_options as parking_options
from implementation.movement_error.profiles import load_profile
from implementation.repair.config import load_options
from implementation.repair.search import prepare, repair
from implementation.repair.artifacts import write, write_bundle, save_result
from implementation.repair.evaluation import total_E
from implementation.trace.model import fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True, help='Frozen case request JSON')
    parser.add_argument('--grid', type=int, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh worker output under btp_work')
    out.mkdir(parents=True)
    request = json.loads(args.input.read_text(encoding='utf-8'))
    case = request['case']
    if case['geometry']['rows'] != args.grid or request['seed'] != args.seed:
        raise ValueError('Worker/request controls differ')
    lookahead = parking_options(ROOT / 'configs/variants/lookahead.next_events_h4.json')
    profile = load_profile(ROOT / 'configs/hardware/extended_no_cooling.json')
    rows = []
    for preceding in request['assignments']:
        assignment = assignment_options(ROOT / 'configs/variants' / ('assignment.' + preceding + '.json'))
        before = time.perf_counter()
        try:
            baseline = prepare(case, lookahead, assignment, profile, seed=args.seed)
            baseline_seconds = time.perf_counter() - before
            base_directory = out / preceding / 'baseline'
            write_bundle(base_directory, baseline)
            for name in request['repair_budgets']:
                directory = out / preceding / name
                directory.mkdir(parents=True)
                try:
                    options = load_options(ROOT / 'configs/variants' / ('repair.' + name + '.json'))
                    write(directory / 'last_incumbent.json', {'bundle_directory': str(base_directory),
                        'full_E': total_E(baseline['evaluation']['result']), 'source': 'validated_baseline'})
                    def checkpoint(value, entry):
                        path = directory / 'accepted' / entry['candidate_id']
                        write_bundle(path, value)
                        write(directory / 'last_incumbent.json', {'bundle_directory': str(path),
                            'full_E': entry['actual_full_E'], 'source': entry['candidate_id']})
                    result = repair(case, lookahead, assignment, profile, options, seed=args.seed,
                                    baseline=baseline, checkpoint=checkpoint)
                    summary = save_result(directory, result, base_directory)
                    if result['incumbent'] is None:
                        raise ValueError('Repair baseline failure')
                    incumbent = result['incumbent']
                    score = incumbent['evaluation']['result']
                    valid = incumbent['evaluation']['accepted_schedule']
                    row = {'case': case['case_id'], 'seed': args.seed, 'preceding_assignment': preceding,
                        'repair': name, 'status': 'ok' if valid else 'invalid',
                        'repair_status': result['status'], 'accepted_schedule': valid,
                        'baseline_E': result['original_E'], 'E': result['final_E'],
                        'delta_E': result['final_E'] - result['original_E'],
                        'F_proxy': score['budget']['fidelity_proxy'], 'makespan_us': score['makespan_us'],
                        'baseline_makespan_us': baseline['evaluation']['result']['makespan_us'],
                        'candidate_evaluations': result['candidate_evaluations'],
                        'accepted_repairs': len(result['accepted_history']),
                        'baseline_compile_validate_seconds': baseline_seconds,
                        'repair_seconds': result['repair_seconds'],
                        'total_compile_validate_repair_seconds': baseline_seconds + result['repair_seconds'],
                        'candidate_compile_seconds': result['candidate_compile_seconds'],
                        'candidate_validation_scoring_seconds': result['candidate_validation_scoring_seconds'],
                        'prefix_local_scoring_seconds': result['prefix_local_scoring_seconds'],
                        'candidate_generation_seconds': result['candidate_generation_seconds'],
                        'baseline_input_unchanged': result['baseline_input_unchanged'],
                        'caller_rng_restored': result['caller_rng_restored'],
                        'final_schedule_sha256': result['final_schedule_sha256'],
                        'original_schedule_sha256': result['original_schedule_sha256'],
                        'raw_result': str((directory / 'result.json').relative_to(ROOT)),
                        'final_bundle_directory': str(Path(summary['final_bundle_directory']).relative_to(ROOT)),
                        'input_circuit_sha256': fingerprint(case['circuit']), 'profile_sha256': fingerprint(profile),
                        'native_physical_validity_claimed': False}
                    if row['delta_E'] > 1e-12 or not row['baseline_input_unchanged'] or not row['caller_rng_restored']:
                        raise AssertionError('Repair violated its retained-incumbent contract')
                    row.update(score['budget']['terms'])
                except Exception as exc:
                    row = {'case': case['case_id'], 'seed': args.seed, 'preceding_assignment': preceding,
                        'repair': name, 'status': 'error', 'accepted_schedule': False,
                        'error': {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}}
                    write(directory / 'failure.json', row)
                rows.append(row)
                write(out / 'rows.json', rows)
        except Exception as exc:
            for name in request['repair_budgets']:
                rows.append({'case': case['case_id'], 'seed': args.seed, 'preceding_assignment': preceding,
                    'repair': name, 'status': 'baseline_failure', 'accepted_schedule': False,
                    'error': {'type': type(exc).__name__, 'message': str(exc)}})
            write(out / preceding / 'baseline_failure.json', rows[-1])
    result = {'status': 'ok' if all(row['status'] == 'ok' for row in rows) else 'invalid',
        'rows': rows, 'hash_seed': os.environ.get('PYTHONHASHSEED'), 'threads': 1,
        'input_request_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest()}
    write(out / 'result.json', result)
    print(json.dumps({'case': case['case_id'], 'seed': args.seed, 'rows': len(rows), 'status': result['status']}))
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
