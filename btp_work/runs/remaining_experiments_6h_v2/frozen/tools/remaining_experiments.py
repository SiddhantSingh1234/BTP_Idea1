"""Frozen, resumable, six-hour measurement controller. No research analysis.

All completed old experiments remain untouched. One Windows-owned process family
runs at a time; per-cell censoring and a shared cumulative time budget are explicit.
"""
import argparse
from copy import deepcopy
import csv
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
CODE = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get('BTP_WORK_ROOT', CODE)).resolve()
sys.path[:0] = [str(CODE), str(CODE / 'tools')]
SUITES = ('weighting', 'assignment', 'hardware', 'workloads', 'scale')
TERMINAL = {'ok', 'invalid', 'unsupported', 'timeout', 'out_of_memory', 'error', 'reused_quality'}


def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path, value):
    path = Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def allowed_study(path):
    path = Path(path).resolve()
    if path.parent != WORK / 'runs': raise ValueError('Study must be directly under btp_work/runs')
    return path


def normalize(original, name, family, study, generator, geometry=None, layout=None):
    from qiskit import QuantumCircuit, qasm2, transpile
    from implementation.trace.model import circuit_from_pairs, fingerprint
    directory = study / 'inputs' / name;directory.mkdir(parents=True)
    (directory / 'original.qasm').write_text(qasm2.dumps(original), encoding='utf-8', newline='\n')
    started = time.perf_counter()
    full = transpile(original, basis_gates=['cz', 'h', 's', 't', 'rx', 'ry', 'rz'], optimization_level=0, seed_transpiler=42)
    pairs = [tuple(full.find_bit(q).index for q in i.qubits) for i in full.data if i.operation.name == 'cz']
    skeleton = QuantumCircuit(original.num_qubits)
    for a, b in pairs: skeleton.cz(a, b)
    (directory / 'normalized.qasm').write_text(qasm2.dumps(skeleton), encoding='utf-8', newline='\n')
    circuit = circuit_from_pairs(original.num_qubits, pairs)
    layers = {}
    for gate in circuit['gates']: layers.setdefault(gate['logical_layer'], []).append(gate['qubits'])
    baseline = read(WORK / 'configs/baselines/rft_snapshot.json')
    case = {'case_id': name, 'family': family, 'circuit': circuit,
        'schedule': [('Time ' + str(k), v) for k, v in sorted(layers.items())],
        'layout': layout or baseline['layout']['frozen_slots'],
        'geometry': geometry or {'rows': 11, 'columns': 11, 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.},
        'baseline_options': baseline['options'], 'generator': generator,
        'original_path': str((directory / 'original.qasm').relative_to(WORK)),
        'normalized_path': str((directory / 'normalized.qasm').relative_to(WORK)),
        'original_sha256': sha(directory / 'original.qasm'), 'normalized_sha256': sha(directory / 'normalized.qasm'),
        'circuit_sha256': fingerprint(circuit), 'normalization_seconds': time.perf_counter() - started,
        'normalization': 'pinned Qiskit1.3.1 opt0 CZ/H/S/T/RX/RY/RZ seed42; physical scope CZ only; original QASM preserved'}
    write(directory / 'case.json', case)
    return case, str((directory / 'case.json').relative_to(WORK))


def freeze(study):
    frozen = study / 'frozen'
    files = list((WORK / 'implementation').rglob('*.py')) + list((WORK / 'configs').rglob('*.json'))
    tools = ['remaining_experiments.py', 'bounded_experiment_worker.py', 'baseline_campaign.py',
             'run_paper_focus.py', 'phase06_memory.py', 'corrected_dasatom_worker.py']
    files += [WORK / 'tools' / name for name in tools]
    files += [WORK / 'vendor/NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a/src/compiler_core.py']
    vendor = WORK / 'vendor/DasAtom-73a6bdf0fd200b2733745211eaf2e0c1e17f496a'
    files += list(vendor.rglob('*.py'))
    for directory in [vendor, WORK / 'vendor/NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a']:
        files += [p for p in directory.glob('*') if p.is_file() and 'license' in p.name.lower()]
    files += [WORK / 'configs/environment/requirements-py313-win64.lock', WORK / 'configs/environment/requirements-py313-win64.txt']
    hashes = {}
    for source in sorted(set(files)):
        relative = source.relative_to(WORK);target = frozen / relative
        target.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(source, target)
        hashes[relative.as_posix()] = sha(target)
    return hashes


