"""Best feasible incumbent, deterministic budgets, strict FULL-error acceptance."""
from copy import deepcopy
import math
import random
import time
from implementation.repair.config import validate_options
from implementation.repair.replay import replay, ReplayLimit, PrefixViolation
from implementation.repair.evaluation import bundle, total_E, recipe_hash, prefix_invariant, local_objective
from implementation.repair.neighborhood import rank_boundaries, generate, route_metrics
from implementation.lookahead.events import FutureEventIndex
from implementation.trace.model import fingerprint


def prepare(case, lookahead, assignment, profile, *, seed=42):
    recipe = recipe_hash(case, lookahead, assignment, profile, seed)
    compiled = replay(case, lookahead, assignment, profile, seed=seed)
    return bundle(compiled, case, profile, recipe)


def strict_improvement(candidate_E, incumbent_E, tolerance):
    return math.isfinite(candidate_E) and candidate_E < incumbent_E - tolerance


def repair(case, lookahead, assignment, profile, options, *, seed=42, baseline=None,
           checkpoint=None, stop_check=None):
    caller_rng = random.getstate()
    started = time.perf_counter()
    options = validate_options(options)
    audits = []
    commits = []
    evaluations = 0
    candidate_compile_seconds = 0.
    candidate_scoring_seconds = 0.
    prefix_scoring_seconds = 0.
    generation_seconds = 0.
    rounds = 0
    baseline_seconds = 0.
    baseline_input_hash = fingerprint(baseline) if baseline is not None else None
    try:
        before = time.perf_counter()
        try:
            incumbent = deepcopy(baseline) if baseline is not None else prepare(
                case, lookahead, assignment, profile, seed=seed)
            baseline_seconds = time.perf_counter() - before
            if incumbent['recipe_sha256'] != recipe_hash(case, lookahead, assignment, profile, seed):
                raise ValueError('Baseline/options/profile/circuit identity differs')
            if not incumbent['evaluation']['accepted_schedule']:
                raise ValueError('Baseline is invalid/unsupported; repair cannot clear it')
            incumbent_E = total_E(incumbent['evaluation']['result'])
        except Exception as exc:
            return {'status': 'baseline_failure', 'incumbent': None, 'audit': [],
                    'error': {'type': type(exc).__name__, 'message': str(exc)},
                    'repair_seconds': time.perf_counter() - started}
        original_E = incumbent_E
        original_schedule_hash = fingerprint(incumbent['evaluation']['schedule'])
        overrides = deepcopy(incumbent['compilation'].get('repair_overrides', {}))
        minimum_order = max((b['order'] for b in incumbent['compilation']['repair_boundaries']
                              if b['key'] in overrides), default=0)
        visited = {fingerprint(overrides)}
        index = FutureEventIndex(case['schedule'], case['circuit']['num_qubits'], case['circuit'])

        def expired():
            return options['max_repair_seconds'] is not None and time.perf_counter() - started >= options['max_repair_seconds']

        def result(status):
            random.setstate(caller_rng)
            return {'status': status, 'incumbent': incumbent, 'audit': audits, 'accepted_history': commits,
                'original_E': original_E, 'final_E': incumbent_E,
                'original_schedule_sha256': original_schedule_hash,
                'final_schedule_sha256': fingerprint(incumbent['evaluation']['schedule']),
                'baseline_input_unchanged': baseline is None or fingerprint(baseline) == baseline_input_hash,
                'caller_rng_restored': random.getstate() == caller_rng,
                'options': options, 'rounds': rounds, 'candidate_evaluations': evaluations,
                'baseline_prepare_or_copy_seconds': baseline_seconds,
                'candidate_compile_seconds': candidate_compile_seconds,
                'candidate_validation_scoring_seconds': candidate_scoring_seconds,
                'prefix_local_scoring_seconds': prefix_scoring_seconds,
                'candidate_generation_seconds': generation_seconds,
                'repair_seconds': time.perf_counter() - started}

        if not options['enabled'] or not options['max_evaluations'] or not options['max_rounds']:
            return result('disabled' if not options['enabled'] else 'zero_budget')
        if expired():
            return result('wall_budget_exhausted')
        for round_number in range(options['max_rounds']):
            rounds += 1
            if stop_check and stop_check():
                return result('stopped_with_incumbent')
            before = time.perf_counter()
            selected = rank_boundaries(incumbent['compilation'], options, minimum_order)
            neighborhood = []
            for boundary, metrics in selected:
                neighborhood.extend((boundary, proposal) for proposal in
                    generate(boundary, case, index, lookahead, profile, options))
            generation_seconds += time.perf_counter() - before
            if not neighborhood:
                return result('no_candidates')
            parent_hash = fingerprint(incumbent)
            parent_E = incumbent_E
            local_cache = {}
            winner = None
            exhausted = False
            for boundary, proposal in neighborhood:
                if evaluations >= options['max_evaluations'] or expired() or (stop_check and stop_check()):
                    exhausted = True
                    break
                plan = deepcopy(overrides)
                plan[proposal['boundary_key']] = {
                    'prefix_sha256': proposal['prefix_sha256'], 'targets': proposal['targets']}
                plan_hash = fingerprint(plan)
                if plan_hash in visited:
                    continue
                visited.add(plan_hash)
                evaluations += 1
                entry = {'candidate_id': 'r' + str(round_number + 1) + '_c' + str(evaluations),
                    'round': round_number + 1, 'boundary_key': proposal['boundary_key'],
                    'boundary_order': proposal['boundary_order'], 'kind': proposal['kind'],
                    'selection_reason': proposal['reason'], 'predicted_score': proposal['predicted'],
                    'parent_schedule_sha256': fingerprint(incumbent['evaluation']['schedule']),
                    'parent_full_E': parent_E, 'accepted': False, 'proposal': deepcopy(proposal),
                    'override_plan': deepcopy(plan), 'actual_full_E': None,
                    'local_E_delta': None, 'valid': False, 'prefix_unchanged': False}
                tick = time.perf_counter()
                try:
                    before = time.perf_counter()
                    compiled = replay(case, lookahead, assignment, profile, seed=seed,
                        overrides=plan, route_limit=options['max_replay_route_calls'])
                    entry['compile_seconds'] = time.perf_counter() - before
                    candidate_compile_seconds += entry['compile_seconds']
                    before = time.perf_counter()
                    candidate = bundle(compiled, case, profile, incumbent['recipe_sha256'])
                    entry['validation_scoring_seconds'] = time.perf_counter() - before
                    candidate_scoring_seconds += entry['validation_scoring_seconds']
                    entry['valid'] = candidate['evaluation']['accepted_schedule']
                    prefix = prefix_invariant(incumbent, candidate, boundary)
                    entry['prefix_evidence'] = prefix
                    entry['prefix_unchanged'] = prefix['unchanged']
                    entry['actual_full_E'] = total_E(candidate['evaluation']['result'])
                    entry['candidate_schedule_sha256'] = fingerprint(candidate['evaluation']['schedule'])
                    entry['candidate_instructions_sha256'] = fingerprint(candidate['compilation']['instructions'])
                    entry['final_rng_sha256'] = compiled['random_state_after_sha256']
                    entry['final_budget'] = deepcopy(candidate['evaluation']['result'].get('budget'))
                    entry['violations'] = candidate['evaluation']['result']['validation']['violations']
                    candidate_boundary = next(b for b in compiled['repair_boundaries'] if b['key'] == boundary['key'])
                    entry['before_route_metrics'] = route_metrics(boundary)
                    entry['after_route_metrics'] = route_metrics(candidate_boundary)
                    before = time.perf_counter()
                    if boundary['key'] not in local_cache:
                        local_cache[boundary['key']] = local_objective(incumbent, boundary)
                    local = local_objective(candidate, candidate_boundary)
                    old_local = local_cache[boundary['key']]
                    entry['local_E_delta'] = local - old_local if local is not None and old_local is not None else None
                    entry['prefix_scoring_seconds'] = time.perf_counter() - before
                    prefix_scoring_seconds += entry['prefix_scoring_seconds']
                    eligible = entry['valid'] and entry['prefix_unchanged'] and strict_improvement(
                        entry['actual_full_E'], parent_E, options['improvement_tolerance_E'])
                    entry['improves_full_error'] = eligible
                    entry['locally_better_globally_worse'] = (
                        entry['local_E_delta'] is not None and entry['local_E_delta'] < -options['improvement_tolerance_E']
                        and entry['actual_full_E'] > parent_E + options['improvement_tolerance_E'])
                    if expired():
                        entry['decision'] = 'wall_budget_reject'
                        exhausted = True
                    elif not entry['valid']:
                        entry['decision'] = 'invalid_reject'
                    elif not entry['prefix_unchanged']:
                        entry['decision'] = 'prefix_reject'
                    elif eligible:
                        entry['decision'] = 'feasible_round_candidate'
                        if winner is None or entry['actual_full_E'] < winner[0]['actual_full_E']:
                            winner = (entry, candidate, plan)
                    else:
                        entry['decision'] = 'full_error_reject'
                except Exception as exc:
                    # Elapsed work on failures still counts toward reported
                    # cost and the deterministic evaluation budget.
                    elapsed = time.perf_counter() - tick
                    if 'compile_seconds' not in entry:
                        entry['compile_seconds'] = elapsed
                        candidate_compile_seconds += elapsed
                    entry.update(decision='candidate_exception_reject',
                        error={'type': type(exc).__name__, 'message': str(exc)})
                entry['evaluation_seconds'] = time.perf_counter() - tick
                entry['incumbent_unchanged_after_trial'] = fingerprint(incumbent) == parent_hash
                entry['caller_rng_restored_after_trial'] = random.getstate() == caller_rng
                if not entry['incumbent_unchanged_after_trial'] or not entry['caller_rng_restored_after_trial']:
                    raise AssertionError('Private trial leaked incumbent or RNG state')
                audits.append(entry)
                if exhausted:
                    break
            if winner is not None:
                entry, candidate, plan = winner
                incumbent = candidate
                incumbent_E = entry['actual_full_E']
                overrides = plan
                minimum_order = entry['boundary_order']
                entry.update(accepted=True, decision='accepted_full_replay')
                commits.append({'candidate_id': entry['candidate_id'], 'before_E': parent_E,
                    'after_E': incumbent_E, 'boundary_key': entry['boundary_key'],
                    'prefix_evidence': deepcopy(entry['prefix_evidence']),
                    'schedule_sha256': fingerprint(incumbent['evaluation']['schedule']),
                    'bundle': deepcopy(incumbent)})
                for trial in audits:
                    if trial['round'] == round_number + 1 and trial['decision'] == 'feasible_round_candidate':
                        trial['decision'] = 'not_best_feasible_round_candidate'
                if checkpoint:
                    checkpoint(deepcopy(incumbent), deepcopy(entry))
            if exhausted or evaluations >= options['max_evaluations']:
                return result('budget_exhausted_with_incumbent')
            if winner is None:
                return result('no_improvement')
        return result('round_budget_complete')
    finally:
        random.setstate(caller_rng)
