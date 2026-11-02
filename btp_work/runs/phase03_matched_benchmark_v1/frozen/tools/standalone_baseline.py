"""Freeze and run the paper-only Phase01 baseline without an active agent.

Only prepare reads mutable implementation files. Run must execute the frozen
copy. One OS lock owns a study; every worker has a bounded, durable attempt.
"""
import argparse
import csv
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import msvcrt
import os
from pathlib import Path
import platform
import shutil
import statistics
import sys
import time

sys.dont_write_bytecode = True
CODE = Path(__file__).resolve().parents[1]
DEFAULT = CODE / 'runs/phase01_frozen_baseline_v1'
DAS = 'DasAtom-73a6bdf0fd200b2733745211eaf2e0c1e17f496a'
RFT = 'NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a'


def now(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def packages():
    return {d.metadata['Name'].lower().replace('_', '-'): d.version
            for d in importlib.metadata.distributions()}


def study_path(value):
    study = Path(value).resolve()
    work = study.parent.parent
    if study.parent.name != 'runs' or work.name != 'btp_work':
        raise ValueError('Study must be a direct child of btp_work/runs')
    return study, work


def lock(study):
    handle = (study / 'controller.lock').open('a+b')
    # Reading the locked byte itself fails on Windows before locking() can
    # report contention. File size is safe to inspect while another owner runs.
    if (study / 'controller.lock').stat().st_size == 0:
        handle.write(b'0'); handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close(); return None
    return handle


def unlock(handle):
    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1); handle.close()


