"""Common-model full replay/prefix accounting; no private fidelity formula."""
from copy import deepcopy
import math
from implementation.lookahead.evaluation import evaluate_compilation
from implementation.movement_error.schedule import make_schedule
from implementation.movement_error.evaluator import evaluate
from implementation.trace.model import fingerprint


def total_E(result):
    budget = result.get('budget')
    if not budget:
        raise ValueError('No defined common-model budget')
    if budget.get('total_E_infinite'):
        return math.inf
    value = budget.get('total_E')
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError('Undefined/nonphysical common-model objective')
    return float(value)


def recipe_hash(case, lookahead, assignment, profile, seed):
    return fingerprint({'case': case, 'lookahead': lookahead, 'assignment': assignment,
                        'profile': profile, 'seed': seed})


def bundle(compilation, case, profile, recipe):
    value = evaluate_compilation(compilation, case['circuit'], case['geometry'], profile)
    result = value['result']
    if value['accepted_schedule']:
        carriers = result['final_physical_carriers']
        heating = result['final_n_by_physical_atom']
        for q, n in compilation['statistics']['predicted_prefix_n_by_qubit'].items():
            if abs(n - heating[carriers[q]]) > 1e-12:
                raise ValueError('Downstream heating disagrees with common full replay')
        if abs(compilation['physical_clock_us'] - result['makespan_us']) > 1e-8:
            raise ValueError('Downstream time disagrees with common full replay')
        for q, exposure_value in compilation['weighted_exposure_us'].items():
            if abs(exposure_value - result['per_qubit_exposure'][q]['weighted_exposure_us']) > 1e-7:
                raise ValueError('Downstream exposure disagrees with common full replay')
    return {'compilation': compilation, 'evaluation': value, 'recipe_sha256': recipe}


def placement_span(schedule, boundary):
    gates = set(boundary['active_gate_ids'])
    events = schedule['events']
    gate = next((event for event in events if event.get('gate_id') in gates), None)
    if gate is None:
        raise ValueError('Repair active gates absent from schedule')
    placement = gate['placement_batch']
    indices = [i for i, event in enumerate(events) if event.get('placement_batch') == placement]
    return min(indices), max(indices) + 1, placement


def prefix_invariant(incumbent, candidate, boundary):
    before = incumbent['evaluation']['schedule']
    after = candidate['evaluation']['schedule']
    i, _, old = placement_span(before, boundary)
    j, _, new = placement_span(after, boundary)
    left, right = before['events'][:i], after['events'][:j]
    return {'unchanged': left == right and old == new,
            'incumbent_prefix_sha256': fingerprint(left), 'candidate_prefix_sha256': fingerprint(right),
            'incumbent_event_count': len(left), 'candidate_event_count': len(right), 'placement_batch': old}


def prefix_objective(bundle_value, boundary, *, include_transition):
    """Exact common error for a complete physical prefix with its CZ subset."""
    trace = deepcopy(bundle_value['evaluation']['schedule']['source_trace'])
    _, _, placement = placement_span(bundle_value['evaluation']['schedule'], boundary)
    indices = [i for i, event in enumerate(trace['events']) if event.get('placement_batch') == placement]
    if not indices:
        raise ValueError('Source placement boundary absent')
    stop = max(indices) + 1 if include_transition else min(indices)
    trace['events'] = trace['events'][:stop]
    seen = {event['gate_id'] for event in trace['events'] if event['kind'] == 'gate'}
    metadata = trace['metadata']
    metadata['circuit']['gates'] = [gate for gate in metadata['circuit']['gates'] if gate['gate_id'] in seen]
    metadata['circuit_sha256'] = fingerprint(metadata['circuit'])
    metadata.pop('events_sha256', None)
    metadata['source_counts'] = {
        'nonempty_movement_blocks': sum(event['kind'] == 'move' for event in trace['events']),
        'gate_stages': len({event.get('gate_batch') for event in trace['events'] if event['kind'] == 'gate'})}
    if 'legacy_scored_CZ' in metadata:
        metadata['legacy_scored_CZ'] = len(seen)
    result = evaluate(make_schedule(trace, bundle_value['evaluation']['schedule']['profile'], 'retime'), include_audit=False)
    if result['status'] != 'ok' or not result['valid_for_comparison']:
        raise ValueError('Independent prefix evaluation is not valid')
    return total_E(result)


def local_objective(bundle_value, boundary):
    before = prefix_objective(bundle_value, boundary, include_transition=False)
    after = prefix_objective(bundle_value, boundary, include_transition=True)
    return after - before if math.isfinite(before) and math.isfinite(after) else None
