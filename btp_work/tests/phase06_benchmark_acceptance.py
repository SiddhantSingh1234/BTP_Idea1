"""Integration checks for full-matrix Phase06 launch, resume and accounting."""
import argparse
from copy import deepcopy
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import model_comparison as service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--study', type=Path, required=True)
    args = parser.parse_args()
    out, study = args.out.resolve(), args.study.resolve()
    if out.exists() or study.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh output/study paths')
    out.mkdir(parents=True)
    checkpoints = {}
    protected = [ROOT / 'runs' / name / part for name in [
        'phase01_frozen_baseline_v1', 'phase03_matched_benchmark_v1',
        'phase04_matched_benchmark_v2', 'phase05_matched_benchmark_v1']
        for part in ['manifest.json', 'results.csv']]
    before = {str(p): service.sha(p) for p in protected}
    manifest = service.prepare(study, ROOT, ROOT / 'runs/phase01_frozen_baseline_v1', 'phase6')
    assert len(manifest['jobs']) == 66 and len(manifest['variants']) == 8
    assert len(service.summarize(study, manifest)) > 0
    assert service.read(study / 'summary.json')['rows'] == 528
    checkpoints['complete_frozen_66_by_8_protocol'] = True
    version = service.read(ROOT / 'reports/phase_06/version_manifest.json')
    assert all(service.sha(ROOT / p) == h for p, h in version['artifact_sha256'].items()
        if p.startswith(('implementation/', 'configs/')))
    checkpoints['accepted_phase06_scientific_version_unchanged'] = True
    def launch():
        previous_start = service.read(study / 'progress.json').get('started_utc')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            str(ROOT / 'tools/Start-ModelComparison.ps1'), '-Track', 'phase6', '-Study', str(study), '-Limit', '1'],
            capture_output=True, text=True, encoding='utf-8', timeout=60)
        with (out / 'launches.txt').open('a', encoding='utf-8') as handle:
            handle.write(result.stdout + result.stderr + '\n')
        assert result.returncode == 0, result.stderr
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            progress = service.read(study / 'progress.json')
            if (progress.get('started_utc') != previous_start and not service.baseline_running(study)
                    and progress['state'] == 'paused_at_limit'):
                return
            if progress['state'] in ['error', 'finished_with_issues_or_missing_sources']:
                raise AssertionError(progress)
            time.sleep(1)
        raise TimeoutError('Detached acceptance controller did not finish')
    launch()
    first = service.records(study, manifest['jobs'][0]['target_id'])[0][0]
    first_hash = service.sha(first)
    launch()
    assert service.sha(first) == first_hash
    assert len(service.records(study, manifest['jobs'][0]['target_id'])) == 1
    assert service.read(study / 'summary.json')['target_status_counts']['ok'] == 2
    checkpoints['detached_launcher_limit_and_resume_preserve_committed_results'] = True
    # A different circuit family/grid exercises normalization/register/layout controls.
    job = next(j for j in manifest['jobs'] if j['family'] == 'tableII' and j['case'] == 'bv_n16' and j['grid'] == 35)
    source, seconds, scope = service.source_request(study, manifest, job)
    request = {'track': 'phase6', 'job': job, 'source': source, 'native': job['native'],
        'original_compile_seconds': seconds, 'original_timing_scope': scope,
        'geometry': {'rows': 35, 'columns': 35, 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.},
        'variants': manifest['variants'], 'raw_input': str(study / 'frozen' / job['raw_path'])}
    request_path = out / 'tableII_request.json'
    service.write(request_path, request)
    handle = service.acquire(ROOT / 'runs/model_comparison_execution.lock')
    assert handle is not None
    try:
        service.bounded.ROOT = ROOT
        result = service.bounded.bounded_job(job, 600, output_root=out / 'different_family',
            worker_path=study / 'frozen/tools/model_comparison_worker.py',
            router_path=study / 'frozen/implementation/repair/replay.py', input_path=study / job['frozen_input'],
            env_extra={'BTP_WORK_ROOT': str(ROOT), 'BTP_COMPARISON_REQUEST': str(request_path)})
        assert result['status'] == 'ok', result
    finally:
        service.release(handle)
    results = [service.records(study, j['target_id'])[0][1]['result']['rows'] for j in manifest['jobs'][:2]]
    results.append(result['result']['rows'])
    for rows in results:
        assert len(rows) == 8 and all(r['status'] == 'ok' and r['accepted_schedule'] for r in rows)
        for row in rows:
            assert row['phase05_instructions_exact'] and row['baseline_input_unchanged'] and row['caller_rng_restored']
            assert row['delta_extended_E_vs_start'] <= 1e-12
            cap = {'disabled': 0, 'zero': 0, 'small': 4, 'standard': 12}[row['repair_budget']]
            assert row['candidate_evaluations'] <= cap
            assert row['compile_seconds'] is None and row['end_to_end_compile_validate_repair_seconds'] > 0
            assert row['end_to_end_compile_validate_repair_seconds'] == row['baseline_compile_validate_seconds'] + row['repair_wall_seconds']
            if cap == 0:
                assert row['final_schedule_sha256'] == row['original_schedule_sha256']
    checkpoints['24_real_rows_match_phase05_and_preserve_repair_contracts'] = True
    fake = out / 'contamination'
    fake.mkdir()
    mini = deepcopy(manifest)
    mini['jobs'] = [manifest['jobs'][0]]
    def fake_bounded(job, timeout, **kwargs):
        path = fake / 'measurements' / job['target_id'] / 'attempt_01/attempt_record.json'
        record = {'status': 'ok', 'record_path': str(path.relative_to(ROOT)), 'result': {'rows': results[0]}}
        service.write(path, record)
        return record
    with patch.object(service, 'CODE', fake / 'frozen'), patch.object(service, 'EXECUTION', fake / 'frozen'), \
            patch.object(service, 'verify', return_value=mini), \
            patch.object(service, 'baseline_running', side_effect=[False, True]), \
            patch.object(service, 'source_request', return_value=({}, 1., 'unused')), \
            patch.object(service.bounded, 'bounded_job', side_effect=fake_bounded):
        result = service.run(fake, ROOT, 0)
    assert result['state'] == 'interrupted_external_benchmark'
    with (fake / 'results.csv').open(newline='') as csvfile:
        assert all(r['end_to_end_compile_validate_repair_seconds'] == '' and r['repair_wall_seconds'] == ''
            for r in csv.DictReader(csvfile))
    checkpoints['overlapping_phase01_invalidates_end_to_end_timings'] = True
    assert before == {str(p): service.sha(p) for p in protected}
    checkpoints['four_completed_studies_and_datasets_unchanged'] = True
    service.write(out / 'result.json', {'passed': True, 'checks': checkpoints, 'real_rows': 24,
        'study_manifest_sha256': service.sha(study / 'manifest.json')})
    print(json.dumps({'passed': True, 'checks': checkpoints, 'real_rows': 24}))


if __name__ == '__main__':
    main()
