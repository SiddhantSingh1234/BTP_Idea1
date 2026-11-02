"""Incremental four-family, paired L/A/R experiment over frozen scientific modules.

Only the legacy-parking entry guard is broadened in a private replay function;
the emitted legacy baseline is checked against the unchanged Phase05 compiler.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import csv
import gc
import hashlib
import inspect
import itertools
import json
import os
from pathlib import Path
import random
import sys
import time
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    from implementation.repair.artifacts import write as save
    save(path, value)


@contextmanager
def factorial_replay_scope():
    """Permit exact legacy parking without editing the accepted Phase06 source."""
    import implementation.repair.search as search
    original = search.replay
    source = inspect.getsource(original)
    anchor = "if lookahead['lookahead_policy'] != 'next_events':"
    if source.count(anchor) != 1:
        raise ValueError('Frozen replay guard anchor changed')
    source = source.replace(anchor, "if lookahead['lookahead_policy'] not in ('next_events', 'legacy_exact'):")
    namespace = dict(original.__globals__)
    exec(compile(source, str(Path(__file__)) + '.legacy_guard_only', 'exec'), namespace)
    search.replay = namespace['replay']
    try:
        yield
    finally:
        search.replay = original


def normalize(original, case_id, directory, generator):
    from qiskit import QuantumCircuit, qasm2, transpile
    from implementation.trace.model import circuit_from_pairs, fingerprint
    directory.mkdir(parents=True, exist_ok=False)
    original_path = directory / 'original.qasm'
    original_path.write_text(qasm2.dumps(original), encoding='utf-8', newline='\n')
    started = time.perf_counter()
    full = transpile(original, basis_gates=['cz', 'h', 's', 't', 'rx', 'ry', 'rz'],
                     optimization_level=0, seed_transpiler=42)
    pairs = [tuple(full.find_bit(q).index for q in inst.qubits)
             for inst in full.data if inst.operation.name == 'cz']
    skeleton = QuantumCircuit(original.num_qubits)
    for a, b in pairs:
        skeleton.cz(a, b)
    normalized = directory / 'normalized.qasm'
    normalized.write_text(qasm2.dumps(skeleton), encoding='utf-8', newline='\n')
    # Earliest legal CZ layers, preserving each wire's original CZ order.
    circuit = circuit_from_pairs(original.num_qubits, pairs)
    layers = {}
    for gate in circuit['gates']:
        layers.setdefault(gate['logical_layer'], []).append(gate['qubits'])
    baseline = read(ROOT / 'configs/baselines/rft_snapshot.json')
    case = {'case_id': case_id, 'family': generator['family'], 'circuit': circuit,
            'schedule': [('Time ' + str(i), p) for i, p in sorted(layers.items())],
            'layout': baseline['layout']['frozen_slots'],
            'geometry': {'rows': 11, 'columns': 11, 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.},
            'baseline_options': baseline['options'], 'generator': generator,
            'original_path': original_path.relative_to(ROOT).as_posix(),
            'normalized_path': normalized.relative_to(ROOT).as_posix(),
            'original_sha256': sha(original_path), 'normalized_sha256': sha(normalized),
            'circuit_sha256': fingerprint(circuit),
            'normalization_seconds': time.perf_counter() - started,
            'normalization': 'Qiskit1.3.1 CZ/H/S/T/RX/RY/RZ opt0 seed42; CZ skeleton; one-qubit operations retained in original QASM for semantic restoration'}
    write(directory / 'case.json', case)
    return case


def prepare_study(out):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import quantum_volume
    import networkx as nx
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use a fresh study directory under btp_work')
    out.mkdir(parents=True)
    cases = []
    for n in [5, 10]:
        source = ROOT / 'benchmarks/current_baseline_v1/raw/fig4_qft' / ('qft_' + str(n) + '.qasm')
        cases.append(normalize(QuantumCircuit.from_qasm_file(str(source)), 'qft_' + str(n),
            out / 'inputs' / ('qft_' + str(n)), {'family': 'qft', 'source': source.relative_to(ROOT).as_posix(),
            'source_sha256': sha(source), 'reuse': 'original input reused; factorial combinations/seeds are new'}))
    for name in ['4mod5-v1_22', 'cm152a_212']:
        source = ROOT / 'benchmarks/current_baseline_v1/raw/tableII' / (name + '.qasm')
        if not source.exists():
            raise FileNotFoundError(source)
        cases.append(normalize(QuantumCircuit.from_qasm_file(str(source)), name,
            out / 'inputs' / name, {'family': 'qtetris', 'source': source.relative_to(ROOT).as_posix(),
            'source_sha256': sha(source), 'reuse': 'published input reused; factorial combinations/seeds are new'}))
    for n, seed in [(6, 701), (8, 702)]:
        graph = nx.random_regular_graph(3, n, seed=seed)
        edges = sorted(tuple(sorted(e)) for e in graph.edges())
        qc = QuantumCircuit(n)
        qc.h(range(n))
        gammas, betas = [.31, .57], [.23, .41]
        for gamma, beta in zip(gammas, betas):
            for a, b in edges:
                qc.rzz(2 * gamma, a, b)
            qc.rx(2 * beta, range(n))
        label = f'qaoa_n{n}_p2_g{seed}'
        cases.append(normalize(qc, label, out / 'inputs' / label,
            {'family': 'qaoa', 'graph': 'simple random 3-regular', 'graph_seed': seed,
             'edges': edges, 'p': 2, 'gamma': gammas, 'beta': betas,
             'convention': 'H preparation; exp(-i gamma ZZ) cost and exp(-i beta X) mixer; MaxCut up to sign/constant convention, fixed angles, no optimizer'}))
        qc = quantum_volume(n, depth=4, seed=seed)
        label = f'qv_n{n}_d4_s{seed}'
        cases.append(normalize(qc, label, out / 'inputs' / label,
            {'family': 'quantum_volume', 'model': 'Qiskit Haar-random SU4 pairs with random bipartitions',
             'seed': seed, 'depth': 4, 'metric_measurement_claimed': False}))
    files = list((ROOT / 'implementation').rglob('*.py'))
    files += [Path(__file__), ROOT / 'tools/phase06_memory.py']
    files += list((ROOT / 'configs/variants').glob('*.json')) + [ROOT / 'configs/hardware/extended_no_cooling.json']
    protocol = {'schema': 'incremental_phase07.v1', 'status': 'frozen_before_final_run',
        'cases': cases, 'quality_seeds': [41, 42, 43, 44, 45],
        'timing_repeats_at_seed42': 3, 'quality_units': 'eight circuit instances, five paired routing seeds; repeats never independent quality observations',
        'factorial': {'L': ['legacy_exact', 'next_events_h4'],
                     'A': ['sum_distance_expanded', 'composite_bottleneck_expanded'],
                     'R': ['disabled', 'small']},
        'interpretation': 'A changes composite objective at fixed expanded candidates; L changes parking policy; correction and geometry fixed; R evaluates at most4 candidates',
        'replay_adaptation': 'Private copy changes only legacy-parking entry guard. All baseline instructions/RNG checked against unchanged Phase05 compiler; no accepted source edits',
        'worker_wall_seconds': 240, 'study_wall_budget_seconds': 3600,
        'worker_memory_bytes': 4294967296, 'threads': 1, 'hash_seed': 0,
        'scope': 'additional four-family factorial study; does not replace prior 66-target paper matrices',
        'remaining_large_study': ['QFT through100 matched primary baselines', 'larger QAOA/QV instances', 'weighting ablations beyond implemented controls'],
        'artifact_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in files}}
    write(out / 'protocol.json', protocol)
    print(json.dumps({'prepared': out.as_posix(), 'cases': len(cases), 'planned_quality_rows': len(cases) * 5 * 8,
                      'planned_rows_with_timing_repeats': len(cases) * 7 * 8}), flush=True)


def worker(request_path, seed, grid, out):
    from implementation.assignment.costs import load_options as assignment_options
    from implementation.assignment.integration import compile_schedule
    from implementation.lookahead.potential import load_options as parking_options
    from implementation.movement_error.profiles import load_profile
    from implementation.repair.config import load_options as repair_options
    import implementation.repair.search as search
    from implementation.repair.evaluation import total_E
    from implementation.repair.artifacts import write_bundle, save_result
    from implementation.trace.model import fingerprint
    from phase06_memory import memory_scope
    request = read(request_path)
    case = request['case']
    if seed != request['seed'] or grid != case['geometry']['rows'] or out.exists():
        raise ValueError('Worker request/output mismatch')
    out.mkdir(parents=True)
    profile = load_profile(ROOT / 'configs/hardware/extended_no_cooling.json')
    rows = []
    with memory_scope() as release_contexts:
        with factorial_replay_scope():
            for L, A in itertools.product([0, 1], repeat=2):
                look = parking_options(ROOT / ('configs/variants/lookahead.' + ('next_events_h4' if L else 'legacy_exact') + '.json'))
                assign = assignment_options(ROOT / ('configs/variants/assignment.' + ('composite_bottleneck_expanded' if A else 'sum_distance_expanded') + '.json'))
                label = f'L{L}A{A}'
                before = time.perf_counter()
                baseline = search.prepare(case, look, assign, profile, seed=seed)
                baseline_seconds = time.perf_counter() - before
                if not baseline['evaluation']['accepted_schedule']:
                    raise ValueError('Invalid baseline: ' + label)
                # This independent untouched integration establishes legacy compatibility.
                legacy = compile_schedule(case['schedule'], case['circuit']['num_qubits'], case['layout'],
                    case['geometry'], case['baseline_options'], look, assign, profile,
                    circuit=case['circuit'], routing_seed=seed)
                if legacy['instructions'] != baseline['compilation']['instructions'] or legacy['random_state_after_sha256'] != baseline['compilation']['random_state_after_sha256']:
                    raise AssertionError('Factorial baseline differs from unchanged compiler')
                del legacy
                basepath = out / label / 'baseline'
                write_bundle(basepath, baseline)
                for R in [0, 1]:
                    directory = out / (label + f'R{R}')
                    options = repair_options(ROOT / ('configs/variants/repair.' + ('small' if R else 'disabled') + '.json'))
                    tick = time.perf_counter()
                    result = search.repair(case, look, assign, profile, options, seed=seed, baseline=baseline)
                    repair_seconds = time.perf_counter() - tick
                    saved = save_result(directory, result, basepath)
                    final = result['incumbent']
                    score = final['evaluation']['result']
                    row = {'case': case['case_id'], 'family': case['family'], 'seed': seed,
                        'repeat': request['repeat'], 'quality_sample': request['repeat'] == 0,
                        'L': L, 'A': A, 'R': R, 'variant': label + f'R{R}',
                        'status': 'ok', 'accepted_schedule': final['evaluation']['accepted_schedule'],
                        'E': total_E(score), 'baseline_E': result['original_E'], 'makespan_us': score['makespan_us'],
                        'N': case['circuit']['num_qubits'], 'CZ': len(case['circuit']['gates']),
                        'baseline_compile_validate_seconds': baseline_seconds, 'repair_wall_seconds': repair_seconds,
                        'total_seconds': baseline_seconds + repair_seconds,
                        'candidate_evaluations': result['candidate_evaluations'], 'accepted_repairs': len(result['accepted_history']),
                        'baseline_compatibility_verified': True, 'baseline_input_unchanged': result['baseline_input_unchanged'],
                        'caller_rng_restored': result['caller_rng_restored'],
                        'normalized_sha256': case['normalized_sha256'], 'circuit_sha256': case['circuit_sha256'],
                        'final_schedule_sha256': result['final_schedule_sha256'],
                        'final_bundle_directory': str(Path(saved['final_bundle_directory']).relative_to(ROOT)),
                        'raw_result': str((directory / 'result.json').relative_to(ROOT)),
                        **score['budget']['terms']}
                    if not row['accepted_schedule'] or row['E'] > row['baseline_E'] + 1e-12:
                        raise AssertionError('Factorial retained-incumbent violation')
                    rows.append(row)
                    del final, result
                    release_contexts()
                del baseline
                release_contexts()
    write(out / 'result.json', {'status': 'ok', 'rows': rows})
    print(json.dumps({'case': case['case_id'], 'seed': seed, 'rows': len(rows)}), flush=True)


def run_study(study, pilot=False):
    from run_paper_focus import bounded_job
    protocol = read(study / 'protocol.json')
    for name, digest in protocol['artifact_sha256'].items():
        if sha(ROOT / name) != digest:
            raise AssertionError('Frozen code/config changed: ' + name)
    out = study / ('cost_pilot' if pilot else 'campaign')
    if out.exists():
        raise FileExistsError('Fresh output required: ' + str(out))
    out.mkdir()
    started = time.perf_counter()
    rows, coverage = [], []
    cases = [protocol['cases'][0], next(c for c in protocol['cases'] if c['family'] == 'qaoa')] if pilot else protocol['cases']
    for case in cases:
        for seed in ([42] if pilot else protocol['quality_seeds']):
            for repeat in range(1 if pilot or seed != 42 else protocol['timing_repeats_at_seed42']):
                label = case['case_id'] + f'__s{seed}__r{repeat}'
                request = out / 'requests' / (label + '.json')
                write(request, {'case': case, 'seed': seed, 'repeat': repeat})
                if time.perf_counter() - started >= protocol['study_wall_budget_seconds']:
                    record = {'status': 'unrun_budget', 'record_path': None}
                else:
                    job = {'target_id': label, 'seed': seed, 'grid': 11,
                           'expected_normalized_sha256': sha(request)}
                    record = bounded_job(job, protocol['worker_wall_seconds'], output_root=out / 'raw',
                        worker_path=Path(__file__), router_path=ROOT / 'implementation/repair/search.py',
                        input_path=request, env_extra={'PHASE07_EXTENSION_WORKER': '1'})
                fresh = record.get('result', {}).get('rows', [])
                if record.get('status') == 'ok' and len(fresh) == 8:
                    rows.extend(fresh)
                else:
                    for L, A, R in itertools.product([0, 1], repeat=3):
                        rows.append({'case': case['case_id'], 'family': case['family'], 'seed': seed,
                            'repeat': repeat, 'quality_sample': repeat == 0, 'L': L, 'A': A, 'R': R,
                            'variant': f'L{L}A{A}R{R}', 'status': record['status'], 'accepted_schedule': False})
                coverage.append({'case': case['case_id'], 'family': case['family'], 'seed': seed,
                    'repeat': repeat, 'status': record['status'], 'attempt_record': record.get('record_path'),
                    'process_wall_seconds': record.get('process_wall_seconds'),
                    'peak_working_set_bytes': record.get('peak_working_set_bytes')})
                write(out / 'progress.json', {'completed_rows': len(rows), 'completed_jobs': len(coverage)})
                print(json.dumps(coverage[-1]), flush=True)
    fields = sorted({k for row in rows for k in row})
    with (out / 'results.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    write(out / 'coverage.json', coverage)
    write(out / 'summary.json', {'rows': len(rows), 'quality_rows': sum(r['quality_sample'] for r in rows),
        'ok_rows': sum(r['status'] == 'ok' for r in rows), 'wall_seconds': time.perf_counter() - started,
        'pilot': pilot, 'source_protocol_sha256': sha(study / 'protocol.json')})


def main():
    if os.environ.get('PHASE07_EXTENSION_WORKER'):
        p = argparse.ArgumentParser(); p.add_argument('--input', type=Path, required=True)
        p.add_argument('--grid', type=int, required=True); p.add_argument('--seed', type=int, required=True)
        p.add_argument('--out', type=Path, required=True); args = p.parse_args()
        try:
            worker(args.input, args.seed, args.grid, args.out.resolve()); return 0
        except Exception as exc:
            args.out.mkdir(parents=True, exist_ok=True)
            write(args.out / 'result.json', {'status': 'error', 'error': {'type': type(exc).__name__,
                'message': str(exc), 'traceback': traceback.format_exc()}})
            traceback.print_exc(); return 2
    p = argparse.ArgumentParser(); p.add_argument('mode', choices=['prepare', 'pilot', 'run'])
    p.add_argument('--study', type=Path, required=True); args = p.parse_args()
    study = args.study.resolve()
    if not study.is_relative_to(ROOT): raise ValueError('Study must stay under btp_work')
    if args.mode == 'prepare': prepare_study(study)
    else: run_study(study, pilot=args.mode == 'pilot')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