def prepare(study, hours=6., smoke=False):
    if not 0 < hours <= 6: raise ValueError('MaxHours must be positive and at most six')
    manifest_path = study / 'manifest.json'
    if manifest_path.exists():
        manifest = verify(study)
        if manifest['max_seconds'] != hours * 3600 or manifest['smoke'] != smoke:
            raise ValueError('Existing study has different frozen budget/test identity')
        return manifest
    study.mkdir(parents=True, exist_ok=True)
    if (study / 'PREPARING.json').exists():
        raise ValueError('Incomplete preparation retained; use a fresh study name rather than overwriting it')
    write(study / 'PREPARING.json', {'started_utc': now(), 'status': 'preparing'})
    from implementation.trace.model import fingerprint
    old_protocol = read(WORK / 'runs/idea1_extension_v1/protocol.json')
    old_results = list(csv.DictReader((WORK / 'runs/idea1_extension_v1/campaign/results.csv').open(encoding='utf-8-sig')))
    base_cases = {}
    for case in old_protocol['cases']:
        path = study / 'inputs' / case['case_id'] / 'case.json'
        write(path, case);base_cases[case['case_id']] = (case, str(path.relative_to(WORK)))
    references = {(r['case'], int(r['seed'])): r for r in old_results
                  if r['variant'] == 'L1A1R0' and r['quality_sample'].lower() == 'true' and r['status'] == 'ok'}
    jobs = [];seen = set()
    def add(job):
        if job['id'] in seen: return
        seen.add(job['id']);jobs.append(job)
    def reference(case_name, seed):
        identity = f'reference__{case_name}__s{seed}'
        add({'id': identity, 'suite': 'reference', 'kind': 'reuse', 'seed': seed,
             'case_id': case_name, 'case_path': base_cases[case_name][1], 'timeout': 0,
             'source': references[case_name, seed], 'source_csv': 'runs/idea1_extension_v1/campaign/results.csv'})
        return identity
    def measure(suite, name, seed, label, **options):
        case, path = base_cases[name]
        add({'id': f'{suite}__{name}__s{seed}__{label}', 'suite': suite, 'kind': 'compile',
             'case_id': name, 'case_path': path, 'seed': seed, 'variant': label,
             'timeout': 18, 'grid': case['geometry']['rows'], 'reference_id': reference(name, seed), **options})
    if smoke:
        name = old_protocol['cases'][0]['case_id']
        measure('weighting', name, 42, 'critical', weight_mode='critical_remaining_depth')
        measure('assignment', name, 42, 'no_heating', remove_term='heating')
        measure('hardware', name, 42, 'heating_double', profile='heating_double')
        case, path = base_cases[name]
        add({'id': 'smoke__direct_uniform', 'suite': 'weighting', 'kind': 'compile', 'case_id': name,
             'case_path': path, 'seed': 42, 'variant': 'uniform', 'grid': 11, 'timeout': 30})
        add({'id': 'smoke__repair', 'suite': 'assignment', 'kind': 'compile', 'case_id': name,
             'case_path': path, 'seed': 42, 'variant': 'repair', 'repair': 'small', 'grid': 11, 'timeout': 30})
        add({'id': 'smoke__dasatom', 'suite': 'workloads', 'kind': 'dasatom', 'case_id': name,
             'case_path': path, 'seed': 42, 'variant': 'dasatom', 'grid': 11, 'timeout': 30})
        add({'id': 'smoke__timeout', 'suite': 'scale', 'kind': 'timeout_test', 'seed': 42,
             'variant': 'deliberate_timeout_validation', 'grid': 11, 'timeout': .3})
    else:
        for name in base_cases:
            for seed in [41, 42, 43]:
                reference(name, seed)
                for mode in ['uniform', 'critical_remaining_depth']:
                    for gamma in [.5, .9, 1.]:
                        if mode == 'uniform' and gamma == .9: continue
                        measure('weighting', name, seed, f'{mode}_gamma{gamma}', weight_mode=mode, gamma=gamma)
                for term in ['conflict', 'future', 'heating', 'transfer']:
                    measure('assignment', name, seed, 'without_' + term, remove_term=term)
        for name in ['qft_10', '4mod5-v1_22', 'qaoa_n8_p2_g702', 'qv_n8_d4_s702']:
            for seed in [41, 42, 43]:
                for profile in ['heating_half', 'heating_double', 'acceleration_half', 'acceleration_double',
                                'coherence_short', 'coherence_long', 'transfer_lower', 'transfer_higher']:
                    measure('hardware', name, seed, profile, profile=profile)
                for grid in [20, 35]:
                    measure('hardware', name, seed, f'parking_area_grid{grid}', grid=grid)
        from qiskit import QuantumCircuit
        from qiskit.circuit.library import QFT, quantum_volume
        import networkx as nx
        for n in [10, 12]:
            graph_seed = 900 + n
            edges = sorted(tuple(sorted(e)) for e in nx.random_regular_graph(3, n, seed=graph_seed).edges())
            for depth in [2, 4]:
                q = QuantumCircuit(n);q.h(range(n))
                angles = [(float(.17 + .09*i), float(.23 + .07*i)) for i in range(depth)]
                for gamma, beta in angles:
                    for a, b in edges: q.rzz(2*gamma, a, b)
                    q.rx(2*beta, range(n))
                name = f'qaoa_n{n}_p{depth}_g{graph_seed}'
                base_cases[name] = normalize(q, name, 'qaoa', study,
                    {'type': 'genuine QAOA cost/mixer circuit', 'graph_seed': graph_seed, 'degree': 3,
                     'edges': edges, 'p': depth, 'angles_gamma_beta': angles})
            for depth in [8, 16]:
                seed = 1000 + n
                name = f'qv_n{n}_d{depth}_s{seed}'
                base_cases[name] = normalize(quantum_volume(n, depth=depth, seed=seed), name, 'quantum_volume', study,
                    {'type': 'Haar-random SU4 pair model', 'depth': depth, 'generator_seed': seed})
        for name, (case, path) in list(base_cases.items()):
            if name in {c['case_id'] for c in old_protocol['cases']}: continue
            for seed in [41, 42, 43]:
                for label, options, cap in [
                    ('rft_snapshot', {'lookahead': 'legacy_exact', 'assignment': 'phase04_reference'}, 45),
                    ('rft_corrected', {'lookahead': 'legacy_exact', 'assignment': 'sum_distance_expanded'}, 60),
                    ('proposed_small', {'repair': 'small'}, 90), ('dasatom_corrected', {'kind': 'dasatom'}, 60)]:
                    add({'id': f'workloads__{name}__s{seed}__{label}', 'suite': 'workloads', 'kind': 'compile',
                         'case_id': name, 'case_path': path, 'seed': seed, 'variant': label, 'grid': 11,
                         'timeout': cap, **options})
        # Use the feasible primary-baseline grid: existing corrected DasAtom
        # QFT60 took about17s on11x11 versus1224s on35x35. Do not spend the
        # limited campaign on large-grid VF2 jobs already known to be costly.
        # 100 loaded atoms fit in121 sites; the fixed original interaction
        # slots are shared by both RFT controls and the proposed method.
        baseline = read(WORK / 'configs/baselines/rft_snapshot.json')
        slots = baseline['layout']['frozen_slots']
        geometry = {'rows': 11, 'columns': 11, 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.}
        for n in range(65, 101, 5):
            name = 'qft_' + str(n)
            case, path = normalize(QFT(n, do_swaps=True).decompose(), name, 'qft', study,
                                   {'type': 'exact QFT with final swaps', 'N': n, 'approximation_degree': 0}, geometry, slots)
            base_cases[name] = (case, path)
            for seed in [42, 43]:
                for label, options, cap in [
                    ('rft_snapshot', {'lookahead': 'legacy_exact', 'assignment': 'phase04_reference'}, 45),
                    ('rft_corrected', {'lookahead': 'legacy_exact', 'assignment': 'sum_distance_expanded'}, 75),
                    ('proposed_small', {'repair': 'small'}, 150), ('dasatom_corrected', {'kind': 'dasatom'}, 90)]:
                    add({'id': f'scale__{name}__s{seed}__{label}', 'suite': 'scale', 'kind': 'compile',
                         'case_id': name, 'case_path': path, 'seed': seed, 'variant': label, 'grid': 11,
                         'timeout': cap, **options})
    # New finite-bank resource points reuse the old synthetic physical input;
    # these are resource transforms, explicitly separate from planner gains.
    stress = 'runs/phase_03/pilot_03/raw/sources/synthetic_heating'
    for banks in ([1, 8] if smoke else [1, 2, 8]):
        for threshold in ([15] if smoke else [12, 15, 25]):
            add({'id': f'hardware__cooling_b{banks}_t{threshold}', 'suite': 'hardware', 'kind': 'cooling',
                 'seed': 42, 'grid': 8, 'timeout': 18, 'banks': banks, 'threshold': threshold,
                 'source_trace': stress, 'variant': f'cooling_b{banks}_t{threshold}'})
    # Jobs run by suite priority; small decision ablations are never displaced
    # by a large expensive VF2/QFT job. Shared controls are imported once.
    order = {'reference': -1, 'weighting': 0, 'assignment': 1, 'hardware': 2, 'workloads': 3, 'scale': 4}
    jobs.sort(key=lambda j: (order[j['suite']], j['case_id'] if 'case_id' in j else '', j['seed'], j['id']))
    copied = freeze(study)
    source_inputs = {}
    for _, path in base_cases.values():
        case = read(WORK / path);source_inputs[path] = sha(WORK / path)
        for key in ['normalized_path', 'original_path']: source_inputs[case[key]] = sha(WORK / case[key])
    for name in ['metadata.json', 'events.jsonl']:
        source_inputs[stress + '/' + name] = sha(WORK / stress / name)
    for source in ['runs/idea1_extension_v1/campaign/results.csv']:
        source_inputs[source] = sha(WORK / source)
    cap = sum(j['timeout'] for j in jobs)
    if not smoke and cap > 5.25 * 3600:
        raise AssertionError('Declared worker caps exceed the permitted experiment portfolio')
    manifest = {'schema': 'remaining_experiments.bounded.v1', 'prepared_utc': now(), 'smoke': smoke,
        'max_seconds': hours * 3600, 'max_worker_cap_sum_seconds': cap, 'jobs': jobs,
        'frozen_files': copied, 'input_sha256': source_inputs,
        'quality_seed_policy': 'large QFT:2 routing seeds; larger QAOA/QV and small ablations:3 routing seeds; private planner seed/layout fixed; resource choice justified by six-hour cap',
        'timing_policy': 'one timed execution per new seed/setting; old same-seed repeats retained as variability evidence; no invented confidence interval',
        'critical_weight_definition': 'parking only: remaining CZ-DAG longest-path gate count, normalized by maximum among queried resolved events; assignment future estimator unchanged',
        'scope': 'measurement-only bounded remaining-study portfolio; no automatic research interpretation, reports or slides',
        'censoring': 'timeout/OOM/unsupported/error outcomes retained; no same-cap retry except interrupted owned-worker attempts',
        'memory_cap_bytes': 4294967296, 'threads': 1, 'hash_seed': 0,
        'native_device_and_historical_provenance_limits': 'unchanged; runtime completion cannot manufacture calibration or missing paper identity'}
    write(study / 'manifest.json', manifest)
    write(study / 'manifest.sha256.json', {'sha256': sha(study / 'manifest.json')})
    write(study / 'budget.json', {'spent_seconds': 0., 'max_seconds': manifest['max_seconds'], 'updated_utc': now()})
    (study / 'PREPARING.json').rename(study / 'preparation_record.json')
    return manifest


