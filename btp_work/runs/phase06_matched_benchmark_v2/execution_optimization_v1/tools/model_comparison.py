"""Freeze/resume comparisons of the Phase01 matrix under Phases 03 through 06.

No Phase01 controller or scientific source is changed. Only saved schedules are
rescored for Phase03; Phase04 adds matched original-region timed compilations.
"""
import argparse
from copy import deepcopy
import csv
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import shutil
import statistics
import sys
import time

sys.dont_write_bytecode = True
EXECUTION = Path(__file__).resolve().parents[1]
CODE = EXECUTION.parent / 'frozen' if EXECUTION.name == 'execution_optimization_v1' else EXECUTION
sys.path.insert(0, str(CODE / 'tools'))
sys.path.insert(0, str(EXECUTION / 'tools'))
import standalone_baseline as baseline_service
import run_paper_focus as bounded

RFT = 'NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a'
VARIANTS = ['next_events_h1', 'next_events_h2', 'next_events_h4', 'next_events_h8']
PHASE5_VARIANTS = ['phase04_reference', 'sum_distance', 'bottleneck_distance',
    'bottleneck_time', 'composite_sum', 'composite_bottleneck',
    'sum_distance_expanded', 'composite_bottleneck_expanded',
    'composite_no_conflict', 'composite_no_future']
