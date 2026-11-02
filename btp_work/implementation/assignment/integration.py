"""Phase05 isolated checked hooks: oriented assignment, unchanged parking/router."""
from dataclasses import asdict
import hashlib
import itertools
import math
import random
import sys
import time
import types
from implementation.lookahead.integration import LookaheadContext, load_core, CORE, CORE_SHA256
from implementation.assignment.costs import (validate_options, make_problem, candidates, assign, Problem)
from implementation.assignment.matching import AssignmentInfeasible, covering_matching
from implementation.adapters.upstream import rft_groups
from implementation.movement_error.physics import movement_time, heating_increment

_serial = itertools.count()


class AssignmentContext(LookaheadContext):
    def __init__(self, schedule, n, circuit, lookahead, geometry, config, profile):
        super().__init__(schedule, n, circuit, lookahead, geometry['spacing_um'])
        self.assignment = validate_options(config)
        self.geometry = dict(geometry)
        self.profile = profile
        self.n_by_qubit = {q: profile['heating']['initial_n_by_qubit'].get(str(q),
                          profile['heating']['initial_n']) for q in range(n)}
        self.assignment_records = []
        self.route_records = []
        self.candidate_seconds = 0.
        self.cost_seconds = 0.
        self.matching_seconds = 0.
        self.pending_assignment_id = None

    def observe_route(self, instructions):
        groups, diagnostics = rft_groups('\n'.join(instructions))
        if diagnostics:
            raise ValueError('Router format not understood by Phase05 prefix observer: ' + str(diagnostics))
        for group in groups:
            if group['kind'] != 'move':
                continue
            distances = {item['qubit']: math.dist(item['from'], item['to']) * self.spacing_um
                         for item in group['items']}
            duration = movement_time(max(distances.values(), default=0.), self.profile['movement'])
            for q, distance in distances.items():
                self.n_by_qubit[q] += heating_increment(distance, duration, self.profile['heating'])
            self.route_records.append({'distances_um': distances, 'duration_us': duration,
                'assignment_record_index': self.pending_assignment_id})

    def complete_batch(self, pairs):
        super().complete_batch(pairs)
        self.pending_assignment_id = None

    def solve_assignment(self, movers, static_slots, current, committed, committed_slots,
                         center, active_pairs, finished_indices):
        started = time.perf_counter()
        slots = candidates(static_slots, center, len(movers), self.assignment)
        self.candidate_seconds += time.perf_counter() - started
        active = frozenset(self.index.gate_id(self.layer, active_pairs[i]) for i in finished_indices)
        problem = make_problem(movers, slots, current, committed, committed_slots, self.geometry,
            index=self.index, layer=self.layer, completed=frozenset(self.completed), active=active,
            n_by_qubit=dict(self.n_by_qubit), profile=self.profile,
            lookahead=self.config, config=self.assignment)
        self.cost_seconds += problem.build_seconds
        count = len(movers)
        feasible_prefix_calls = 1
        if covering_matching(problem.costs) is None:
            low, high = 0, count
            while low < high:
                mid = (low + high + 1) // 2
                feasible_prefix_calls += 1
                if covering_matching(problem.costs[:mid]) is None:
                    high = mid - 1
                else:
                    low = mid
            count = low
        if not count:
            if not committed:
                raise AssignmentInfeasible('No legal fallback pair can execute; explicit finite failure')
            self.assignment_records.append({'logical_layer': self.layer, 'rows_requested': len(movers),
                'rows_assigned': 0, 'fallback': 'commit only already accepted dynamic pairs'})
            return {'mapping': {}, 'row_count': 0}
        if count < len(movers):
            # Rebuild the chosen prefix with exactly the active gates that will
            # execute; deferred current-layer gates remain pending.
            chosen_pairs = {tuple(pair) for pair in movers[:count]}
            kept = [i for i in finished_indices if tuple(active_pairs[i]) not in set(map(tuple, movers))
                    or tuple(active_pairs[i]) in chosen_pairs]
            active = frozenset(self.index.gate_id(self.layer, active_pairs[i]) for i in kept)
            problem = make_problem(movers[:count], slots, current, committed, committed_slots, self.geometry,
                index=self.index, layer=self.layer, completed=frozenset(self.completed), active=active,
                n_by_qubit=dict(self.n_by_qubit), profile=self.profile,
                lookahead=self.config, config=self.assignment)
            self.cost_seconds += problem.build_seconds
        mapping, selected, result = assign(problem, self.assignment['objective'])
        self.matching_seconds += result.seconds
        self.assignment_records.append({'logical_layer': self.layer, 'rows_requested': len(movers),
            'rows_assigned': count, 'candidate_count': len(slots), 'candidate_policy': self.assignment['candidate_policy'],
            'candidate_slots': slots, 'pairs': problem.pairs, 'committed_moves': problem.committed_moves,
            'completed_gate_ids': sorted(self.completed), 'active_gate_ids': sorted(active),
            'cost_matrix': [[x if math.isfinite(x) else None for x in row] for row in problem.costs],
            'legal_mask': [[math.isfinite(x) for x in row] for row in problem.costs],
            'selected': selected, 'maximum_cost': result.maximum, 'sum_cost': result.total,
            'threshold': result.threshold, 'feasibility_calls': result.feasibility_calls,
            'prefix_feasibility_calls': feasible_prefix_calls, 'build_seconds': problem.build_seconds,
            'matching_seconds': result.seconds, 'snapshot_n_by_qubit': dict(self.n_by_qubit),
            'fallback': 'serialize deferred suffix' if count < len(movers) else None})
        self.pending_assignment_id = len(self.assignment_records) - 1
        return {'mapping': mapping, 'row_count': count}

    def statistics(self):
        value = super().statistics()
        value.update(assignment_solves=len(self.assignment_records),
            assignment_candidate_seconds=self.candidate_seconds,
            assignment_cost_seconds=self.cost_seconds, assignment_matching_seconds=self.matching_seconds,
            physical_prefix_move_batches=len(self.route_records),
            predicted_prefix_n_by_qubit=dict(self.n_by_qubit))
        return value