def verify(study):
    manifest = read(study / 'manifest.json')
    if sha(study / 'manifest.json') != read(study / 'manifest.sha256.json')['sha256']:
        raise ValueError('Frozen manifest changed')
    for name, digest in manifest['frozen_files'].items():
        if sha(study / 'frozen' / name) != digest: raise ValueError('Frozen source changed: ' + name)
    for name, digest in manifest['input_sha256'].items():
        if sha(WORK / name) != digest: raise ValueError('Frozen input changed: ' + name)
    return manifest


def attempts(study, job):
    return sorted((study / 'measurements' / job['id']).glob('attempt_*/attempt_record.json'))


def outcome(study, job):
    paths = attempts(study, job)
    for path in reversed(paths):
        record = read(path)
        if record.get('status') in TERMINAL: return record
    return read(paths[-1]) if paths else None


def summarize(study, manifest):
    rows = [];counts = {}
    for job in manifest['jobs']:
        record = outcome(study, job)
        status = (record or {}).get('status', 'not_run')
        counts[status] = counts.get(status, 0) + 1
        row = {k: job.get(k) for k in ['id', 'suite', 'case_id', 'variant', 'seed', 'kind', 'reference_id', 'timeout']}
        row.update(status=status, accepted_schedule=False)
        if record:
            row.update(record.get('result') or {})
            row['status'] = status
            row['record_path'] = record.get('record_path')
            row['process_wall_seconds'] = record.get('process_wall_seconds')
            row['observed_family_peak_bytes'] = record.get('peak_working_set_bytes')
        for key, value in list(row.items()):
            if isinstance(value, (dict, list)): row[key] = json.dumps(value, sort_keys=True)
        rows.append(row)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    target = study / 'results.csv';tmp = study / 'results.csv.tmp'
    with tmp.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields);writer.writeheader();writer.writerows(rows)
    tmp.replace(target)
    result = {'updated_utc': now(), 'planned_cells': len(rows), 'status_counts': counts,
              'all_cells_terminal': all(row['status'] in TERMINAL for row in rows),
              'new_accepted_schedules': sum(r['status'] == 'ok' and r.get('accepted_schedule') is True for r in rows),
              'research_analysis_performed': False, 'reports_or_slides_built': False}
    write(study / 'summary.json', result)
    return result