def prepare(study, work):
    if study.exists():
        if not (study / 'manifest.json').exists():
            raise ValueError('Incomplete preparation; preserve it and use a new study name')
        verify(study); return read(study / 'manifest.json')
    plan = read(work / 'configs/studies/paper_focus_v2.json')
    assert len(plan['jobs']) == 132
    study.mkdir(parents=True)
    files = {}
    def copy(source, relative):
        target = study / relative
        if target.exists():
            if sha(target) != sha(source): raise ValueError('Snapshot path collision')
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files[relative] = sha(target)
    code = ['tools/standalone_baseline.py', 'tools/corrected_dasatom_worker.py',
            'tools/run_paper_focus.py', 'tools/baseline_campaign.py',
            'tools/phase00_smoke.py', 'implementation/__init__.py']
    for folder, module in [('trace', 'model'), ('adapters', 'upstream'),
                           ('validation', 'checker'), ('metrics', 'legacy'),
                           ('corrected', 'dasatom_routes')]:
        code += [f'implementation/{folder}/__init__.py', f'implementation/{folder}/{module}.py']
    code += [f'vendor/{DAS}/DasAtom_fun.py', f'vendor/{DAS}/Enola/route.py']
    code += [f'vendor/{RFT}/dasatom/DasAtom-main/DasAtom_fun.py', f'vendor/{RFT}/dasatom/DasAtom-main/Enola/route.py']
    code += [p.relative_to(work).as_posix() for p in (work / f'vendor/{RFT}/src').glob('*.py')]
    for vendor in [DAS, RFT]:
        code += [p.relative_to(work).as_posix() for p in (work / 'vendor' / vendor).glob('LICENSE*')]
    for name in code: copy(work / name, 'frozen/' + name)
    for name in ['configs/studies/paper_focus_v2.json', 'configs/environment/environment.json',
                 'configs/environment/requirements-py313-win64.lock']:
        copy(work / name, 'frozen/' + name)
    jobs = []
    for original in plan['jobs']:
        job = dict(original)
        normalized = f"benchmarks/current_baseline_v1/normalized/{job['family']}/{job['case']}_native.qasm"
        assert sha(work / normalized) == job['expected_normalized_sha256']
        assert sha(work / job['raw_path']) == job['raw_sha256']
        copy(work / normalized, 'frozen/' + normalized)
        copy(work / job['raw_path'], 'frozen/' + job['raw_path'])
        job['frozen_input'] = 'frozen/' + normalized
        evidence = []
        for previous in job['all_existing_attempts']:
            assert sha(work / previous['record']) == previous['sha256']
            relative = 'references/' + Path(previous['record']).as_posix()
            copy(work / previous['record'], relative)
            evidence.append(relative)
        job['frozen_native_records'] = evidence
        reference = job['selected_reference']
        if reference:
            for source in (work / reference['worker']).iterdir():
                if source.is_file(): copy(source, 'references/' + source.relative_to(work).as_posix())
            record_path = work / reference['record']
            audit = work / 'reports/phase_02/live_audit_v2/attempts' / record_path.parent.parent.name / record_path.parent.name
            for name in ['audit.json', 'trace_manifest.json']:
                copy(audit / name, 'references/' + (audit / name).relative_to(work).as_posix())
        cached = work / 'runs/paper_focus_v2/cached_corrections_05' / job['target_id']
        if cached.exists():
            for source in cached.rglob('*'):
                if source.is_file(): copy(source, 'references/' + source.relative_to(work).as_posix())
        if job['algorithm'] == 'dasatom':
            job['timeout_seconds'] = 3600 if job['case'] == 'qv_n16_d5' else (6000 if job['case'] == 'square_root_7' else 1800)
        jobs.append(job)
    # Cheap measurements first; the nine missing layouts last. No repeated matrix.
    jobs.sort(key=lambda j: (j['algorithm'] == 'dasatom', j['selected_reference'] is None,
                             j['grid'], j['family'] != 'fig4_qft',
                             int(j['case'].split('_')[1]) if j['family'] == 'fig4_qft' else 0, j['case']))
    contract = {
        'baseline': 'RFT pinned native7 reused; DasAtom pinned with declared discrete correctness repairs',
        'rft_targets': 66, 'dasatom_targets': 66, 'inputs': 27,
        'phase04_comparison': 'Run the same 66 RFT input/grid targets on a separately frozen completed Phase04 implementation. DasAtom is the unchanged anchor.',
        'seed': 42, 'hash_seed': 0, 'threads': 1, 'register': 'full declared register',
        'r_int_grid_units': 2, 'r_blk_grid_units': 4,
        'rft_timer': 'original run_benchmark timed region; excludes preprocessing/offline layout/warmup/imports/scoring',
        'rft_warmup': 'one upstream reference warmup, preserve exact original initial layout and options',
        'dasatom_timer': 'fresh corrected pipeline, grid/partition/embedding/gate grouping/repair; no warmup; different from RFT timer',
        'phase04_timer_requirement': 'Match original RFT timed region, include new event index and heuristic construction/calls; do not compare unlike timer scopes',
        'timing_controls': 'Retain all RFT samples/range/CV. Before claiming speedups check host drift with small paired unchanged-RFT controls; no whole-matrix blanket repeats.',
        'quality_scoring': 'Same frozen trace legacy scorer and profile for before/after. Extended model scores must use one separately frozen common profile.',
        'physical_coverage': 'Known discrete constraints checked. Native minimum trajectory clearance/calibrated fidelity remain unsupported.',
        'paper_revision_evidence': 'unresolved', 'heuristics_in_baseline': False}
    write(study / 'comparison_contract.json', contract)
    files['comparison_contract.json'] = sha(study / 'comparison_contract.json')
    manifest = {'schema': 'standalone-baseline.v1', 'created_utc': now(), 'owner': '/root',
                'study': str(study), 'work': str(work), 'python_version': platform.python_version(),
                'packages': packages(), 'jobs': jobs, 'files': files, 'serial': True,
                'new_measurements': 66, 'reused_rft_targets': 66, 'monitor_gap_limit_seconds': 60,
                'idle_sleep_prevention': True, 'manual_sleep_shutdown': 'May interrupt. Long monitor gaps invalidate the interrupted attempt; resume skips durable successes.',
                'phase_01_complete': False}
    write(study / 'manifest.json', manifest)
    (study / 'manifest.sha256').write_text(sha(study / 'manifest.json') + '\n', encoding='ascii')
    write(study / 'progress.json', {'state': 'prepared', 'updated_utc': now(), 'new_measurements_completed': 0})
    return manifest


def verify(study, runtime=False):
    manifest = read(study / 'manifest.json')
    if sha(study / 'manifest.json') != (study / 'manifest.sha256').read_text().strip():
        raise ValueError('Frozen manifest changed')
    for name, expected in manifest['files'].items():
        if sha(study / name) != expected: raise ValueError('Frozen file changed: ' + name)
    if runtime and (packages() != manifest['packages'] or platform.python_version() != manifest['python_version']):
        raise ValueError('Python environment changed; preserve study and restore pinned environment')
    return manifest


def records(study, job):
    return [(p, read(p)) for p in sorted((study / 'measurements' / job['target_id']).glob('attempt_*/attempt_record.json'))]


