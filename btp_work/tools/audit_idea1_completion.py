"""Read-only provenance and independent final-schedule audit of bounded studies.

Streams large artifact hashes; never loads compilation/prefix snapshots. Replaying
the published final schedules is independent of trusting their recorded scores;
it is not an independent implementation of the physical model or compiler.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
sys.dont_write_bytecode = True


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    from implementation.repair.artifacts import write as save
    save(path, value)


def locations(row):
    worker = (ROOT / row['record_path']).parent / 'worker'
    bundle = ROOT / row['final_bundle'] if row.get('final_bundle') else worker
    return bundle / 'schedule.json', bundle / 'evaluation.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    study, out = args.study.resolve(), args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('A fresh audit output under btp_work is required')
    out.mkdir(parents=True)
    started = time.perf_counter()
    manifest = read(study / 'manifest.json')
    for name, digest in manifest['frozen_files'].items():
        assert sha(study / 'frozen' / name) == digest, name
    for name, digest in manifest['input_sha256'].items():
        assert sha(ROOT / name) == digest, name
    # Use the exact study implementation for replay, not any later scientific edits.
    sys.path.insert(0, str(study / 'frozen'))
    from implementation.trace.model import fingerprint
    from implementation.movement_error.evaluator import evaluate
    table = list(csv.DictReader((study / 'results.csv').open(encoding='utf-8-sig', newline='')))
    jobs = {r['id']: r for r in manifest['jobs']}
    assert len({r['id'] for r in table}) == len(table) == len(jobs)
    assert {r['id'] for r in table} == set(jobs)
    assert all(r['status'] in {'ok', 'reused_quality', 'unsupported', 'timeout', 'out_of_memory'} for r in table)
    cache, checked = {}, []
    artifacts, artifact_bytes, repair_trials, repair_commits = 0, 0, 0, 0
    for index, row in enumerate(table):
        job = jobs[row['id']]
        record_path = ROOT / row['record_path']
        record = read(record_path)
        assert record['status'] == row['status']
        if row['status'] != 'reused_quality':
            assert record['worker_sha256'] == manifest['frozen_files']['tools/bounded_experiment_worker.py']
            # The inherited launcher names this field router_sha256; this study
            # explicitly supplies the scoped weighting helper in that argument.
            assert record['router_sha256'] == manifest['frozen_files']['implementation/budgeted_study/weighting.py']
            assert record['input_sha256'] == sha(study / 'requests' / (row['id'] + '.json'))
            assert record.get('monitor_error') is None
            for relative, digest in record.get('worker_artifact_sha256', {}).items():
                path = record_path.parent / relative
                assert sha(path) == digest, str(path)
                artifacts += 1
                artifact_bytes += path.stat().st_size
        result = {'id': row['id'], 'status': row['status'], 'suite': row['suite'],
                  'case_id': row['case_id'], 'seed': row['seed'], 'variant': row['variant']}
        if row['status'] in {'ok', 'reused_quality'}:
            assert row['accepted_schedule'].lower() == 'true'
            path, evaluation = locations(row)
            schedule = read(path)
            if job.get('case_path'):
                case = read(ROOT / job['case_path'])
                assert row['normalized_sha256'] == case['normalized_sha256']
                assert schedule['source_trace']['metadata']['circuit'] == case['circuit']
            digest = fingerprint(schedule)
            if row['schedule_sha256']: assert digest == row['schedule_sha256']
            recorded = read(evaluation)
            if digest not in cache:
                fresh = evaluate(schedule, include_audit=False)
                assert fresh['status'] == 'ok' and fresh['valid_for_comparison'], row['id']
                assert fresh['budget'] == recorded['budget'], row['id']
                cache[digest] = {k: fresh[k] for k in ('budget', 'counts', 'makespan_us', 'profile_sha256')}
            value = cache[digest]
            assert math.isclose(value['budget']['total_E'], float(row['extended_E']), rel_tol=1e-13, abs_tol=1e-12)
            assert math.isclose(value['makespan_us'], float(row['makespan_us']), rel_tol=1e-13, abs_tol=1e-8)
            assert math.isclose(sum(value['budget']['terms'].values()), value['budget']['total_E'], rel_tol=1e-13)
            assert math.isclose(value['budget']['fidelity_proxy'], math.exp(-value['budget']['total_E']), abs_tol=1e-15)
            if row['profile_sha256']: assert value['profile_sha256'] == row['profile_sha256']
            result.update(schedule_sha256=digest, replayed_E=value['budget']['total_E'],
                          profile_sha256=value['profile_sha256'], counts=value['counts'])
            repair_path = record_path.parent / 'worker/repair/result.json'
            if repair_path.exists():
                repair = read(repair_path)
                assert repair['candidate_evaluations'] == len(repair['audit']) <= repair['options']['max_evaluations']
                assert repair['final_E'] <= repair['original_E'] + 1e-12
                repair_trials += len(repair['audit'])
                for entry in repair['audit']:
                    assert entry['incumbent_unchanged_after_trial'] and entry['caller_rng_restored_after_trial']
                    if entry.get('accepted'):
                        repair_commits += 1
                        assert entry['valid'] and entry['prefix_unchanged']
                        assert entry['actual_full_E'] < entry['parent_full_E'] - 1e-12
                        evidence = entry['prefix_evidence']
                        assert evidence['incumbent_prefix_sha256'] == evidence['candidate_prefix_sha256']
        elif row['status'] in {'timeout', 'out_of_memory'}:
            assert not (record.get('result') or {}).get('accepted_schedule', False)
            result['censored_at_seconds'] = float(row['timeout'])
            result['last_stage'] = read(record_path.parent / 'worker/stage.json') if (record_path.parent / 'worker/stage.json').exists() else None
            baseline = record_path.parent / 'worker/baseline/bundle.json'
            result['partial_baseline_exists'] = baseline.exists()
            result['partial_baseline_is_not_completed_method'] = True
        else:
            assert job['kind'] == 'cooling'
            assert 'Finite prepared cold banks exhausted' in record['result']['error']
            result['reason'] = record['result']['error']
        checked.append(result)
        if index % 25 == 0:
            write(out / 'progress.json', {'checked': index + 1, 'planned': len(table), 'elapsed_seconds': time.perf_counter() - started})
            print(json.dumps({'checked': index + 1, 'planned': len(table)}), flush=True)
    write(out / 'schedule_replays.json', checked)
    summary = {'status': 'ok', 'study': str(study.relative_to(ROOT)), 'results_sha256': sha(study / 'results.csv'),
               'manifest_sha256': sha(study / 'manifest.json'), 'planned_cells': len(jobs),
               'status_counts': dict(Counter(r['status'] for r in table)), 'all_cells_terminal': True,
               'distinct_final_schedules_independently_replayed': len(cache),
               'accepted_rows': sum(r['status'] in {'ok', 'reused_quality'} for r in table),
               'frozen_files_verified': len(manifest['frozen_files']), 'inputs_verified': len(manifest['input_sha256']),
               'worker_artifacts_verified': artifacts, 'worker_artifact_bytes_streamed': artifact_bytes,
               'repair_trials_record_assertions': repair_trials, 'strict_commits_record_assertions': repair_commits,
               'coverage_limit': 'Common checker and evaluator replay of every final schedule; no recompile of every rejected repair proposal; no device-calibrated fidelity',
               'audit_script_sha256': sha(__file__),
               'elapsed_seconds': time.perf_counter() - started}
    write(out / 'verification.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__': main()
