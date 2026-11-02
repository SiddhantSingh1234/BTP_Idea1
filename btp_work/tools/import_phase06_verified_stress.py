"""Reuse fresh, identical frozen-worker measurements in the Phase06 rerun."""
import os
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import model_comparison as service


def main():
    study = ROOT / 'runs/phase06_matched_benchmark_v2'
    verification_path = ROOT / 'reports/phase_06/memory_repair_verification.json'
    verification = service.read(verification_path)
    assert verification['passed']
    manifest = service.verify(study, runtime=True)
    revision = service.verify_execution_revision(study)
    assert service.sha(study / 'manifest.json') == verification['study_manifest_sha256']
    assert service.sha(study / 'execution_optimization_v1/manifest.json') == verification['execution_revision_manifest_sha256']
    lock = service.acquire(study / 'controller.lock')
    if lock is None:
        raise ValueError('Controller is already running')
    shared = service.acquire(ROOT / 'runs/model_comparison_execution.lock')
    if shared is None:
        service.release(lock)
        raise ValueError('Another measurement is still running')
    imported = []
    try:
        for evidence in verification['stress_targets']:
            source_record = ROOT / evidence['record']
            record = service.read(source_record)
            job = next(j for j in manifest['jobs'] if j['target_id'] == evidence['target'])
            assert record['status'] == 'ok'
            assert record['worker_sha256'] == revision['files']['tools/model_comparison_worker.py']
            assert record['input_sha256'] == job['expected_normalized_sha256']
            assert record['memory_limit_bytes'] == 4 * 1024**3
            assert record['timeout_seconds'] == manifest['comparison_contract']['timeout_seconds']
            assert record['launcher_protocol'] == 'windows-suspended-job-v1'
            assert len(record['result']['rows']) == 8
            assert {r['variant'] for r in record['result']['rows']} == set(manifest['variants'])
            assert all(r['status'] == 'ok' and r['accepted_schedule'] for r in record['result']['rows'])
            assert record['result']['code_root'] == str(study / 'frozen')
            assert record['result']['hash_seed'] == '0'
            destination = study / 'measurements' / job['target_id'] / 'attempt_01'
            if destination.exists():
                assert service.sha(destination / 'attempt_record.json') == service.sha(source_record)
            else:
                def link_or_copy(src, dst):
                    try:
                        os.link(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)
                    return dst
                shutil.copytree(source_record.parent, destination, copy_function=link_or_copy)
            assert service.sha(destination / 'attempt_record.json') == service.sha(source_record)
            for relative, expected in record['worker_artifact_sha256'].items():
                assert service.sha(destination / relative) == expected, relative
            provenance = {'source_record': str(source_record.relative_to(ROOT)),
                'source_record_sha256': service.sha(source_record),
                'measurement_record': str((destination / 'attempt_record.json').relative_to(ROOT)),
                'verification_sha256': service.sha(verification_path),
                'execution_manifest_sha256': verification['execution_revision_manifest_sha256'],
                'protocol': 'Fresh post-fix run of identical study inputs, frozen worker, seed/profile/budgets, 7200 s/4 GiB/60 s monitor bounds and serial execution lock; no v1 observations imported',
                'raw_bytes_preserved': True,
                'paths': 'Original command/output paths remain as executed; evidence source and canonical hardlink/copy are both retained'}
            service.write(study / 'measurement_imports' / (job['target_id'] + '.json'), provenance)
            imported.append(job['target_id'])
        summary = service.summarize(study, manifest)
        service.write(study / 'verified_stress_import.json', {'imported_targets': imported, 'rows': 8 * len(imported),
            'original_v1_measurements_imported': False, 'summary': summary})
        print({'imported_targets': imported, 'summary': summary})
    finally:
        service.release(shared)
        service.release(lock)


if __name__ == '__main__':
    main()
