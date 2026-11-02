"""Full paper-matrix adapter over the unchanged accepted Phase06 repair API."""
from pathlib import Path
import hashlib
import gc
import random
import sys
import time
import traceback
import types
from implementation.assignment.costs import load_options as assignment_options
from implementation.lookahead.integration import load_core
from implementation.lookahead.potential import load_options as parking_options
from implementation.lookahead.evaluation import pilot_geometry_profile
from implementation.movement_error.profiles import load_profile
from implementation.repair.config import load_options as repair_options
from implementation.repair.search import prepare, repair
from implementation.repair.artifacts import write_bundle, save_result, write
from implementation.repair.evaluation import total_E
from implementation.trace.model import fingerprint

POLICIES = ['sum_distance', 'composite_bottleneck_expanded']
BUDGETS = ['disabled', 'zero', 'small', 'standard']


def execute(request, source, circuit, out, api):
    from phase06_memory import memory_scope
    with memory_scope():
        return execute_with_memory(request, source, circuit, out, api)


def execute_with_memory(request, source, circuit, out, api):
    # NetworkX's router consumes the GLOBAL RNG. The pilot API deliberately
    # seeds it directly, while full Phase05 starts after original RFT warmup.
    # Reconstruct that exact state and give every full replay the same state.
    # The accepted replay function's bytecode and all scientific APIs stay intact.
    sys.path.insert(0, str(api.CODE / 'vendor' / api.RFT / 'src'))
    import benchmark_runner as runner
    import implementation.repair.search as search
    geometry = request['geometry']
    raw = Path(request['raw_input'])
    if api.sha(raw) != request['job']['raw_sha256']:
        raise ValueError('Frozen raw input changed')
    random.seed(request['job']['seed'])
    _, layout = runner.sample_max_parallel(geometry['rows'], geometry['columns'],
        geometry['r_int'], geometry['r_blk'], m=20)
    if fingerprint(layout) != fingerprint(request['native']['layout']):
        raise ValueError('Cannot reconstruct frozen Phase05 layout/RNG')
    runner.run_benchmark(str(raw), geometry['rows'], geometry['columns'],
        geometry['r_int'], geometry['r_blk'], layout, runner.CompilerOptions(**request['native']['options']))
    if request['job']['routing_seed'] is not None:
        random.seed(request['job']['routing_seed'])
    state = random.getstate()
    state_hash = hashlib.sha256(repr(state).encode()).hexdigest()
    if any(state_hash != v['measured_start_rng_sha256'] for v in request['job']['phase5_controls'].values()):
        raise ValueError('Reconstructed full-benchmark RNG differs from Phase05')
    write(out / 'routing_rng_state.json', {'state': state, 'sha256_of_repr': state_hash})
    original = search.replay
    class MatchedRandom:
        def __getattr__(self, name):
            return getattr(random, name)
        def seed(self, value):
            if value != request['job']['seed']:
                raise ValueError('Unexpected replay seed')
            random.setstate(state)
    namespace = dict(original.__globals__)
    namespace['random'] = MatchedRandom()
    matched = types.FunctionType(original.__code__, namespace, original.__name__, original.__defaults__, original.__closure__)
    matched.__kwdefaults__ = original.__kwdefaults__
    from phase06_memory import freeze_compilation
    def memory_replay(*args, **kwargs):
        value = freeze_compilation(matched(*args, **kwargs))
        gc.collect()
        return value
    search.replay = memory_replay
    try:
        return execute_matched(request, source, circuit, out, api, state_hash)
    finally:
        search.replay = original