PHASE6_POLICIES = ['sum_distance', 'composite_bottleneck_expanded']
PHASE6_BUDGETS = ['disabled', 'zero', 'small', 'standard']
PHASE6_VARIANTS = [policy + '__' + budget for policy in PHASE6_POLICIES for budget in PHASE6_BUDGETS]


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def acquire(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+b')
    if path.stat().st_size == 0:
        handle.write(b'0')
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return handle
    except OSError:
        handle.close()
        return None


def release(handle):
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    handle.close()


def baseline_running(path):
    handle = acquire(Path(path) / 'controller.lock')
    if handle is None:
        return True
    release(handle)
    return False


def prepare(study, work, baseline, track):
    if study.exists():
        manifest = verify(study)
        if manifest['track'] != track or manifest['baseline'] != str(baseline):
            raise ValueError('Study already belongs to another track/baseline')
        return manifest
    base = baseline_service.verify(baseline)
    study.mkdir(parents=True)
    files = {}

    def copy(source, relative):
        target = study / relative
        if target.exists():
            if sha(target) != sha(source):
                raise ValueError('Frozen path collision: ' + relative)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        files[relative] = sha(target)

    code = ['tools/model_comparison.py', 'tools/model_comparison_worker.py', 'tools/phase05_comparison_worker.py',
            'tools/Start-ModelComparison.ps1', 'tools/standalone_baseline.py',
            'tools/run_paper_focus.py', 'tools/baseline_campaign.py']
    code += [p.relative_to(work).as_posix() for p in (work / 'implementation').rglob('*.py')]
    code += [p.relative_to(work).as_posix() for p in (work / 'vendor' / RFT / 'src').glob('*.py')]
    code += [p.relative_to(work).as_posix() for p in (work / 'vendor' / RFT).glob('LICENSE*')]
    code += [f'vendor/{RFT}/dasatom/DasAtom-main/DasAtom_fun.py',
             f'vendor/{RFT}/dasatom/DasAtom-main/Enola/route.py']
    code += ['configs/hardware/extended_no_cooling.json']
    code += ['configs/variants/lookahead.' + name + '.json' for name in VARIANTS]
    code += ['configs/environment/requirements-py313-win64.lock']
    if track == 'phase6':
        code += ['tools/phase06_comparison_worker.py', 'tools/phase06_memory.py']
        code += ['reports/phase_06/version_manifest.json', 'reports/phase_06/gate_01.json']
        code += ['configs/variants/assignment.' + name + '.json' for name in PHASE6_POLICIES]
        code += ['configs/variants/repair.' + name + '.json' for name in PHASE6_BUDGETS]
        version = read(work / 'reports/phase_06/version_manifest.json')
        if read(work / 'reports/phase_06/gate_01.json')['status'] != 'complete':
            raise ValueError('Phase06 implementation acceptance is incomplete')
        for relative, expected in version['artifact_sha256'].items():
            if relative.startswith(('implementation/', 'configs/')) and sha(work / relative) != expected:
                raise ValueError('Accepted Phase06 scientific source changed: ' + relative)
    if track == 'phase5':
        code += ['configs/variants/assignment.' + name + '.json' for name in PHASE5_VARIANTS]
    for name in sorted(set(code)):
        copy(work / name, 'frozen/' + name)
    copy(baseline / 'manifest.json', 'baseline_manifest.json')
    copy(baseline / 'comparison_contract.json', 'baseline_comparison_contract.json')
    phase5_controls = {}
    if track == 'phase6':
        phase5 = work / 'runs/phase05_matched_benchmark_v1'
        previous = verify(phase5)
        if previous['track'] != 'phase5' or previous['baseline_manifest_sha256'] != sha(baseline / 'manifest.json'):
            raise ValueError('Phase06 requires Phase05 with the same frozen baseline')
        if not read(phase5 / 'summary.json')['matrix_complete']:
            raise ValueError('Complete Phase05 before freezing Phase06 matched controls')
        copy(phase5 / 'manifest.json', 'phase05_reference_manifest.json')
        copy(phase5 / 'results.csv', 'phase05_reference_results.csv')
        with (phase5 / 'results.csv').open(encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle):
                if row['variant'] not in PHASE6_POLICIES:
                    continue
                if row['status'] != 'ok' or row['accepted_schedule'] != 'True':
                    raise ValueError('Unaccepted Phase05 starting control')
                source = work / row['output'] / 'instructions.txt'
                if sha(source) != row['instructions_sha256']:
                    raise ValueError('Phase05 starting instructions changed')
                relative = 'phase05_references/' + row['target_id'] + '/' + row['variant'] + '/instructions.txt'
                copy(source, relative)
                compatibility = source.parent.parent / 'compatibility.json'
                compatibility_relative = 'phase05_references/' + row['target_id'] + '/compatibility.json'
                copy(compatibility, compatibility_relative)
                phase5_controls.setdefault(row['target_id'], {})[row['variant']] = {
                    'instructions': relative, 'instructions_sha256': sha(source),
                    'extended_E': float(row['extended_E']), 'profile_sha256': row['profile_sha256'],
                    'geometry_sha256': row['geometry_sha256'], 'normalized_sha256': row['normalized_sha256'],
                    'measured_start_rng_sha256': read(compatibility)['measured_start_rng_sha256']}
        if len(phase5_controls) != 66 or any(set(v) != set(PHASE6_POLICIES) for v in phase5_controls.values()):
            raise ValueError('Phase06 requires both accepted Phase05 controls for all 66 targets')
    jobs = []
    for original in base['jobs']:
        if track in ['phase4', 'phase5', 'phase6'] and original['algorithm'] != 'rft':
            continue
        job = deepcopy(original)
        for name, expected in [(original['frozen_input'], original['expected_normalized_sha256']),
                               ('frozen/' + original['raw_path'], original['raw_sha256'])]:
            if sha(baseline / name) != expected:
                raise ValueError('Baseline input hash mismatch')
            copy(baseline / name, name)
        if job['algorithm'] == 'rft':
            relative = 'references/' + job['selected_reference']['record'].replace('\\', '/')
            copy(baseline / relative, relative)
            native = read(baseline / relative)['worker_result']
            worker = 'references/' + job['selected_reference']['worker'].replace('\\', '/')
            for name in ['instructions.txt', 'normalized.qasm', 'result.json']:
                copy(baseline / worker / name, worker + '/' + name)
            if sha(baseline / worker / 'instructions.txt') != native['trace_sha256']:
                raise ValueError('Selected RFT instructions changed')
            samples = []
            for relative in job['frozen_native_records']:
                copy(baseline / relative, relative)
                record = read(baseline / relative)
                if record['status'] == 'ok':
                    samples.append(record['worker_result']['native_metrics']['Elapsed Time (s)'])
            job.update(native=native, original_compile_seconds=statistics.median(samples),
                       original_compile_samples=samples, source_worker=worker)
        if track == 'phase6':
            job['phase5_controls'] = phase5_controls[job['target_id']]
        jobs.append(job)
    if len(jobs) != (132 if track == 'phase3' else 66):
        raise ValueError('Expected the complete frozen paper matrix')
    manifest = {
        'schema': 'matched-model-comparison.v1', 'created_utc': now(),
        'track': track, 'baseline': str(baseline), 'baseline_manifest_sha256': sha(baseline / 'manifest.json'),
        'jobs': jobs, 'files': files, 'variants': PHASE6_VARIANTS if track == 'phase6' else PHASE5_VARIANTS if track == 'phase5' else VARIANTS if track == 'phase4' else ['original_phase3'],
        'packages': baseline_service.packages(), 'python_version': sys.version,
        'comparison_contract': {
            'phase3': 'Saved Phase01 RFT and available corrected DasAtom schedules, retimed/scored only; compile times reused explicitly',
            'phase4': '66 matched RFT targets; fresh unmodified control plus h1/2/4/8; DasAtom stays the Phase03-scored anchor',
            'phase5': '66 matched RFT targets; fresh unchanged control, Phase04 h4, corrected sum and fixed assignment controls/ablations; no DasAtom compilation',
            'phase5_parking': 'Fixed next_events_h4 gamma .9; original controls remain separately labelled',
            'phase5_objective_controls': 'Compare composite vs corrected sum at the SAME candidate budget; orientation correction and candidate expansion are separate axes',
            'phase5_excluded_diagnostics': 'All-slot and optional-displacement pilot variants are not in the fixed full-matrix protocol',
            'geometry': 'Same declared analytical two-plane geometry for every control/variant; no calibrated native physical claim',
            'model': 'extended_no_cooling.v1; cubic timing/heating, per-atom transfers and common exposure',
            'quality_scope': 'normalized CZ skeleton; no cooling without extra hardware',
            'seed': 42, 'hash_seed': 0, 'threads': 1,
            'timing': 'Original benchmark_runner.run_benchmark region, including event index/parking; frozen module setup and scoring excluded',
            'warmup': 'One unchanged reference warmup; modified warmup then restore unchanged measured-start global RNG',
            'diagnostics': 'Bounded eight snapshots; same production FutureEventIndex and FuturePotential APIs',
            'best_k_selected': False, 'workers': 'one serial owned family, observed 4GiB cap, finite wall cap',
            'timeout_seconds': 7200 if track == 'phase6' else 1800 if track in ['phase4', 'phase5'] else 600,
            'execution': 'New comparisons serialize with each other and wait while the Phase01 controller lock is held',
            'failures': 'Keep invalid/unsupported/timeouts/errors; do not retry unchanged terminal failures; resume missing source schedules',
        },
    }
    if track == 'phase6':
        manifest['comparison_contract'].update(
            phase6='66 RFT targets x two fixed Phase05 policies x disabled/zero/small/standard repair; 528 rows; no DasAtom reruns',
            phase6_reference='Starting instructions and common-model E must reproduce frozen completed Phase05 controls',
            timing='Separate end-to-end prepare/compile/validate plus repair wall time; includes rejected trials, revalidation and checkpoints. Not comparable directly with Phase05 original compiler timer',
            warmup='One prepare warmup per starting policy, discarded; every repair budget starts from the same prepared incumbent',
            diagnostics='Production Phase06 full replay/boundaries/audits retained; no scientific source changes',
            budgets='Unchanged accepted Phase06 options: disabled, zero, 4 evaluations, 12 evaluations; deterministic caps; no outcome tuning')
        manifest['comparison_contract'].update(
            execution_memory_revision='phase06_memory.v2: lossless immutable replay snapshots, streaming JSON/hash, optional discarded event-audit suppression, explicit cleanup; original scientific sources unchanged',
            prior_campaign='phase06_matched_benchmark_v1 remains immutable; v2 reruns all 66 targets for comparable execution costs')
    write(study / 'manifest.json', manifest)
    (study / 'manifest.sha256').write_text(sha(study / 'manifest.json') + '\n', encoding='ascii')
    write(study / 'progress.json', {'state': 'prepared', 'updated_utc': now(), 'track': track})
    return manifest


def verify_execution_revision(study):
    revision = study / 'execution_optimization_v1'
    manifest = read(revision / 'manifest.json')
    if sha(revision / 'manifest.json') != (revision / 'manifest.sha256').read_text().strip():
        raise ValueError('Execution revision manifest changed')
    if manifest['parent_manifest_sha256'] != sha(study / 'manifest.json'):
        raise ValueError('Execution revision belongs to a different comparison')
    for relative, expected in manifest['files'].items():
        path = (revision / relative).resolve()
        if not path.is_relative_to(revision.resolve()) or sha(path) != expected:
            raise ValueError('Execution revision file changed: ' + relative)
    return manifest


def verify(study, runtime=False):
    manifest = read(study / 'manifest.json')
    if sha(study / 'manifest.json') != (study / 'manifest.sha256').read_text().strip():
        raise ValueError('Comparison manifest changed')
    for name, expected in manifest['files'].items():
        if sha(study / name) != expected:
            raise ValueError('Frozen comparison file changed: ' + name)
    if runtime and (sys.version != manifest['python_version']
                    or baseline_service.packages() != manifest['packages']):
        raise ValueError('Frozen comparison Python environment changed')
    if sha(Path(manifest['baseline']) / 'manifest.json') != manifest['baseline_manifest_sha256']:
        raise ValueError('Original baseline manifest changed')
    if EXECUTION == study / 'execution_optimization_v1': verify_execution_revision(study)
    return manifest


def records(study, target):
    return [(p, read(p)) for p in sorted((study / 'measurements' / target).glob('attempt_*/attempt_record.json'))]


def source_request(study, manifest, job):
    if job['algorithm'] == 'rft':
        return {'kind': 'rft_instructions', 'instructions': str(study / job['source_worker'] / 'instructions.txt')}, job['original_compile_seconds'], job['native']['timing_scope']
    baseline = Path(manifest['baseline'])
    success = next(((p, value) for p, value in records(baseline, job['target_id']) if value['status'] == 'ok'), None)
    if success is None:
        return None
    record_path, record = success
    source = record_path.parent
    destination = study / 'source_observations' / job['target_id'] / source.name
    names = ['worker/trace/metadata.json', 'worker/trace/events.jsonl',
             'worker/result.json', 'worker/metrics.json', 'worker/validation.json']
    evidence = {}
    for name in names:
        expected = record['worker_artifact_sha256'][name]
        if sha(source / name) != expected:
            raise ValueError('Committed DasAtom source artifact changed')
        target = destination / name
        if target.exists() and sha(target) != expected:
            raise ValueError('Previously observed DasAtom source changed')
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        evidence[name] = expected
    source_info = {'kind': 'dasatom_trace', 'worker': str(destination / 'worker'),
                   'source_record': str(record_path), 'source_record_sha256': sha(record_path),
                   'source_artifact_sha256': evidence}
    return source_info, record['result']['corrected_compile_seconds'], record['result']['timing_scope']


def summarize(study, manifest=None):
    manifest = manifest or read(study / 'manifest.json')
    rows = []
    counts = {}
    for job in manifest['jobs']:
        attempts = records(study, job['target_id'])
        selected = next(((p, r) for p, r in attempts if r['status'] == 'ok'), attempts[-1] if attempts else None)
        variants = manifest['variants'] if manifest['track'] in ['phase3', 'phase6'] else ['original_phase3', 'legacy_exact'] + manifest['variants']
        existing = {}
        if selected:
            p, record = selected
            result = record.get('result') or {}
            existing = {row['variant']: row for row in result.get('rows', [])}
            state = record['status']
        else:
            state = 'pending' if job['algorithm'] == 'rft' else 'waiting_for_phase01_schedule'
        counts[state] = counts.get(state, 0) + 1
        for variant in variants:
            row = {key: job[key] for key in ['target_id', 'algorithm', 'family', 'case', 'grid']}
            row.update(variant=variant, status=state, accepted_schedule=False)
            row.update(existing.get(variant, {}))
            row['attempt_status'] = state
            row['attempt_record'] = str(selected[0].relative_to(study)) if selected else None
            if selected and selected[1].get('timing_contaminated'):
                row.update(compile_seconds=None, timing_contaminated=True)
                if manifest['track'] == 'phase6':
                    for field in ['baseline_compile_validate_seconds', 'repair_wall_seconds',
                                  'end_to_end_compile_validate_repair_seconds', 'candidate_compile_seconds',
                                  'candidate_validation_scoring_seconds', 'prefix_local_scoring_seconds',
                                  'candidate_generation_seconds']:
                        row[field] = None
            rows.append(row)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    temporary = study / 'results.csv.tmp'
    with temporary.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(study / 'results.csv')
    summary = {'updated_utc': now(), 'track': manifest['track'], 'targets': len(manifest['jobs']),
               'target_status_counts': counts, 'rows': len(rows), 'accepted_rows': sum(row['accepted_schedule'] for row in rows),
               'matrix_complete': counts.get('ok', 0) == len(manifest['jobs']),
               'baseline_modified': False, 'native_physical_validity_claimed': False,
               'best_k_selected': False, 'model_profile': 'extended_no_cooling.v1'}
    write(study / 'summary.json', summary)
    return summary


def run(study, work, limit):
    if CODE != study / 'frozen' or EXECUTION not in [CODE, study / 'execution_optimization_v1']:
        raise ValueError('Execute frozen controller via Start-ModelComparison.ps1')
    handle = acquire(study / 'controller.lock')
    if handle is None:
        return {'state': 'already_running'}
    global_handle = None
    sleep_api = None
    progress = {'state': 'starting', 'controller_pid': os.getpid(), 'started_utc': now(), 'execution_revision': EXECUTION.name}

    def heartbeat(extra=None):
        progress.update(extra or {})
        progress['updated_utc'] = now()
        write(study / 'progress.json', progress)

    try:
        manifest = verify(study, runtime=True)
        baseline = Path(manifest['baseline'])
        if (study / 'STOP').exists():
            (study / 'STOP').rename(study / ('stop_acknowledged_' + str(time.time_ns())))
        sleep_api = ctypes.WinDLL('kernel32', use_last_error=True).SetThreadExecutionState
        sleep_api.argtypes = [ctypes.c_uint]
        sleep_api.restype = ctypes.c_uint
        if not sleep_api(0x80000001):
            raise OSError('Could not prevent automatic idle sleep')
        while global_handle is None:
            if (study / 'STOP').exists():
                heartbeat({'state': 'stopped'})
                return {'state': 'stopped'}
            global_handle = acquire(work / 'runs/model_comparison_execution.lock')
            if global_handle is None:
                heartbeat({'state': 'waiting_for_other_model_comparison'})
                time.sleep(3)
        bounded.ROOT = work
        count = 0
        for pending in (study / 'measurements').glob('*/attempt_*/request.json'):
            record = pending.parent / 'attempt_record.json'
            if not record.exists():
                write(record, {**read(pending), 'status': 'interrupted_controller_exit', 'result': None})
        for job in manifest['jobs']:
            while baseline_running(baseline):
                if (study / 'STOP').exists():
                    heartbeat({'state': 'stopped'})
                    return {'state': 'stopped', **summarize(study, manifest)}
                heartbeat({'state': 'waiting_for_phase01', 'current_target': None})
                time.sleep(3)
            if (study / 'STOP').exists():
                heartbeat({'state': 'stopped'})
                return {'state': 'stopped', **summarize(study, manifest)}
            previous = records(study, job['target_id'])
            if any(r['status'] in ['ok', 'timeout', 'out_of_memory', 'unsupported', 'error', 'invalid'] for _, r in previous):
                continue
            if limit and count >= limit:
                heartbeat({'state': 'paused_at_limit', 'current_target': None})
                return {'state': 'paused_at_limit', **summarize(study, manifest)}
            source = source_request(study, manifest, job)
            if source is None:
                continue
            verify(study, runtime=True)
            source_info, seconds, timing_scope = source
            request = {'track': manifest['track'], 'job': job, 'source': source_info,
                       'original_compile_seconds': seconds, 'original_timing_scope': timing_scope,
                       'geometry': {'rows': job['grid'], 'columns': job['grid'], 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.0},
                       'variants': manifest['variants'], 'native': job.get('native'),
                       'raw_input': str(study / 'frozen' / job['raw_path'])}
            request_path = study / 'requests' / job['target_id'] / (str(time.time_ns()) + '.json')
            write(request_path, request)
            contaminated = [False]

            def pulse(details):
                contaminated[0] |= baseline_running(baseline)
                stages = sorted((study / 'measurements' / job['target_id']).glob('attempt_*/worker/stage.json'))
                stage = {}
                if stages:
                    try: stage = read(stages[-1])
                    except (OSError, json.JSONDecodeError): pass
                heartbeat({'state': 'running', 'current_target': job['target_id'], **stage, **details})

            heartbeat({'state': 'running', 'current_target': job['target_id']})
            record = bounded.bounded_job(job, manifest['comparison_contract']['timeout_seconds'],
                output_root=study / 'measurements', worker_path=EXECUTION / 'tools/model_comparison_worker.py',
                router_path=study / 'frozen/implementation/lookahead/integration.py',
                input_path=study / job['frozen_input'],
                env_extra={'BTP_WORK_ROOT': str(work), 'BTP_COMPARISON_REQUEST': str(request_path)},
                progress_callback=pulse, stop_check=lambda: (study / 'STOP').exists(), heartbeat_gap_limit=60)
            contaminated[0] |= baseline_running(baseline)
            if contaminated[0] and manifest['track'] in ['phase4', 'phase5', 'phase6']:
                record.update(status='interrupted_external_benchmark', timing_contaminated=True)
                write(work / record['record_path'], record)
            count += 1
            summarize(study, manifest)
            if record['status'].startswith('interrupted'):
                heartbeat({'state': record['status'], 'current_target': None})
                return {'state': record['status']}
        summary = summarize(study, manifest)
        state = 'measurements_complete' if summary['matrix_complete'] else 'finished_with_issues_or_missing_sources'
        heartbeat({'state': state, 'current_target': None, **summary})
        return {'state': state, **summary}
    except Exception as exc:
        heartbeat({'state': 'error', 'error': {'type': type(exc).__name__, 'message': str(exc)}})
        raise
    finally:
        if sleep_api is not None:
            sleep_api(0x80000000)
        if global_handle is not None:
            release(global_handle)
        release(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'run', 'status', 'stop'])
    parser.add_argument('--track', choices=['phase3', 'phase4', 'phase5', 'phase6'], required=True)
    parser.add_argument('--study', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    if args.limit < 0:
        raise ValueError('Limit must be nonnegative')
    work = Path(os.environ.get('BTP_WORK_ROOT', CODE)).resolve()
    default_study = 'phase06_matched_benchmark_v2' if args.track == 'phase6' else 'phase0' + {'phase3': '3', 'phase4': '4', 'phase5': '5'}[args.track] + '_matched_benchmark_v1'
    study = (args.study or work / 'runs' / default_study).resolve()
    if study.parent != work / 'runs':
        raise ValueError('Comparison study must be a direct child of btp_work/runs')
    baseline = (args.baseline or work / 'runs/phase01_frozen_baseline_v1').resolve()
    if args.mode != 'prepare' and read(study / 'manifest.json')['track'] != args.track:
        raise ValueError('Study belongs to a different comparison track')
    if args.mode == 'prepare':
        manifest = prepare(study, work, baseline, args.track)
        result = {'state': 'prepared', **summarize(study, manifest)}
    elif args.mode == 'run':
        result = run(study, work, args.limit)
    elif args.mode == 'status':
        result = {'controller_lock_held': baseline_running(study), 'progress': read(study / 'progress.json'),
                  'summary': read(study / 'summary.json')}
        result = getattr(baseline_service, 'apply_final_acceptance', lambda path, value: value)(study, result)
    else:
        write(study / 'STOP', {'requested_utc': now()})
        result = {'state': 'stop_requested', 'scope': str(study)}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
