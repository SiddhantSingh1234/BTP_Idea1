"""Bind the repaired Phase06 execution to scientific and real-memory evidence."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import model_comparison as service


def main():
    reports = ROOT / 'reports/phase_06'
    study = ROOT / 'runs/phase06_matched_benchmark_v2'
    original = ROOT / 'runs/phase06_matched_benchmark_v1'
    service.verify(study, runtime=True)
    revision = service.verify_execution_revision(study)
    for name, expected in revision['files'].items():
        assert service.sha(ROOT / name) == expected, 'Tested source differs from execution: ' + name
    tests = {'scientific': reports / 'memory_scientific_tests_03/result.json',
        'integration': reports / 'memory_integration_tests_02/result.json',
        'equivalence': reports / 'memory_stress_tests_02/equivalence.json',
        'stress': reports / 'memory_stress_tests_02/result.json'}
    assert all(service.read(p)['passed'] for p in tests.values())
    stress = service.read(tests['stress'])
    assert len(stress['stress_targets']) == 2
    partial_rows = 0
    for target in stress['stress_targets']:
        assert target['status'] == 'ok' and target['peak_working_set_bytes'] < 4 * 1024**3
        path = ROOT / target['record']
        record = service.read(path)
        assert record['status'] == 'ok' and record['memory_limit_bytes'] == 4 * 1024**3
        assert service.sha(path.parent / 'worker/result.json') == record['worker_artifact_sha256']['worker/result.json']
        new = {r['variant']: r for r in record['result']['rows']}
        assert len(new) == 8 and all(r['accepted_schedule'] and r['status'] == 'ok' for r in new.values())
        before_path, before = service.records(original, target['target'])[0]
        assert before['status'] == 'out_of_memory'
        if (before_path.parent / 'worker/rows.json').exists():
            for old in service.read(before_path.parent / 'worker/rows.json'):
                if old['status'] != 'ok':
                    continue
                for key in ['extended_E', 'extended_fidelity', 'extended_makespan_us', 'baseline_E',
                            'candidate_evaluations', 'accepted_repairs', 'final_schedule_sha256']:
                    assert old[key] == new[old['variant']][key], (target['target'], old['variant'], key)
                partial_rows += 1
    original_summary = service.read(original / 'summary.json')
    assert original_summary['target_status_counts'] == {'ok': 42, 'out_of_memory': 24}
    value = {'passed': True, 'created_utc': service.now(),
        'study': str(study), 'expected_targets': 66, 'expected_rows': 528,
        'study_manifest_sha256': service.sha(study / 'manifest.json'),
        'execution_revision_manifest_sha256': service.sha(study / 'execution_optimization_v1/manifest.json'),
        'unchanged_memory_limit_bytes': 4 * 1024**3,
        'scientific_tests_passed': service.read(tests['scientific'])['tests'],
        'equivalent_result_rows': 24, 'equivalent_candidate_audits': 74,
        'original_oom_partial_rows_also_match': partial_rows,
        'stress_targets': stress['stress_targets'],
        'evidence_sha256': {str(p.relative_to(ROOT)): service.sha(p) for p in tests.values()},
        'original_v1_manifest_sha256': service.sha(original / 'manifest.json'),
        'original_v1_results_sha256': service.sha(original / 'results.csv'),
        'frozen_execution_files': revision['files'],
        'scope': 'Full rerun ready; all final campaign results still require completion and analysis'}
    service.write(reports / 'memory_repair_verification.json', value)
    print(value)


if __name__ == '__main__':
    main()