def assignment_core(context):
    if context.assignment['mode'] == 'phase04_passthrough':
        module = load_core(context)
    else:
        raw = CORE.read_bytes()
        if hashlib.sha256(raw).hexdigest() != CORE_SHA256:
            raise ValueError('Pinned source changed')
        source = raw.decode('utf-8')
        hooks = []
        def replace(old, new, label):
            nonlocal source
            if source.count(old) != 1:
                raise ValueError('Phase05 hook anchor changed: ' + label)
            source = source.replace(old, new)
            hooks.append(label)
        replace('        # Get right-filled info for this timestamp',
                '        phase05_context.begin_layer(timestamp_name)\n        # Get right-filled info for this timestamp', 'layer')
        replace('            final_target_positions.update(active_qubit_targets)',
                '            final_target_positions.update(active_qubit_targets)\n            phase05_context.begin_batch(active_pairs_to_map, finished_batch_indices, current_qubit_positions, active_qubit_targets)', 'batch_snapshot')
        replace('            # Remove executed pairs from pending',
                '            phase05_context.complete_batch(executed_pairs)\n            # Remove executed pairs from pending', 'completion')
        replace('right_filled_table = build_right_filled_table(schedule, num_qubits)',
                "right_filled_table = build_right_filled_table(schedule, num_qubits) if phase05_context.policy == 'legacy_exact' else None", 'parking_control')
        begin = source.index('                # Select best candidate slots')
        end = source.index('\n            # --- FINALIZE STEP ---', begin)
        source = source[:begin] + """                phase05_choice = phase05_context.solve_assignment(
                    movers, compatible_static_slots, current_qubit_positions,
                    active_qubit_targets, accepted_dynamic_slots, center_of_mass,
                    active_pairs_to_map, finished_batch_indices)
                pairs_to_assign_now_indices = pairs_to_assign_now_indices[:phase05_choice['row_count']]
                finished_batch_indices = list(accepted_pair_local_indices) + list(pairs_to_assign_now_indices)
                active_qubit_targets.update(phase05_choice['mapping'])
""" + source[end:]
        hooks.append('oriented_assignment_and_bounded_serialization')
        name = '_btp_phase05_core_' + str(next(_serial))
        module = types.ModuleType(name)
        module.__file__ = str(CORE)
        sys.modules[name] = module
        module.phase05_context = context
        exec(compile(source, str(CORE) + '.phase05_hooks', 'exec'), module.__dict__)
        context.original_pick = module._pick_idle_position
        module._pick_idle_position = context.pick
        module.phase04_hook_log = hooks
        module.phase04_loaded_sha256 = hashlib.sha256(source.encode()).hexdigest()
    original_router = module.generate_safe_shuttle_instructions
    def observed_router(*args, **kwargs):
        instructions = original_router(*args, **kwargs)
        context.observe_route(instructions)
        return instructions
    module.generate_safe_shuttle_instructions = observed_router
    return module


def compile_schedule(schedule, n, layout, geometry, baseline_options, lookahead, assignment,
                     profile, *, circuit, routing_seed=42):
    if baseline_options.get('enable_rft_hungarian_bias', False):
        raise ValueError('Existing private future bias must stay disabled')
    if baseline_options.get('assignment_mode', 'hungarian') != 'hungarian':
        raise ValueError('Phase05 controls use the Hungarian baseline')
    if profile['cooling']['enabled']:
        raise ValueError('Phase05 prefix observer requires basic no-cooling resources')
    schedule = [(name, [tuple(pair) for pair in pairs]) for name, pairs in schedule]
    if not layout or n > geometry['rows'] * geometry['columns']:
        raise AssignmentInfeasible('No interaction slots or insufficient register capacity')
    context = AssignmentContext(schedule, n, circuit, lookahead, geometry, assignment, profile)
    module = assignment_core(context)
    options = module.CompilerOptions(**baseline_options)
    slots = [[tuple(site) for site in slot] for slot in layout]
    busiest = module.find_busiest_pairs(schedule)
    canonical = module.create_initial_mapping(busiest, slots)
    random.seed(routing_seed)
    before = hashlib.sha256(repr(random.getstate()).encode()).hexdigest()
    start = time.perf_counter()
    instructions = module.generate_hardware_instructions(schedule, canonical, busiest, n,
        geometry['rows'], geometry['columns'], slots, geometry['r_blk'], geometry['r_int'], options=options)
    seconds = time.perf_counter() - start
    if len(context.completed) != context.index.gate_count:
        raise ValueError('Compiler did not finish all gates')
    return {'instructions': '\n'.join(instructions) + '\n', 'planner_seconds': seconds,
        'decisions': context.decisions, 'batches': context.batches,
        'assignment_records': context.assignment_records, 'route_prefix_records': context.route_records,
        'statistics': context.statistics(), 'core_sha256': CORE_SHA256,
        'hooked_source_sha256': module.phase04_loaded_sha256, 'hooks': module.phase04_hook_log,
        'routing_seed': routing_seed, 'random_state_before_sha256': before,
        'random_state_after_sha256': hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),
        'baseline_options': asdict(options), 'lookahead_options': dict(lookahead),
        'assignment_options': dict(assignment)}
