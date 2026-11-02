"""Phase05 final evidence gate: engineering/pilot scope, not a universal gain."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashes(mapping):
    return all((ROOT / name).is_file() and sha(ROOT / name) == value for name, value in mapping.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use a fresh output under btp_work')
    checks = {}
    checks['accepted_phase03'] = read('reports/phase_03/gate_01.json')['status'] == 'complete'
    checks['accepted_phase04'] = read('reports/phase_04/gate_benchmark_setup_01.json')['status'] == 'complete'
    tests = read('reports/phase_05/tests_03/result.json')
    checks['seventeen_new_groups_pass'] = tests['successful'] and tests['tests'] == 17 and tests['errors'] == tests['failures'] == 0
    checks['current_tested_code_configs_identical'] = hashes(tests['artifact_sha256'])
    previous = read('reports/phase_05/phase04_regression_start_01/result.json')
    checks['unchanged_seventeen_phase04_groups'] = previous['successful'] and previous['tests'] == 17 and hashes(previous['artifact_sha256'])
    checks['all_starting_scientific_sources_unchanged'] = hashes(read('reports/phase_05/start_record.json')['frozen_artifact_sha256'])
    frozen = True
    for name in ['phase01_frozen_baseline_v1', 'phase03_matched_benchmark_v1', 'phase04_matched_benchmark_v1']:
        study = ROOT / 'runs' / name
        manifest = json.loads((study / 'manifest.json').read_text(encoding='utf-8'))
        frozen &= sha(study / 'manifest.json') == (study / 'manifest.sha256').read_text().strip()
        frozen &= all(sha(study / name) == expected for name, expected in manifest['files'].items())
    checks['original_frozen_benchmark_studies_intact'] = frozen
    protocol = read('configs/studies/phase05_pilot_v1.json')
    checks['fixed_thirteen_assignment_configs'] = len(protocol['configuration_sha256']) == 13 and hashes(protocol['configuration_sha256'])
    checks['fixed_development_evaluation_split'] = (len(protocol['development_cases']) == 4 and len(protocol['evaluation_cases']) == 11
        and not set(protocol['development_cases']) & set(protocol['evaluation_cases']) and protocol['weights_tuned'] is False)
    development = read('runs/phase_05/development_01/pilot_results.json')
    pilot = read('runs/phase_05/pilot_01/pilot_results.json')
    checks['fiftysix_development_schedules_valid'] = development['attempts'] == 56 and development['status_counts'] == {'ok': 56} and development['all_accepted']
    checks['threehundredeight_evaluation_schedules_valid'] = pilot['attempts'] == 308 and pilot['status_counts'] == {'ok': 308} and pilot['all_accepted']
    checks['compilation_artifacts_match_current_code'] = hashes(development['artifact_sha256']) and hashes(pilot['artifact_sha256'])
    checks['timing_repeats_not_quality_seeds'] = development['timing_samples'] == 112 and pilot['timing_samples'] == 462 and all(
        sample['not_independent_quality_sample'] for result in [development, pilot] for row in result['rows'] for sample in row['timing_samples'])
    checks['all_prefix_heating_matches_common_evaluator'] = all(row['prefix_heating_matches_full_evaluator'] for result in [development, pilot] for row in result['rows'])
    manifests = [read('runs/phase_05/' + folder + '/manifest.json') for folder in ['development_01', 'pilot_01']]
    checks['actual_case_identities_match_protocol'] = all(manifest['input_hashes'] == protocol[manifest['split'] + '_cases'] for manifest in manifests)
    audit = read('runs/phase_05/audit_01/audit.json')
    checks['all_364_schedules_replayed_identically'] = audit['status'] == 'ok' and audit['replayed_schedules'] == 364 and audit['all_budgets_identical'] and len(audit['records']) == 364
    checks['actual_matrix_independent_optima'] = audit['actual_matrix_optima_checked'] == 2496
    checks['all_applied_orientations_audited'] = audit['applied_orientations_checked'] == 4405
    checks['new_new_proxy_limitation_measured'] = audit['batches_with_unmodeled_new_new_conflicts'] == 824
    checks['historical_legacy_phase04_controls_match'] = len(audit['historical_exact_controls']) == 16 and all(item['exact_instructions'] for item in audit['historical_exact_controls'])
    checks['audit_does_not_relabel_new_compilation'] = audit['fresh_compile_attempts'] == 0
    checks['replayed_schedule_compilation_integrity'] = all(
        sha(ROOT / item['raw_directory'] / 'schedule.json') == item['schedule_sha256']
        and sha(ROOT / item['raw_directory'] / 'compilation.json') == item['compilation_sha256'] for item in audit['records'])
    integrity = hashes(audit['worker_attempt_sha256'])
    for name in audit['worker_attempt_sha256']:
        path = ROOT / name
        record = json.loads(path.read_text(encoding='utf-8'))
        integrity &= all(sha(path.parent / name) == expected for name, expected in record['worker_artifact_sha256'].items())
    checks['all_raw_worker_artifacts_intact'] = integrity
    comparisons = {(item['variant'], item['control']): item for item in audit['comparisons']}
    same = comparisons['composite_bottleneck_expanded', 'sum_distance_expanded']
    old = comparisons['composite_bottleneck_expanded', 'sum_distance']
    checks['matched_candidate_positive_and_negative_results'] = (
        (same['better'], same['tie'], same['worse']) == (10, 8, 4) and (old['better'], old['tie'], old['worse']) == (6, 8, 8))
    checks['no_best_default_or_general_gain_promoted'] = pilot['best_variant_selected'] is False and audit['best_default_selected'] is False
    proofs = [read('reports/phase_05/full_original_' + name + '_01/comparison.json') for name in ['corrected', 'composite']]
    checks['two_full_original_qft5_semantic_proofs'] = all(p['equivalent_up_to_global_phase'] and p['full_original_circuit_checked']
        and p['basis_states'] == 32 and p['maximum_absolute_error'] < 1e-9 and not p['physical_validity_implied'] for p in proofs)
    sources = read('source_review/phase05_primary/manifest.json')
    checks['three_additional_primary_pdfs_and_texts_archived'] = len(sources) == 3 and all(sha(ROOT / item['path']) == item['sha256'] and (ROOT / item['extracted']).is_file() for item in sources)
    checks['original_supplied_papers_proposal_unchanged'] = all(sha(ROOT.parent / item['source']) == item['sha256'] for item in read('source_review/manifest.json'))
    checks['report_exports_match_original_measurements'] = all((ROOT / 'reports/phase_05' / name).read_bytes() == (ROOT / 'runs/phase_05/pilot_01' / name).read_bytes() for name in ['pilot_results.csv', 'pilot_results.json'])
    required = ['reports/phase_05/assignment_spec.md', 'reports/phase_05/source_research.md', 'reports/phase_05/pilot_results.md',
        'reports/phase_05/validation_report.md', 'reports/phase_05/change_ledger.md', 'reports/phase_05/pilot_results.png',
        'reports/phase_05/pilot_results.svg', 'source_review/phase05_primary/README.md', 'source_review/phase05_primary/references.bib',
        'reports/decisions/D008_PHASE05_ORIENTED_ASSIGNMENT.md', 'handoffs/phase_05.md', 'reports/phase_05/runtime_environment.json']
    checks['all_required_deliverables_present'] = all((ROOT / name).is_file() for name in required)
    checks['measured_rectangular_dimensions_and_resources'] = audit['maximum_real_rows'] == 4 and audit['maximum_candidate_columns'] == 6 and audit['maximum_observed_process_family_peak_bytes'] > 0
    docs = [ROOT / 'README.md']
    for name in ['plan', 'handoffs', 'reports/decisions', 'reports/phase_05', 'source_review/phase05_primary']:
        docs.extend((ROOT / name).rglob('*.md'))
    issues = []
    links = 0
    for doc in docs:
        for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', doc.read_text(encoding='utf-8')):
            target = match[1].strip().strip('<>')
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            path = target.partition('#')[0]
            dest = (doc.parent / unquote(path)).resolve() if path else doc
            links += 1
            if not dest.exists() and dest != out:
                issues.append({'document': str(doc.relative_to(ROOT)), 'missing': target})
    checks['all_document_links_resolve'] = not issues
    result = {'phase': '05', 'status': 'complete' if all(checks.values()) else 'needs_revision',
        'accepted_scope': 'oriented assignment implementation and fixed small analytical pilot',
        'checks': checks, 'documents_checked': len(docs), 'local_links_checked': links, 'link_issues': issues,
        'evaluation_schedules': 308, 'development_schedules': 56, 'best_default_selected': False,
        'general_performance_improvement_claimed': False, 'baseline_controllers_modified_or_restarted': False,
        'artifact_sha256': {name: sha(ROOT / name) for name in ['tools/check_phase05.py', 'tools/finalize_phase05_evidence.py']},
        'command': sys.argv}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'passed': sum(checks.values()), 'total': len(checks),
        'failed': [name for name, value in checks.items() if not value], 'link_issues': issues}))
    return 0 if result['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
