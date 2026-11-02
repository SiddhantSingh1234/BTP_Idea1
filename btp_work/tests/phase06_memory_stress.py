"""Paired candidate equivalence and real 4 GiB regression cases for Phase06."""
import argparse
import ctypes
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import model_comparison as service


def compare_workers(new_worker, original, target):
    old = next(p.parent / 'worker' for p, r in service.records(original, target) if r['status'] == 'ok')
    scientific = ['extended_E', 'extended_fidelity', 'extended_makespan_us', 'baseline_E',
        'candidate_evaluations', 'accepted_repairs', 'repair_status',
        'original_schedule_sha256', 'final_schedule_sha256', 'profile_sha256', 'geometry_sha256']
    a = {r['variant']: r for r in service.read(old / 'rows.json')}
    b = {r['variant']: r for r in service.read(new_worker / 'rows.json')}
    assert set(a) == set(b)
    candidates = 0
    for name, row in b.items():
        assert all(row[k] == a[name][k] for k in scientific), (target, name)
        policy, budget = name.split('__')
        left = service.read(old / policy / budget / 'result.json')['audit']
        right = service.read(new_worker / policy / budget / 'result.json')['audit']
        keys = ['candidate_id', 'boundary_key', 'kind', 'override_plan', 'actual_full_E', 'local_E_delta',
            'valid', 'prefix_unchanged', 'decision', 'accepted', 'candidate_schedule_sha256',
            'candidate_instructions_sha256', 'final_rng_sha256', 'final_budget', 'prefix_evidence']
        assert [{k: x.get(k) for k in keys} for x in left] == [{k: x.get(k) for k in keys} for x in right], (target, name)
        candidates += len(right)
    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--case', action='append', help='Optional case:grid stress target; repeatable')
    args = parser.parse_args()
    out, study = args.out.resolve(), args.study.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh output under btp_work')
    out.mkdir(parents=True)
    original = ROOT / 'runs/phase06_matched_benchmark_v1'
    manifest = service.verify(study, runtime=True)
    original_hashes = {p.name: service.sha(original / p.name) for p in [original / 'manifest.json', original / 'results.csv']}
    integration = ROOT / 'runs/phase06_memory_acceptance_02'
    compared, candidates = 0, 0
    for job in manifest['jobs'][:2]:
        path, _ = service.records(integration, job['target_id'])[0]
        candidates += compare_workers(path.parent / 'worker', original, job['target_id'])
        compared += 8
    third = next((ROOT / 'reports/phase_06/memory_integration_tests_02/different_family').glob('*/attempt_01/worker'))
    candidates += compare_workers(third, original, third.parents[1].name)
    compared += 8
    service.write(out / 'equivalence.json', {'passed': True, 'rows': compared, 'candidate_audits': candidates,
        'checks': 'Exact scores, schedule/instruction hashes, proposals, decisions, prefix proofs, budgets and final routing RNG'})
    print(json.dumps({'equivalence_passed': True, 'rows': compared, 'candidate_audits': candidates}), flush=True)
    lock = service.acquire(ROOT / 'runs/model_comparison_execution.lock')
    if lock is None:
        raise ValueError('Another timed comparison is running')
    api = ctypes.WinDLL('kernel32', use_last_error=True).SetThreadExecutionState
    api.argtypes = [ctypes.c_uint]
    api.restype = ctypes.c_uint
    assert api(0x80000001)
    evidence = []
    execution = study / 'execution_optimization_v1'
    service.verify_execution_revision(study)
    try:
        for specification in args.case or ['square_root_7:11', 'qft_60:11']:
            case, grid = specification.split(':')
            grid = int(grid)
            job = next(j for j in manifest['jobs'] if j['case'] == case and j['grid'] == grid)
            old_record = service.records(original, job['target_id'])[0][1]
            assert old_record['status'] == 'out_of_memory'
            source, seconds, scope = service.source_request(study, manifest, job)
            request = {'track': 'phase6', 'job': job, 'source': source, 'native': job['native'],
                'original_compile_seconds': seconds, 'original_timing_scope': scope,
                'geometry': {'rows': grid, 'columns': grid, 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.},
                'variants': manifest['variants'], 'raw_input': str(study / 'frozen' / job['raw_path'])}
            request_path = out / (case + '_request.json')
            service.write(request_path, request)
            last = [0.]
            def pulse(details):
                service.write(out / 'progress.json', {'target': job['target_id'], **details})
                if time.monotonic() - last[0] >= 30:
                    print(json.dumps({'target': case, **details}), flush=True)
                    last[0] = time.monotonic()
            service.bounded.ROOT = ROOT
            record = service.bounded.bounded_job(job, 7200, output_root=out / 'raw',
                worker_path=execution / 'tools/model_comparison_worker.py',
                router_path=execution / 'tools/phase06_memory.py', input_path=study / job['frozen_input'],
                env_extra={'BTP_WORK_ROOT': str(ROOT), 'BTP_COMPARISON_REQUEST': str(request_path)},
                progress_callback=pulse, heartbeat_gap_limit=60)
            evidence.append({'target': job['target_id'], 'status': record['status'],
                'peak_working_set_bytes': record['peak_working_set_bytes'],
                'original_oom_peak_bytes': old_record['peak_working_set_bytes'],
                'wall_seconds': record['process_wall_seconds'], 'record': record['record_path']})
            service.write(out / 'stress_results.json', evidence)
            assert record['status'] == 'ok', evidence[-1]
            assert record['memory_limit_bytes'] == 4 * 1024**3
            rows = record['result']['rows']
            assert len(rows) == 8 and all(r['status'] == 'ok' and r['accepted_schedule'] for r in rows)
            assert all(r['phase05_instructions_exact'] and r['baseline_input_unchanged'] and r['caller_rng_restored'] for r in rows)
            assert all(r['delta_extended_E_vs_start'] <= 1e-12 for r in rows)
            assert record['peak_working_set_bytes'] < 4 * 1024**3
        assert original_hashes == {name: service.sha(original / name) for name in original_hashes}
        service.write(out / 'result.json', {'passed': True, 'equivalent_rows': compared,
            'equivalent_candidate_audits': candidates, 'stress_targets': evidence,
            'original_study_preserved': True, 'production_manifest_sha256': service.sha(study / 'manifest.json')})
        print(json.dumps({'passed': True, 'stress_targets': evidence}), flush=True)
    finally:
        api(0x80000000)
        service.release(lock)


if __name__ == '__main__':
    main()