def summarize(study):
    manifest = read(study / 'manifest.json'); rows = []; complete = 0; held = 0
    for job in manifest['jobs']:
        row = {k: job[k] for k in ['target_id', 'algorithm', 'family', 'case', 'grid', 'expected_normalized_sha256']}
        row.update(compile_seconds=None, compile_min_seconds=None, compile_max_seconds=None,
                   compile_sample_count=0, compile_cv=None, runtime_us=None, movement_batches=None,
                   legacy_fidelity=None, physical_validity_claimed=False, record=None)
        if job['algorithm'] == 'rft':
            native = [read(study / p) for p in job['frozen_native_records']]
            samples = [r['worker_result']['native_metrics']['Elapsed Time (s)'] for r in native if r['status'] == 'ok']
            assert samples
            result = next(r['worker_result'] for r in native if r['status'] == 'ok')
            score = result['shared_legacy_score']
            row.update(status='reused_native', compile_seconds=statistics.median(samples),
                       compile_min_seconds=min(samples), compile_max_seconds=max(samples), compile_sample_count=len(samples),
                       compile_cv=statistics.stdev(samples)/statistics.mean(samples) if len(samples)>1 and statistics.mean(samples)>0 else None,
                       runtime_us=score['Total_T (us)'], movement_batches=score['Num Movement Ops'],
                       legacy_fidelity=score['Fidelity (DasAtom Model)'], record=job['frozen_native_records'][0],
                       timing_scope=result['timing_scope'])
        else:
            attempts = records(study, job)
            success = next(((p, r) for p, r in attempts if r['status'] == 'ok'), None)
            if success:
                p, record = success; result = record['result']; worker = p.parent / 'worker'
                validation = read(worker / 'validation.json')
                if not validation['structural_valid']: raise ValueError('Successful record has validation errors')
                score = read(worker / 'metrics.json')['legacy']; duration = result['corrected_compile_seconds']
                row.update(status='measured_corrected', compile_seconds=duration, compile_min_seconds=duration,
                           compile_max_seconds=duration, compile_sample_count=1,
                           runtime_us=score['runtime_proxy_us'], movement_batches=score['movement_blocks'],
                           legacy_fidelity=score['fidelity_proxy'], record=str(p.relative_to(study)),
                           timing_scope=result['timing_scope'])
                complete += 1
            else:
                status = attempts[-1][1]['status'] if attempts else 'pending'
                row.update(status=status, timing_scope='not measured', record=str(attempts[-1][0].relative_to(study)) if attempts else None)
                held += status in ['timeout', 'out_of_memory', 'unsupported', 'error', 'invalid']
        rows.append(row)
    target = study / 'results.csv'; temp = target.with_suffix('.csv.tmp')
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with temp.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    temp.replace(target)
    summary = {'updated_utc': now(), 'paper_configurations': len(rows), 'reused_rft': 66,
               'new_corrected_dasatom_successes': complete, 'held_failures': held,
               'remaining_corrected_measurements': 66-complete, 'measurement_matrix_complete': complete == 66,
               'phase_01_complete': False, 'remaining_acceptance': 'Final discrepancy analysis, regenerated figure/table, independent dataset gate and handoff review; no exact manuscript provenance claim.',
               'paper_revision_evidence': 'unresolved', 'full_physical_validity_claimed': False}
    write(study / 'summary.json', summary)
    return summary


def status(study):
    handle = lock(study)
    running = handle is None
    if handle is not None: unlock(handle)
    progress = read(study / 'progress.json')
    return {'controller_lock_held': running, 'progress': progress,
            'summary': read(study / 'summary.json') if (study / 'summary.json').exists() else None}


