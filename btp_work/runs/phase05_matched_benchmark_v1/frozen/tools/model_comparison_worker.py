"""Matched Phase03 rescoring / Phase04 compilation worker. Run via bounded controller."""
import argparse
from copy import deepcopy
from collections import OrderedDict
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import time
import traceback

sys.dont_write_bytecode = True
EXECUTION = Path(__file__).resolve().parents[1]
CODE = EXECUTION.parent / 'frozen' if EXECUTION.name == 'execution_optimization_v1' else EXECUTION
WORK = Path(os.environ.get('BTP_WORK_ROOT', CODE)).resolve()
sys.path.insert(0, str(CODE))
from implementation.trace.model import read_cz_qasm, load_trace, save_trace, fingerprint
from implementation.adapters.upstream import rft_groups, build_trace
from implementation.lookahead.evaluation import pilot_geometry_profile
from implementation.lookahead.integration import LookaheadContext, load_core
from implementation.lookahead.potential import FuturePotential, load_options
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.schedule import make_schedule
from implementation.movement_error.evaluator import evaluate
from implementation.metrics.legacy import measure_trace
from implementation.validation.checker import check_trace

RFT = 'NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def instruction_text(stats):
    return '\n'.join(stats['instructions']) + '\n'


class BenchmarkContext(LookaheadContext):
    """Same event/potential APIs; retain at most eight diagnostic snapshots.

    Diagnostic storage is bounded independently of circuit length. No changes
    to candidates, event selection, weights, anchors or routing are introduced.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0
        self.evictions = 0
        self.batch_count = 0
        self.audited_events = 0
        self.missing = 0

    def begin_batch(self, *args):
        super().begin_batch(*args)
        self.batch_count += 1
        if len(self.batches) > 8:
            self.batches.pop()

    def pick(self, **kwargs):
        started = time.perf_counter()
        self.calls += 1
        self.evictions += int(kwargs['is_evicted'])
        if self.policy == 'legacy_exact':
            return self.original_pick(**kwargs)
        query_start = time.perf_counter()
        events = self.index.query(kwargs['qubit'], self.layer, self.config['h'],
                                  completed=self.completed, active=self.active)
        self.query_seconds += time.perf_counter() - query_start
        self.query_count += 1
        for event in events:
            if event['gate_id'] in self.completed or event['gate_id'] in self.active:
                raise AssertionError('Consumed/active event entered parking objective')
        potential = FuturePotential.from_events(events, self.snapshot,
                    gamma=self.config['gamma'], spacing_um=self.spacing_um)
        chosen, candidates = potential.choose(kwargs['available_positions'], kwargs['center_of_mass'])
        self.audited_events += len(events)
        self.missing += len(potential.missing_gate_ids)
        self.potential_seconds += time.perf_counter() - started
        if len(self.decisions) < 8:
            self.decisions.append({
                'qubit': kwargs['qubit'], 'logical_layer': self.layer,
                'is_evicted': kwargs['is_evicted'], 'events': events,
                'chosen_site': list(chosen) if chosen is not None else None,
                'resolved_anchors': [list(item) for item in potential.resolved],
                'candidate_count': len(candidates), 'completed_count': len(self.completed)})
        return chosen

    def statistics(self):
        result = super().statistics()
        result.update(parking_calls=self.calls, eviction_calls=self.evictions,
                      missing_anchor_events=self.missing, placement_batches=self.batch_count,
                      audited_event_count=self.audited_events,
                      diagnostic_snapshot_limit=8, diagnostic_policy='bounded snapshots; production event/potential APIs')
        return result


def source_trace(request, circuit):
    source = request['source']
    if source['kind'] == 'dasatom_trace':
        trace = load_trace(source['worker'] + '/trace')
        if fingerprint(trace['metadata']['circuit']) != fingerprint(circuit):
            raise ValueError('Saved DasAtom trace has different circuit')
        return trace
    groups, diagnostics = rft_groups(Path(source['instructions']).read_text(encoding='utf-8'))
    return build_trace(groups, circuit, pilot_geometry_profile(request['geometry']),
        origin={'kind': 'frozen_phase01_rft', 'upstream_status': 'ok',
                'original_register_complete': True}, timing='two_transfer_stages', diagnostics=diagnostics)


@contextmanager
def reuse_trace_analysis():
    """Cache exact duplicate analysis within one score, never across workers.

    Full canonical trace hashes include events, geometry, timing and metadata.
    Changed traces (including the independent retiming projection) are checked
    separately. Copy returned results so callers cannot mutate cached evidence.
    """
    import implementation.movement_error.schedule as schedule_module
    import implementation.movement_error.checker as checker_module
    import implementation.movement_error.evaluator as evaluator_module
    counters = {'validation_hits': 0, 'validation_misses': 0,
                'metrics_hits': 0, 'metrics_misses': 0}
    def memoize(function, category):
        cache = OrderedDict()
        def call(trace):
            try:
                key = fingerprint(trace)
            except (ValueError, TypeError, OverflowError):
                # Let the original validator classify malformed trace input.
                counters[category + '_misses'] += 1
                return function(trace)
            if key in cache:
                counters[category + '_hits'] += 1
                cache.move_to_end(key)
                return deepcopy(cache[key])
            counters[category + '_misses'] += 1
            result = function(trace)
            cache[key] = deepcopy(result)
            if len(cache) > 8: cache.popitem(last=False)
            return result
        return call
    checked = memoize(check_trace, 'validation')
    measured = memoize(measure_trace, 'metrics')
    bindings = [(globals(), 'check_trace', checked), (globals(), 'measure_trace', measured),
                (vars(schedule_module), 'check_trace', checked),
                (vars(checker_module), 'check_trace', checked),
                (vars(evaluator_module), 'measure_trace', measured)]
    originals = [(namespace, name, namespace[name]) for namespace, name, replacement in bindings]
    try:
        for namespace, name, replacement in bindings: namespace[name] = replacement
        yield counters
    finally:
        for namespace, name, original in reversed(originals): namespace[name] = original


def score(trace, request, variant, out, compile_seconds=None, **extra):
    if request['track'] != 'phase3':
        return score_uncached(trace, request, variant, out, compile_seconds, **extra)
    # Small traces are already cheap; avoid cache hashing/copying overhead there.
    enabled = len(trace['events']) >= 512
    statistics = {'validation_hits': 0, 'validation_misses': 0, 'metrics_hits': 0, 'metrics_misses': 0}
    if enabled:
        with reuse_trace_analysis() as statistics:
            row = score_uncached(trace, request, variant, out, compile_seconds, **extra)
    else:
        row = score_uncached(trace, request, variant, out, compile_seconds, **extra)
    write(out / 'analysis_reuse.json', {
        **statistics, 'enabled': enabled, 'minimum_events': 512,
        'scope': 'this score only', 'key': 'SHA-256 of complete canonical trace',
        'max_entries_per_analysis': 8, 'scientific_functions_unchanged': True})
    return row


def score_uncached(trace, request, variant, out, compile_seconds=None, **extra):
    # A separately derived analytical geometry is applied to BOTH controls and
    # modified schedules. Source files/unknown native coverage remain untouched.
    trace = deepcopy(trace)
    hardware = pilot_geometry_profile(request['geometry'])
    trace['metadata']['hardware'] = hardware
    trace['metadata']['hardware_sha256'] = fingerprint(hardware)
    trace['metadata'].setdefault('assumptions', []).extend(hardware['assumptions'])
    trace['metadata']['physical_evidence_complete'] = False
    validation = check_trace(trace)
    metrics = measure_trace(trace)
    profile = load_profile(CODE / 'configs/hardware/extended_no_cooling.json')
    schedule = make_schedule(trace, profile, 'retime')
    result = evaluate(schedule, include_audit=False)
    save_trace(out / 'trace', trace)
    for name, value in [('validation', validation), ('metrics', metrics),
                        ('schedule', schedule), ('evaluation', result)]:
        write(out / (name + '.json'), value)
    accepted = validation['status'] == 'ok' and result['status'] == 'ok' and result['valid_for_comparison']
    row = {key: request['job'][key] for key in ['target_id', 'algorithm', 'family', 'case', 'grid']}
    row.update(variant=variant, status='ok' if accepted else (
        'invalid' if 'invalid' in [validation['status'], result['status']] else 'unsupported'),
        accepted_schedule=accepted, normalized_sha256=request['job']['expected_normalized_sha256'],
        profile_sha256=result['profile_sha256'], geometry_sha256=fingerprint(hardware),
        compile_seconds=compile_seconds, scoring_seconds=None,
        legacy_E=metrics['legacy']['negative_log_fidelity'],
        legacy_fidelity=metrics['legacy']['fidelity_proxy'],
        legacy_runtime_us=metrics['legacy']['runtime_proxy_us'],
        extended_E=(result.get('budget') or {}).get('total_E'),
        extended_E_infinite=(result.get('budget') or {}).get('total_E_infinite'),
        extended_fidelity=(result.get('budget') or {}).get('fidelity_proxy'),
        extended_makespan_us=result.get('makespan_us'),
        moved_atom_events=metrics['moved_atom_events'], routing_batches=metrics['routing_batches'],
        sum_atom_distance_um=metrics['sum_atom_distance_um'],
        native_physical_validity_claimed=False, scoring_scope='normalized_CZ_skeleton',
        output=str(out.relative_to(WORK)), **extra)
    row.update((result.get('budget') or {}).get('terms', {}))
    return row


def modified_benchmark(runner, raw, request, config, circuit, state):
    context = BenchmarkContext([], 0, None, config, request['geometry']['spacing_um'])
    hooked = load_core(context)
    original_picker = context.original_pick
    original_generate = runner.generate_hardware_instructions

    def generate(schedule, canonical, busiest, n, rows, cols, slots, r_blk, r_int, options=None):
        # This callback is INSIDE the original run_benchmark timer: event-index
        # construction, queries and all parking work are therefore charged.
        context.__init__(schedule, n, circuit, config, request['geometry']['spacing_um'])
        context.original_pick = original_picker
        return hooked.generate_hardware_instructions(schedule, canonical, busiest, n,
                                        rows, cols, slots, r_blk, r_int, options=options)

    runner.generate_hardware_instructions = generate
    geometry = request['geometry']
    layout = [[tuple(p) for p in slot] for slot in request['native']['layout']]
    options = runner.CompilerOptions(**request['native']['options'])
    try:
        # Warm up this variant, then restore the same measured-start global RNG
        # state as the unchanged control. Warmup outcomes are never quality trials.
        random.setstate(state)
        runner.run_benchmark(str(raw), geometry['rows'], geometry['columns'],
                             geometry['r_int'], geometry['r_blk'], layout, options)
        random.setstate(state)
        stats = runner.run_benchmark(str(raw), geometry['rows'], geometry['columns'],
                                    geometry['r_int'], geometry['r_blk'], layout, options)
        if stats is None or len(context.completed) != context.index.gate_count:
            raise ValueError('Incomplete compilation')
        return stats, context
    finally:
        runner.generate_hardware_instructions = original_generate


def execute(request, source, out):
    if request['track'] == 'phase5': write(out / 'stage.json', {'stage': 'saved_reference_scoring', 'current_variant': 'original_phase3'})
    circuit = read_cz_qasm(source)
    if sha(source) != request['job']['expected_normalized_sha256']:
        raise ValueError('Frozen normalized input changed')
    started = time.perf_counter()
    baseline = score(source_trace(request, circuit), request, 'original_phase3',
        out / 'original_phase3', request['original_compile_seconds'],
        compilation_reused=True, timing_scope=request['original_timing_scope'])
    baseline['scoring_seconds'] = time.perf_counter() - started
    rows = [baseline]
    write(out / 'rows.json', rows)
    if request['track'] == 'phase3':
        return rows

    sys.path.insert(0, str(CODE / 'vendor' / RFT / 'src'))
    import benchmark_runner as runner
    native = request['native']
    geometry = request['geometry']
    raw = Path(request['raw_input'])
    if sha(raw) != request['job']['raw_sha256']:
        raise ValueError('Frozen raw input changed')
    if request['track'] == 'phase5': write(out / 'stage.json', {'stage': 'unchanged_control_compilation', 'current_variant': 'legacy_exact'})
    random.seed(request['job']['seed'])
    _, sampled = runner.sample_max_parallel(geometry['rows'], geometry['columns'],
                                            geometry['r_int'], geometry['r_blk'], m=20)
    if fingerprint(sampled) != fingerprint(native['layout']):
        raise ValueError('Cannot reproduce frozen offline layout/RNG sequence')
    layout = [[tuple(p) for p in slot] for slot in native['layout']]
    options = runner.CompilerOptions(**native['options'])
    runner.run_benchmark(str(raw), geometry['rows'], geometry['columns'],
                         geometry['r_int'], geometry['r_blk'], layout, options)
    if request['job']['routing_seed'] is not None:
        random.seed(request['job']['routing_seed'])
    state = random.getstate()
    direct = runner.run_benchmark(str(raw), geometry['rows'], geometry['columns'],
                                  geometry['r_int'], geometry['r_blk'], layout, options)
    text = instruction_text(direct)
    expected = Path(request['source']['instructions']).read_text(encoding='utf-8')
    exact = text == expected
    rng_equal = hashlib.sha256(repr(random.getstate()).encode()).hexdigest() == native['global_random_state_after']
    write(out / 'compatibility.json', {'instructions_exact': exact, 'rng_after_exact': rng_equal,
        'measured_start_rng_sha256': hashlib.sha256(repr(state).encode()).hexdigest(),
        'frozen_native_trace_sha256': native['trace_sha256'],
        'fresh_trace_sha256': hashlib.sha256(text.encode()).hexdigest()})
    if not exact or not rng_equal:
        raise ValueError('Unmodified control does not reproduce Phase01; modified comparison withheld')
    direct_row = deepcopy(baseline)
    direct_row.update(variant='legacy_exact', compilation_reused=False,
        compile_seconds=direct['Elapsed Time (s)'], timing_scope='original run_benchmark region',
        legacy_exact_instructions=True, legacy_exact_rng=True)
    rows.append(direct_row)
    write(out / 'rows.json', rows)
    if request['track'] == 'phase5':
        from phase05_comparison_worker import execute_variants
        return execute_variants(runner, raw, request, circuit, state, baseline, rows, out, sys.modules[__name__])
    for name in request['variants']:
        config = load_options(CODE / 'configs/variants' / ('lookahead.' + name + '.json'))
        stats, context = modified_benchmark(runner, raw, request, config, circuit, state)
        text = instruction_text(stats)
        variant_out = out / name
        variant_out.mkdir()
        (variant_out / 'instructions.txt').write_text(text, encoding='utf-8', newline='\n')
        write(variant_out / 'parking_diagnostics.json', {
            'statistics': context.statistics(), 'decisions_sample': context.decisions,
            'batches_sample': context.batches, 'lookahead_options': config,
            'baseline_options': native['options'], 'layout_sha256': fingerprint(native['layout'])})
        groups, diagnostics = rft_groups(text)
        trace = build_trace(groups, circuit, pilot_geometry_profile(geometry),
            origin={'kind': 'matched_phase04', 'original_register_complete': True,
                    'lookahead_options': config}, timing='two_transfer_stages', diagnostics=diagnostics)
        before = time.perf_counter()
        row = score(trace, request, name, variant_out, stats['Elapsed Time (s)'],
            compilation_reused=False, timing_scope='original run_benchmark region INCLUDING event-index construction and parking',
            layout_sha256=fingerprint(native['layout']), h=config['h'], gamma=config['gamma'])
        row['scoring_seconds'] = time.perf_counter() - before
        row['delta_extended_E_vs_original'] = (
            row['extended_E'] - baseline['extended_E']
            if row['accepted_schedule'] and baseline['accepted_schedule']
            and row['extended_E'] is not None and baseline['extended_E'] is not None else None)
        rows.append(row)
        write(out / 'rows.json', rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--grid', type=int, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(WORK):
        raise ValueError('Use a new output inside btp_work')
    out.mkdir(parents=True)
    os.chdir(out)
    request = read(os.environ['BTP_COMPARISON_REQUEST'])
    if args.grid != request['job']['grid'] or args.seed != request['job']['seed']:
        raise ValueError('Worker/request controls differ')
    result = {'status': 'error', 'track': request['track'], 'rows': [],
              'hash_seed': os.environ.get('PYTHONHASHSEED'), 'code_root': str(CODE)}
    try:
        rows = execute(request, args.input, out)
        result.update(rows=rows, status='ok' if all(row['status'] == 'ok' for row in rows)
                      else ('error' if any(row['status'] == 'error' for row in rows) else
                            'invalid' if any(row['status'] == 'invalid' for row in rows) else 'unsupported'))
    except Exception as exc:
        if (out / 'rows.json').exists():
            result['rows'] = read(out / 'rows.json')
        result['error'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    write(out / 'result.json', result)
    print(json.dumps({'status': result['status'], 'rows': len(result['rows'])}), flush=True)
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
