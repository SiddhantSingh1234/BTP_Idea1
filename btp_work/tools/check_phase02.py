"""Evidence-aware Phase 02 gate; never marks a live dataset complete."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a fresh output under btp_work')
    tests=read('reports/phase_02/tests_05/result.json');checks={}
    checks['acceptance_tests']=tests['successful'] and tests['tests']>=14 and not tests['failures'] and not tests['errors']
    checks['tested_artifacts_unchanged']=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in tests['artifact_sha256'].items())
    checks['required_fixtures']=len(list((ROOT/'tests/fixtures/trace_v1').glob('*/expected.json')))>=25
    proofs=[read(f'reports/phase_02/full_circuit_{algorithm}_qft5_02/comparison.json') for algorithm in ['rft','dasatom']]
    checks['independent_original_circuit_checks']=all(p['equivalent_up_to_global_phase'] and p['full_original_circuit_checked'] and not p['physical_validity_implied'] for p in proofs)
    control=read('runs/phase_02/dasatom_corrected_vacancy_qft10_01/validation.json')
    checks['separate_corrected_control']=control['status']=='ok' and control['fully_validated_within_model'] and not control['source_physical_evidence_complete']
    checks['decision_and_handoff_present']=all((ROOT/p).exists() for p in ['reports/decisions/D002_TRACE_V1.md','reports/decisions/D003_PHASE02_SEMANTICS_AND_CONTROL.md','reports/phase_02/discrepancy_ledger.md','handoffs/phase_02.md'])
    plan=read('runs/current_baseline/study_v1/plan.json')
    checks['benchmark_worker_unchanged']=hashlib.sha256((ROOT/'tools/phase00_smoke.py').read_bytes()).hexdigest()==plan['worker_sha256']
    audit_path=ROOT/'reports/phase_02/live_audit_v2/live_status.json'
    audit=json.loads(audit_path.read_text()) if audit_path.exists() else None
    checks['available_audit_has_no_integrity_mismatches']=audit is not None and all(audit[k]==0 for k in ['adapter_errors','legacy_mismatches','mapping_mismatches','frozen_contract_mismatches'])
    full_audit=bool(audit and audit['job_accounting']['first_pass_dataset_audit_complete'])
    phase1_complete='| 01 | complete |' in (ROOT/'plan/STATUS.md').read_text(encoding='utf-8')
    engineering=all(checks.values())
    complete=engineering and full_audit and phase1_complete
    result={'phase':'02','status':'complete' if complete else ('blocked_dependency' if engineering else 'needs_revision'),
        'engineering_checks':checks,'engineering_checks_pass':engineering,
        'full_first_pass_audit_complete':full_audit,'phase_01_accepted_complete':phase1_complete,
        'phase_complete':complete,'audited_attempts_at_check':audit['audited_attempts'] if audit else None,
        'remaining':['Frozen Phase 01 dataset, final full audit and phase acceptance'] if engineering and not complete else [],
        'paper_revision_resolved':False,'original_native_measurements_changed':False}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
    return 0 if engineering else 1


if __name__=='__main__':raise SystemExit(main())