def run(study, work, limit):
    if CODE != study / 'frozen': raise ValueError('Run the frozen tools/standalone_baseline.py; use Start-Phase01Benchmark.ps1')
    handle = lock(study)
    if handle is None: return {'state': 'already_running'}
    sleep_api = None; manifest = None; state = 'error'; current = None
    progress = {'state': 'starting', 'controller_pid': os.getpid(), 'started_utc': now()}
    def heartbeat(extra=None):
        progress.update(extra or {}); progress['updated_utc'] = now(); write(study / 'progress.json', progress)
    def event(value):
        with (study / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'utc': now(), **value}) + '\n'); stream.flush(); os.fsync(stream.fileno())
    try:
        heartbeat(); manifest = verify(study, runtime=True)
        for request_path in (study / 'measurements').glob('*/attempt_*/request.json'):
            attempt = request_path.parent / 'attempt_record.json'
            if not attempt.exists():
                request = read(request_path)
                write(attempt, {**request, 'status': 'interrupted_controller_exit', 'result': None,
                                'recovered_utc': now(), 'reason': 'No committed terminal record; timings not accepted'})
                event({'event': 'recovered_incomplete_attempt', 'record': str(attempt.relative_to(study))})
        if (study / 'STOP').exists():
            (study / 'STOP').rename(study / ('stop_acknowledged_' + str(time.time_ns())))
        # Only the worker family is terminated by the bounded runner. The OS
        # releases this lock on controller exit/crash, making resumption safe.
        import run_paper_focus as runner
        runner.ROOT = work
        env = runner.environment()
        env.update(BTP_WORK_ROOT=str(work), BTP_VENDOR_ROOT=str(study / 'frozen/vendor'),
                   MPLCONFIGDIR=str(work / '.compiler-tools/matplotlib'), XDG_CACHE_HOME=str(work / '.compiler-tools/xdg-cache'),
                   TEMP=str(work / '.compiler-tools/tmp'), TMP=str(work / '.compiler-tools/tmp'))
        sleep_api = ctypes.WinDLL('kernel32', use_last_error=True).SetThreadExecutionState
        sleep_api.argtypes = [ctypes.c_uint]; sleep_api.restype = ctypes.c_uint
        if not sleep_api(0x80000001): raise OSError('Could not prevent automatic idle sleep')
        event({'event': 'controller_started', 'pid': os.getpid(), 'idle_sleep_prevented': True})
        count = 0; state = 'running'; summary = summarize(study)
        for job in manifest['jobs']:
            if job['algorithm'] != 'dasatom': continue
            if (study / 'STOP').exists(): state = 'stopped'; break
            previous = records(study, job)
            if any(r['status'] == 'ok' for _, r in previous): continue
            # Identical failures stay explicit. Raising caps or changing code
            # requires a new, reviewed protocol/study, never an endless retry.
            if any(r['status'] in ['timeout', 'out_of_memory', 'unsupported', 'error', 'invalid'] for _, r in previous): continue
            if limit and count >= limit: state = 'paused_at_limit'; break
            if packages() != manifest['packages']: raise ValueError('Environment changed during campaign')
            for name, expected in manifest['files'].items():
                if name.startswith('frozen/') and ('benchmarks/' not in name) and sha(study / name) != expected:
                    raise ValueError('Frozen code/config changed: ' + name)
            current = job['target_id']
            heartbeat({'state': 'running', 'current_target': current, 'worker_pid': None, 'stage': 'launch', **summary})
            event({'event': 'target_started', 'target_id': current})
            def pulse(details):
                base = study / 'measurements' / current
                stages = sorted(base.glob('attempt_*/worker/stage.json'))
                try: stage = read(stages[-1])['stage'] if stages else 'launch'
                except (OSError, json.JSONDecodeError): stage = 'updating'
                heartbeat({**details, 'stage': stage})
            record = runner.bounded_job(job, job['timeout_seconds'], output_root=study / 'measurements',
                worker_path=study / 'frozen/tools/corrected_dasatom_worker.py',
                router_path=study / 'frozen/implementation/corrected/dasatom_routes.py',
                input_path=study / job['frozen_input'], env_extra=env, progress_callback=pulse,
                stop_check=lambda: (study / 'STOP').exists(), heartbeat_gap_limit=manifest['monitor_gap_limit_seconds'])
            event({'event': 'target_finished', 'target_id': current, 'status': record['status']})
            count += 1; summary = summarize(study)
            if record['status'].startswith('interrupted'):
                state = 'stopped' if record['status'] == 'interrupted_by_user' else 'interrupted'; break
        else:
            state = 'measurements_complete' if summary['measurement_matrix_complete'] else 'finished_with_issues'
        verify(study, runtime=True)
        heartbeat({**summary, 'state': state, 'current_target': None, 'worker_pid': None})
        return {'state': state, **summary}
    except Exception as exc:
        heartbeat({'state': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}, 'current_target': current})
        event({'event': 'controller_error', 'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        if sleep_api is not None: sleep_api(0x80000000)
        unlock(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'run', 'status', 'stop'])
    parser.add_argument('--study', type=Path, default=DEFAULT)
    parser.add_argument('--limit', type=int, default=0, help='0 = all pending paper targets')
    args = parser.parse_args(); study, work = study_path(args.study)
    if args.limit < 0: raise ValueError('limit must be nonnegative')
    if args.mode == 'prepare':
        manifest = prepare(study, work); result = {'state': 'prepared', 'frozen_files': len(manifest['files']), **summarize(study)}
    elif args.mode == 'run': result = run(study, work, args.limit)
    elif args.mode == 'status': result = status(study)
    else:
        write(study / 'STOP', {'requested_utc': now()}); result = {'state': 'stop_requested', 'scope': 'this study only'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