def execute_matched(request, source, circuit, out, api, state_hash):
    core = load_core()
    _, schedule, n = core.analyze_qasm_file(str(source))
    if n != circuit['num_qubits']:
        raise ValueError('Normalized register differs from repair schedule')
    case = {'case_id': request['job']['target_id'], 'schedule': schedule,
        'circuit': circuit, 'layout': request['native']['layout'],
        'geometry': request['geometry'], 'baseline_options': request['native']['options'],
        'input_kind': 'complete frozen Phase01 normalized paper-matrix target',
        'input_sha256': request['job']['expected_normalized_sha256'],
        'full_benchmark_routing_rng_sha256': state_hash}
    write(out / 'case.json', case)
    lookahead = parking_options(api.CODE / 'configs/variants/lookahead.next_events_h4.json')
    profile = load_profile(api.CODE / 'configs/hardware/extended_no_cooling.json')
    seed = request['job']['seed']
    rows = []
    for policy in POLICIES:
        write(out / 'stage.json', {'stage': 'prepare_and_match_phase05', 'current_variant': policy})
        try:
            assignment = assignment_options(api.CODE / 'configs/variants' / ('assignment.' + policy + '.json'))
            # Warm the exact API used by both baseline and trials, outside timing.
            warm = prepare(case, lookahead, assignment, profile, seed=seed)
            del warm
            gc.collect()
            started = time.perf_counter()
            baseline = prepare(case, lookahead, assignment, profile, seed=seed)
            baseline_seconds = time.perf_counter() - started
            reference = request['job']['phase5_controls'][policy]
            text = baseline['compilation']['instructions']
            evidence = {
                'instructions_exact': hashlib.sha256(text.encode()).hexdigest() == reference['instructions_sha256'],
                'common_E_exact': abs(total_E(baseline['evaluation']['result']) - reference['extended_E']) <= 1e-12,
                'profile_exact': fingerprint(profile) == reference['profile_sha256'],
                'geometry_exact': fingerprint(pilot_geometry_profile(case['geometry'])) == reference['geometry_sha256'],
                'normalized_input_exact': api.sha(source) == reference['normalized_sha256'],
                'accepted_schedule': baseline['evaluation']['accepted_schedule']}
            write(out / policy / 'phase05_compatibility.json', evidence)
            if not all(evidence.values()):
                raise ValueError('Repair starting policy differs from completed Phase05: ' + str(evidence))
            baseline_directory = out / policy / 'baseline'
            write_bundle(baseline_directory, baseline)
        except Exception as exc:
            for budget in BUDGETS:
                rows.append({'variant': policy + '__' + budget, 'status': 'error',
                    'accepted_schedule': False, 'error': str(exc)})
            write(out / policy / 'baseline_failure.json', {'error': str(exc), 'traceback': traceback.format_exc()})
            write(out / 'rows.json', rows)
            continue
        for budget in BUDGETS:
            variant = policy + '__' + budget
            directory = out / policy / budget
            write(out / 'stage.json', {'stage': 'repair', 'current_variant': variant})
            row = {key: request['job'][key] for key in ['target_id', 'algorithm', 'family', 'case', 'grid']}
            row.update(variant=variant, preceding_assignment=policy, repair_budget=budget,
                status='error', accepted_schedule=False, native_physical_validity_claimed=False)
            try:
                options = repair_options(api.CODE / 'configs/variants' / ('repair.' + budget + '.json'))
                write(directory / 'last_incumbent.json', {'bundle_directory': str(baseline_directory),
                    'full_E': total_E(baseline['evaluation']['result']), 'source': 'matched_phase05_baseline'})
                def checkpoint(value, entry):
                    path = directory / 'accepted' / entry['candidate_id']
                    write_bundle(path, value)
                    write(directory / 'last_incumbent.json', {'bundle_directory': str(path),
                        'full_E': entry['actual_full_E'], 'source': entry['candidate_id']})
                started = time.perf_counter()
                result = repair(case, lookahead, assignment, profile, options, seed=seed,
                    baseline=baseline, checkpoint=checkpoint)
                repair_wall = time.perf_counter() - started
                summary = save_result(directory, result, baseline_directory)
                incumbent = result['incumbent']
                if incumbent is None:
                    raise ValueError('Repair lost its valid incumbent')
                score = incumbent['evaluation']['result']
                metrics = incumbent['evaluation']['metrics']
                if (result['final_E'] > result['original_E'] + 1e-12
                        or not result['baseline_input_unchanged'] or not result['caller_rng_restored']):
                    raise AssertionError('Retained incumbent / rollback contract failed')
                if budget in ['disabled', 'zero'] and (
                        result['final_schedule_sha256'] != result['original_schedule_sha256']
                        or incumbent['compilation']['instructions'] != baseline['compilation']['instructions']
                        or incumbent['compilation']['random_state_after_sha256'] != baseline['compilation']['random_state_after_sha256']):
                    raise AssertionError('Disabled/zero changed its Phase05 control')
                for accepted in result['accepted_history']:
                    if not accepted['after_E'] < accepted['before_E'] - options['improvement_tolerance_E']:
                        raise AssertionError('Accepted repair lacks strict complete-E improvement')
                row.update(status='ok' if incumbent['evaluation']['accepted_schedule'] else 'invalid',
                    accepted_schedule=incumbent['evaluation']['accepted_schedule'],
                    normalized_sha256=reference['normalized_sha256'], profile_sha256=score['profile_sha256'],
                    geometry_sha256=reference['geometry_sha256'], phase05_instructions_exact=True,
                    extended_E=result['final_E'], extended_fidelity=score['budget']['fidelity_proxy'],
                    extended_makespan_us=score['makespan_us'], baseline_E=result['original_E'],
                    delta_extended_E_vs_start=result['final_E'] - result['original_E'],
                    moved_atom_events=metrics['moved_atom_events'], routing_batches=metrics['routing_batches'],
                    sum_atom_distance_um=metrics['sum_atom_distance_um'],
                    baseline_compile_validate_seconds=baseline_seconds, repair_wall_seconds=repair_wall,
                    end_to_end_compile_validate_repair_seconds=baseline_seconds + repair_wall,
                    compile_seconds=None,
                    timing_scope='Phase06 end-to-end preparation/compilation/validation plus repair, revalidation, rejected trials and checkpoints; separate from original compiler timer',
                    repair_status=result['status'], candidate_evaluations=result['candidate_evaluations'],
                    accepted_repairs=len(result['accepted_history']),
                    baseline_input_unchanged=result['baseline_input_unchanged'], caller_rng_restored=result['caller_rng_restored'],
                    final_schedule_sha256=result['final_schedule_sha256'],
                    original_schedule_sha256=result['original_schedule_sha256'],
                    final_bundle_directory=str(Path(summary['final_bundle_directory']).relative_to(api.WORK)),
                    output=str(directory.relative_to(api.WORK)))
                for field in ['candidate_compile_seconds', 'candidate_validation_scoring_seconds',
                              'prefix_local_scoring_seconds', 'candidate_generation_seconds']:
                    row[field] = result[field]
                row.update(score['budget']['terms'])
                # Do not retain the preceding budget's accepted bundles while
                # constructing the next candidate family.
            except Exception as exc:
                row.update(status='error', accepted_schedule=False, error=str(exc))
                write(directory / 'failure.json', {'error': str(exc), 'traceback': traceback.format_exc()})
            finally:
                accepted = result = summary = incumbent = score = metrics = None
            rows.append(row)
            write(out / 'rows.json', rows)
            gc.collect()
        del baseline
        gc.collect()
    write(out / 'stage.json', {'stage': 'complete', 'current_variant': None})
    return rows
