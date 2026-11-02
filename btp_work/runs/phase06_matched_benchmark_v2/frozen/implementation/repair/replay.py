"""Private Phase05 replay with captured physical boundaries and checked overrides."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import inspect
import math
import random
import sys
import time
from implementation.assignment.integration import AssignmentContext, assignment_core
from implementation.assignment.costs import compatible_slots
from implementation.lookahead.integration import CORE_SHA256
from implementation.trace.model import fingerprint


class ReplayLimit(ValueError):
    pass


class PrefixViolation(ValueError):
    pass


def plain(value):
    # Stable JSON-compatible keys and RNG tuples, including after disk reload.
    import json
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def positions(value):
    return {int(q): tuple(site) for q, site in value.items()}


def boundary_key(layer, active):
    return str(layer) + ':' + ','.join(sorted(active))


def check_targets(targets, current, pairs, geometry):
    targets = positions(targets)
    if set(targets) != set(current):
        raise ValueError('A repair must preserve the entire loaded register')
    if len(set(targets.values())) != len(targets):
        raise ValueError('Duplicate repaired occupancy')
    for site in targets.values():
        if len(site) != 2 or any(type(x) is not int for x in site):
            raise ValueError('Non-grid repair destination')
        if not (0 <= site[0] < geometry['rows'] and 0 <= site[1] < geometry['columns']):
            raise ValueError('Out-of-grid repair destination')
    slots = []
    for a, b in pairs:
        slot = (targets[a], targets[b])
        if math.dist(*slot) > geometry['r_int'] + 1e-9:
            raise ValueError('Repair breaks an active gate')
        if not all(compatible_slots(slot, other, geometry['r_blk']) for other in slots):
            raise ValueError('Repair breaks simultaneous-gate restrictions')
        slots.append(slot)
    return targets


class ReplayContext(AssignmentContext):
    def __init__(self, *args, overrides=None, route_limit=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.overrides = deepcopy(overrides or {})
        self.route_limit = route_limit
        self.boundaries = []
        self.applied_keys = []
        self.current_pairs = []
        self.clock_us = 0.
        self.exposure = dict.fromkeys(self.n_by_qubit, 0.)

    def begin_batch(self, pairs, indices, current, targets):
        super().begin_batch(pairs, indices, current, targets)
        self.current_pairs = [tuple(pairs[i]) for i in indices]

    def observe_route(self, instructions):
        first = len(self.route_records)
        super().observe_route(instructions)
        rates = self.profile['exposure']['rates']
        transfer = 2 * self.profile['noise']['transfer_duration_us']
        for record in self.route_records[first:]:
            moving = {q for q, d in record['distances_um'].items() if d > 0}
            duration = record['duration_us']
            span = duration + (transfer if moving else 0.)
            self.clock_us += span
            for q in self.exposure:
                if q in moving:
                    self.exposure[q] += duration * rates['move'] + transfer * rates['transfer']
                else:
                    self.exposure[q] += span * rates['stationary']

    def complete_batch(self, pairs):
        active_qubits = {q for pair in pairs for q in pair}
        super().complete_batch(pairs)
        if pairs:
            duration = self.profile['noise']['cz_duration_us']
            self.clock_us += duration
            rates = self.profile['exposure']['rates']
            for q in self.exposure:
                self.exposure[q] += duration * rates['gate' if q in active_qubits else 'stationary']

    def route(self, current, targets, rows, columns, router, private_rng):
        if self.route_limit is not None and len(self.boundaries) >= self.route_limit:
            raise ReplayLimit('Candidate exceeded its deterministic route-call budget')
        key = boundary_key(self.layer, self.active)
        state = plain({
            'positions': {str(q): list(p) for q, p in current.items()},
            'physical_carriers': {str(q): 'a' + str(q) for q in current},
            'traps': {str(q): 'SLM' for q in current},
            'heating_n': {str(q): n for q, n in self.n_by_qubit.items()},
            'clock_us': self.clock_us,
            'weighted_exposure_us': {str(q): value for q, value in self.exposure.items()},
            'cooling_resources': [], 'completed_gate_ids': sorted(self.completed),
            'active_gate_ids': sorted(self.active),
            'pending_gate_ids': sorted(set(self.index.gate_layer) - self.completed),
            'routing_rng_state': random.getstate(),
            'planner_private_rng_state': private_rng.getstate()})
        state_hash = fingerprint(state)
        proposed = {q: tuple(site) for q, site in targets.items()}
        override = self.overrides.get(key)
        if override is not None:
            if state_hash != override['prefix_sha256']:
                raise PrefixViolation('Candidate prefix differs at ' + key)
            replacement = check_targets(override['targets'], current, self.current_pairs, self.geometry)
            targets.clear()
            targets.update(replacement)
            self.active_targets = {q: targets[q] for q in self.active_targets}
            self.snapshot = {**current, **self.active_targets}
            self.batches[-1]['committed_active_targets'] = {str(q): list(p) for q, p in self.active_targets.items()}
            if self.pending_assignment_id is not None:
                self.assignment_records[self.pending_assignment_id]['phase06_override'] = {
                    'boundary_key': key, 'physical_targets': {str(q): list(p) for q, p in self.active_targets.items()},
                    'original_matrix_selection_retained_as_proposal_only': True}
            self.applied_keys.append(key)
        start = len(self.route_records)
        instructions = router(current, targets, rows, columns)
        actual = deepcopy(self.route_records[start:])
        identifier = self.pending_assignment_id
        candidate_slots = []
        if identifier is not None:
            candidate_slots = self.assignment_records[identifier].get('candidate_slots', [])
        self.boundaries.append({
            'key': key, 'order': len(self.boundaries), 'logical_layer': self.layer,
            'active_gate_ids': sorted(self.active), 'active_pairs': deepcopy(self.current_pairs),
            'prefix_state': state, 'prefix_sha256': state_hash,
            'current_positions': {str(q): list(p) for q, p in current.items()},
            'targets': {str(q): list(p) for q, p in targets.items()},
            'unrepaired_proposed_targets': {str(q): list(p) for q, p in proposed.items()},
            'assignment_record_index': identifier, 'candidate_slots': deepcopy(candidate_slots),
            'route_batches': actual, 'repair_override_applied': override is not None})
        return instructions


def replay(case, lookahead, assignment, profile, *, seed=42, overrides=None, route_limit=None):
    """Recompute the entire circuit; enforce every recorded prefix before changes.

    Caller RNG is restored on success and on exceptions. Cost includes prefix
    recomputation; this is not claimed to be an optimized snapshot resume.
    """
    if case['baseline_options'].get('enable_rft_hungarian_bias', False):
        raise ValueError('Existing private future bias must stay disabled')
    if profile['cooling']['enabled']:
        raise ValueError('The accepted Phase05 pipeline has no cooling-resource planner')
    if lookahead['lookahead_policy'] != 'next_events':
        raise ValueError('Phase06 core holds generalized parking fixed')
    if case['baseline_options'].get('assignment_mode', 'hungarian') != 'hungarian':
        raise ValueError('Repair requires the accepted oriented assignment pipeline')
    if not case['layout'] or case['circuit']['num_qubits'] > case['geometry']['rows'] * case['geometry']['columns']:
        raise ValueError('Invalid baseline capacity')
    if assignment['mode'] != 'oriented':
        raise ValueError('Repair uses an orientation-corrected Phase05 control')
    caller_rng = random.getstate()
    module = None
    started = time.perf_counter()
    try:
        schedule = [(name, [tuple(pair) for pair in pairs]) for name, pairs in case['schedule']]
        context = ReplayContext(schedule, case['circuit']['num_qubits'], case['circuit'],
            lookahead, case['geometry'], assignment, profile, overrides=overrides, route_limit=route_limit)
        module = assignment_core(context)
        observed_router = module.generate_safe_shuttle_instructions
        def guarded_router(current, targets, rows, columns):
            frame = inspect.currentframe().f_back
            try:
                private = frame.f_locals.get('rng')
                if not isinstance(private, random.Random):
                    raise PrefixViolation('Private planner RNG cannot be observed')
                return context.route(current, targets, rows, columns, observed_router, private)
            finally:
                del frame
        module.generate_safe_shuttle_instructions = guarded_router
        options = module.CompilerOptions(**case['baseline_options'])
        slots = [[tuple(site) for site in slot] for slot in case['layout']]
        busiest = module.find_busiest_pairs(schedule)
        canonical = module.create_initial_mapping(busiest, slots)
        random.seed(seed)
        before = hashlib.sha256(repr(random.getstate()).encode()).hexdigest()
        clock = time.perf_counter()
        instructions = module.generate_hardware_instructions(schedule, canonical, busiest,
            case['circuit']['num_qubits'], case['geometry']['rows'], case['geometry']['columns'],
            slots, case['geometry']['r_blk'], case['geometry']['r_int'], options=options)
        planner_seconds = time.perf_counter() - clock
        if len(context.completed) != context.index.gate_count:
            raise PrefixViolation('Incomplete replayed circuit')
        if set(context.applied_keys) != set(overrides or {}):
            raise PrefixViolation('An override boundary was not reached')
        return {'instructions': '\n'.join(instructions) + '\n', 'planner_seconds': planner_seconds,
            'wrapper_seconds': time.perf_counter() - started,
            'decisions': context.decisions, 'batches': context.batches,
            'assignment_records': context.assignment_records, 'route_prefix_records': context.route_records,
            'statistics': context.statistics(), 'core_sha256': CORE_SHA256,
            'hooked_source_sha256': module.phase04_loaded_sha256,
            'hooks': module.phase04_hook_log + ['phase06_private_boundary_replay'],
            'routing_seed': seed, 'random_state_before_sha256': before,
            'random_state_after_sha256': hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),
            'baseline_options': asdict(options), 'lookahead_options': dict(lookahead),
            'assignment_options': dict(assignment), 'repair_boundaries': context.boundaries,
            'repair_overrides': plain(overrides or {}), 'physical_clock_us': context.clock_us,
            'weighted_exposure_us': {str(q): v for q, v in context.exposure.items()}}
    finally:
        random.setstate(caller_rng)
        if module is not None:
            sys.modules.pop(module.__name__, None)
