"""Matched full-matrix Phase05 integration; scientific assignment code is unchanged."""
from copy import deepcopy
import hashlib
from pathlib import Path
import random
import time
import traceback
from implementation.assignment.integration import AssignmentContext, assignment_core
from implementation.assignment.costs import load_options as load_assignment
from implementation.assignment.matching import AssignmentInfeasible
from implementation.lookahead.potential import load_options as load_lookahead
from implementation.movement_error.profiles import load_profile
from implementation.adapters.upstream import rft_groups, build_trace
from implementation.lookahead.evaluation import pilot_geometry_profile
from implementation.trace.model import fingerprint


def bounded_context_type(parking_context):
    class MatchedAssignmentContext(AssignmentContext, parking_context):
        """Same production hooks and heating; bound retained diagnostics only."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.assignment_count = 0
            self.route_count = 0

        def solve_assignment(self, *args, **kwargs):
            choice = super().solve_assignment(*args, **kwargs)
            self.assignment_count += 1
            self.pending_assignment_id = self.assignment_count - 1
            del self.assignment_records[8:]
            return choice

        def observe_route(self, instructions):
            before = len(self.route_records)
            super().observe_route(instructions)
            self.route_count += len(self.route_records) - before
            del self.route_records[8:]

        def statistics(self):
            result = super().statistics()
            result.update(assignment_solves=self.assignment_count,
                physical_prefix_move_batches=self.route_count,
                diagnostic_snapshot_limit=8,
                diagnostic_policy='first eight assignment/route/parking snapshots; complete operation counts and heating state')
            return result
    return MatchedAssignmentContext


def assignment_benchmark(api, runner, raw, request, lookahead, config, profile, circuit, state):
    geometry = request['geometry']
    native = request['native']
    if native['options'].get('enable_rft_hungarian_bias', False):
        raise ValueError('Existing assignment future bias must remain disabled')
    if native['options'].get('assignment_mode', 'hungarian') != 'hungarian' or profile['cooling']['enabled']:
        raise ValueError('Matched Phase05 requires Hungarian baseline and no cooling')
    context_type = bounded_context_type(api.BenchmarkContext)
    context = context_type([], 0, None, lookahead, geometry, config, profile)
    core = assignment_core(context)
    picker = context.original_pick
    original_generate = runner.generate_hardware_instructions
    def generate(schedule, canonical, busiest, n, rows, columns, slots, r_blk, r_int, options=None):
        # All event-index, prefix-physics and assignment construction/calls are
        # inside the exact original run_benchmark timed region.
        context.__init__(schedule, n, circuit, lookahead, geometry, config, profile)
        context.original_pick = picker
        return core.generate_hardware_instructions(schedule, canonical, busiest, n,
            rows, columns, slots, r_blk, r_int, options=options)
    runner.generate_hardware_instructions = generate
    layout = [[tuple(p) for p in slot] for slot in native['layout']]
    options = runner.CompilerOptions(**native['options'])
    try:
        random.setstate(state)
        runner.run_benchmark(str(raw), geometry['rows'], geometry['columns'],
                             geometry['r_int'], geometry['r_blk'], layout, options)
        random.setstate(state)
        stats = runner.run_benchmark(str(raw), geometry['rows'], geometry['columns'],
                                    geometry['r_int'], geometry['r_blk'], layout, options)
        if stats is None or len(context.completed) != context.index.gate_count:
            raise ValueError('Phase05 did not complete the full gate set')
        return stats, context
    finally:
        runner.generate_hardware_instructions = original_generate


def execute_variants(runner, raw, request, circuit, state, baseline, rows, out, api):
    profile = load_profile(api.CODE / 'configs/hardware/extended_no_cooling.json')
    parking = load_lookahead(api.CODE / 'configs/variants/lookahead.next_events_h4.json')
    for name in request['variants']:
        directory = out / name
        directory.mkdir()
        row = {key: request['job'][key] for key in ['target_id','algorithm','family','case','grid']}
        row.update(variant=name, accepted_schedule=False, compilation_reused=False,
                   scoring_scope='normalized_CZ_skeleton', native_physical_validity_claimed=False)
        api.write(out / 'stage.json', {'stage': 'compilation', 'current_variant': name})
        try:
            config = load_assignment(api.CODE / 'configs/variants' / ('assignment.' + name + '.json'))
            if name == 'phase04_reference':
                stats, context = api.modified_benchmark(runner, raw, request, parking, circuit, state)
            else:
                stats, context = assignment_benchmark(api, runner, raw, request,
                    parking, config, profile, circuit, state)
            text = api.instruction_text(stats)
            (directory / 'instructions.txt').write_text(text, encoding='utf-8', newline='\n')
            diagnostics = {'statistics': context.statistics(),
                'assignment_options': config, 'parking_options': parking,
                'decisions_sample': context.decisions, 'batches_sample': context.batches,
                'assignment_sample': getattr(context, 'assignment_records', []),
                'route_prefix_sample': getattr(context, 'route_records', []),
                'instructions_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'random_state_after_sha256': hashlib.sha256(repr(random.getstate()).encode()).hexdigest()}
            api.write(directory / 'assignment_diagnostics.json', diagnostics)
            groups, parse_diagnostics = rft_groups(text)
            trace = build_trace(groups, circuit, pilot_geometry_profile(request['geometry']),
                origin={'kind': 'matched_phase05', 'original_register_complete': True,
                        'lookahead_options': parking, 'assignment_options': config},
                timing='two_transfer_stages', diagnostics=parse_diagnostics)
            api.write(out / 'stage.json', {'stage': 'validation_and_scoring', 'current_variant': name})
            start = time.perf_counter()
            row = api.score(trace, request, name, directory, stats['Elapsed Time (s)'],
                compilation_reused=False,
                timing_scope='original run_benchmark region INCLUDING event index, prefix heating, assignment and parking',
                layout_sha256=fingerprint(request['native']['layout']),
                assignment_metric=config['metric'], assignment_objective=config['objective'],
                candidate_policy=config['candidate_policy'], h=parking['h'], gamma=parking['gamma'])
            row['scoring_seconds'] = time.perf_counter() - start
            row['instructions_sha256'] = diagnostics['instructions_sha256']
            row['event_index_bytes'] = diagnostics['statistics']['event_index_reachable_bytes']
            if name != 'phase04_reference':
                evaluation = api.read(directory / 'evaluation.json')
                matches = bool(evaluation.get('final_n_by_physical_atom') is not None)
                if matches:
                    for q, n in context.n_by_qubit.items():
                        atom = evaluation['final_physical_carriers'][str(q)]
                        matches &= abs(n - evaluation['final_n_by_physical_atom'][atom]) < 1e-12
                row.update(prefix_heating_matches_full_evaluator=matches,
                    assignment_solves=diagnostics['statistics']['assignment_solves'],
                    assignment_candidate_seconds=context.candidate_seconds,
                    assignment_cost_seconds=context.cost_seconds,
                    assignment_matching_seconds=context.matching_seconds)
                if not matches:
                    row.update(status='error', accepted_schedule=False,
                               error='Prefix heating differs from full independent evaluator')
        except Exception as exc:
            row.update(status='unsupported' if isinstance(exc, AssignmentInfeasible) else 'error',
                accepted_schedule=False, error_type=type(exc).__name__, error=str(exc))
            api.write(directory / 'failure.json', {'type': type(exc).__name__,
                'message': str(exc), 'traceback': traceback.format_exc()})
        rows.append(row)
        api.write(out / 'rows.json', rows)
    controls = {row['variant']: row for row in rows}
    for row in rows:
        for control, label in [('original_phase3','original'), ('phase04_reference','phase04'),
                               ('sum_distance','corrected_sum_distance'),
                               ('sum_distance_expanded','expanded_sum_distance')]:
            reference = controls.get(control, {})
            row['delta_extended_E_vs_' + label] = (row['extended_E'] - reference['extended_E']
                if row.get('accepted_schedule') and reference.get('accepted_schedule')
                and row.get('extended_E') is not None and reference.get('extended_E') is not None else None)
    api.write(out / 'rows.json', rows)
    api.write(out / 'stage.json', {'stage': 'complete', 'current_variant': None})
    return rows