def import_reference(study, job):
    from implementation.trace.model import fingerprint
    row = job['source'];case = read(WORK / job['case_path'])
    if row['normalized_sha256'] != case['normalized_sha256'] or row['circuit_sha256'] != fingerprint(case['circuit']):
        raise ValueError('Reused control has different normalized input')
    schedule = read(WORK / row['final_bundle_directory'] / 'schedule.json')
    if fingerprint(schedule) != row['final_schedule_sha256']:
        raise ValueError('Reused control schedule changed')
    result = {'status': 'reused_quality', 'accepted_schedule': True, 'extended_E': float(row['E']),
              'makespan_us': float(row['makespan_us']), 'normalized_sha256': row['normalized_sha256'],
              'schedule_sha256': row['final_schedule_sha256'], 'final_bundle': row['final_bundle_directory'],
              'compile_validate_repair_seconds': None,
              'timing_scope': 'immutable validated old quality only; old timer not relabelled a fresh sample'}
    path = study / 'measurements' / job['id'] / 'attempt_01/attempt_record.json'
    write(path, {'status': 'reused_quality', 'result': result, 'source_csv': job['source_csv'],
                 'source_raw_result': row['raw_result'], 'record_path': str(path.relative_to(WORK))})


def run(study, suite):
    if CODE != study / 'frozen': raise ValueError('Run the frozen controller through the PowerShell launcher')
    import msvcrt
    import baseline_campaign
    import run_paper_focus as bounded
    def acquire(path):
        path.parent.mkdir(parents=True, exist_ok=True);handle = path.open('a+b')
        if path.stat().st_size == 0: handle.write(b'0');handle.flush()
        handle.seek(0)
        try: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1);return handle
        except OSError: handle.close();return None
    def release(handle):
        if handle:
            handle.seek(0);msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1);handle.close()
    local = acquire(study / 'controller.lock')
    if local is None: return {'state': 'already_running'}
    global_lock = None;sleep_api = None
    started = time.monotonic();initial_spent = read(study / 'budget.json')['spent_seconds']
    budget = read(study / 'budget.json')['max_seconds']
    state = {'state': 'starting', 'controller_pid': os.getpid(), 'suite': suite, 'started_utc': now(),
             'analysis_will_run_automatically': False}
    def pulse(extra=None):
        state.update(extra or {});state.update(updated_utc=now(), spent_seconds=initial_spent + time.monotonic()-started,
                                               remaining_seconds=max(0., budget-initial_spent-(time.monotonic()-started)))
        write(study / 'progress.json', state)
        write(study / 'budget.json', {'spent_seconds': state['spent_seconds'], 'max_seconds': budget, 'updated_utc': now()})
    def stop(): return (study / 'STOP').exists() or initial_spent + time.monotonic()-started >= budget
    try:
        manifest = verify(study)
        bounded.ROOT = WORK
        baseline_campaign.WORK = WORK;baseline_campaign.ROOT = WORK.parent
        (WORK / '.compiler-tools/tmp').mkdir(parents=True, exist_ok=True)
        if (study / 'STOP').exists(): (study / 'STOP').rename(study / ('stop_acknowledged_' + str(time.time_ns())))
        sleep_api = ctypes.WinDLL('kernel32', use_last_error=True).SetThreadExecutionState
        sleep_api.argtypes = [ctypes.c_uint];sleep_api.restype = ctypes.c_uint
        if not sleep_api(0x80000001): raise OSError('Cannot inhibit automatic idle sleep')
        while global_lock is None:
            if stop(): pulse({'state': 'stopped_or_budget_exhausted'});return state
            global_lock = acquire(WORK / 'runs/model_comparison_execution.lock')
            if global_lock is None: pulse({'state': 'waiting_for_other_experiment'});time.sleep(2)
        # Avoid overlapping original-baseline timings as well as other models.
        while True:
            baseline_lock = acquire(WORK / 'runs/phase01_frozen_baseline_v1/controller.lock')
            if baseline_lock: release(baseline_lock);break
            if stop(): pulse({'state': 'stopped_or_budget_exhausted'});return state
            pulse({'state': 'waiting_for_original_baseline'});time.sleep(2)
        for pending in (study / 'measurements').glob('*/attempt_*/request.json'):
            if not (pending.parent / 'attempt_record.json').exists():
                write(pending.parent / 'attempt_record.json', {**read(pending), 'status': 'interrupted_controller_exit', 'result': None,
                      'record_path': str((pending.parent / 'attempt_record.json').relative_to(WORK))})
        selected = [j for j in manifest['jobs'] if suite == 'all' or j['suite'] == suite]
        dependencies = {j.get('reference_id') for j in selected}
        selected = [j for j in manifest['jobs'] if j in selected or j['id'] in dependencies]
        for job in selected:
            prior = outcome(study, job)
            if prior and prior.get('status') in TERMINAL: continue
            if stop(): break
            if len(attempts(study, job)) >= 2:
                pulse({'state': 'interrupted_attempt_limit', 'current_cell': job['id']});continue
            if job['kind'] == 'reuse': import_reference(study, job);continue
            remaining = budget-initial_spent-(time.monotonic()-started)
            if remaining < job['timeout'] + 8:
                # Preserve the declared cap; never relabel a reduced-cap attempt.
                pulse({'state': 'cell_deferred_insufficient_remaining_budget', 'current_cell': job['id']});continue
            verify(study)
            request = study / 'requests' / (job['id'] + '.json')
            write(request, job)
            wrapped = {'target_id': job['id'], 'seed': job['seed'], 'grid': job.get('grid', 11),
                       'expected_normalized_sha256': sha(request)}
            pulse({'state': 'running', 'current_cell': job['id']})
            record = bounded.bounded_job(wrapped, job['timeout'], output_root=study / 'measurements',
                worker_path=CODE / 'tools/bounded_experiment_worker.py',
                router_path=CODE / 'implementation/budgeted_study/weighting.py', input_path=request,
                env_extra={'BTP_WORK_ROOT': str(WORK), 'BTP_VENDOR_ROOT': str(CODE / 'vendor')},
                progress_callback=lambda details: pulse({'state': 'running', 'current_cell': job['id'], **details}),
                stop_check=stop, heartbeat_gap_limit=60)
            summarize(study, manifest)
            pulse({'state': 'cell_finished', 'current_cell': job['id'], 'last_status': record['status']})
            if record['status'].startswith('interrupted'): break
        summary = summarize(study, manifest)
        selected_terminal = all((outcome(study, j) or {}).get('status') in TERMINAL for j in selected)
        pulse({'state': 'selected_measurements_finished' if selected_terminal else 'stopped_or_budget_deferred',
               'current_cell': None, **summary})
        return state
    except Exception as exc:
        pulse({'state': 'controller_error', 'error': {'type': type(exc).__name__, 'message': str(exc)}})
        raise
    finally:
        pulse()
        if sleep_api: sleep_api(0x80000000)
        release(global_lock);release(local)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare', 'run', 'status', 'stop'])
    p.add_argument('--study', type=Path, required=True);p.add_argument('--suite', choices=['all', *SUITES], default='all')
    p.add_argument('--max-hours', type=float, default=6.);p.add_argument('--smoke', action='store_true')
    args = p.parse_args();study = allowed_study(args.study)
    if args.mode == 'prepare':
        m = prepare(study, args.max_hours, args.smoke)
        result = {'state': 'prepared_not_started', 'planned_cells': len(m['jobs']),
                  'worker_cap_sum_seconds': m['max_worker_cap_sum_seconds'], 'max_hours': m['max_seconds']/3600}
    elif args.mode == 'run': result = run(study, args.suite)
    elif args.mode == 'stop': write(study / 'STOP', {'requested_utc': now()});result = {'state': 'stop_requested'}
    else:
        result = {'progress': read(study / 'progress.json') if (study / 'progress.json').exists() else {'state': 'prepared_not_started'},
                  'budget': read(study / 'budget.json'),
                  'summary': read(study / 'summary.json') if (study / 'summary.json').exists() else None}
    print(json.dumps(result));return 0


if __name__ == '__main__': raise SystemExit(main())
