"""NEW Phase03 evidence gate; Phase01 dataset closure is explicitly separate."""
import argparse,hashlib,json,math,re,sys
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.movement_error.profiles import load_profile
from implementation.trace.model import fingerprint


def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def hashes_match(mapping):return all((ROOT/name).is_file() and hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in mapping.items())

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--finalize',action='store_true');args=parser.parse_args();out=args.out.resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a fresh gate output under btp_work')
 checks={};tests=read('reports/phase_03/tests_04/result.json');regression=read('reports/phase_03/phase02_regression_01/result.json');pilot=read('runs/phase_03/pilot_03/error_budget_pilot.json')
 checks['sixteen_model_groups_pass']=tests['successful'] and tests['tests']==16 and tests['errors']==0 and tests['failures']==0
 checks['tested_phase03_code_profiles_unchanged']=hashes_match(tests['artifact_sha256'])
 checks['fourteen_original_groups_pass']=regression['successful'] and regression['tests']==14 and regression['errors']==0 and regression['failures']==0
 checks['original_tested_artifacts_unchanged']=hashes_match(read('reports/phase_02/tests_05/result.json')['artifact_sha256']) and not tests['original_phase02_tested_artifacts_changed']
 checks['pilot_frozen_code_profiles_match']=hashes_match(pilot['code_and_profiles_sha256'])
 checks['pilot_cases_and_failures_retained']=pilot['rows']==56 and pilot['status_counts']=={'unsupported':41,'invalid':3,'ok':12}
 plan=read('runs/current_baseline/study_v1/plan.json')
 checks['live_native_worker_unchanged']=hashlib.sha256((ROOT/'tools/phase00_smoke.py').read_bytes()).hexdigest()==plan['worker_sha256']
 profiles=list((ROOT/'configs/hardware').glob('*.json'));resolved=[load_profile(path) for path in profiles]
 checks['seven_validated_profiles']=len(resolved)==7 and len({p['profile_id'] for p in resolved})==7
 rows=pilot['rows_data'];checks['no_missing_raw_records']=all((ROOT/r['raw_result']).exists() and (not r['raw_schedule'] or (ROOT/r['raw_schedule']).exists()) for r in rows)
 checks['source_decisions_preserved']=True;checks['frozen_rescores_unchanged']=True;checks['per_term_budgets_sum']=True
 for r in rows:
  if r['raw_schedule']:
   s=read(r['raw_schedule']);checks['source_decisions_preserved'] &= fingerprint(s['source_trace'])==s['source_trace_sha256']
   if s['operation']=='rescore':checks['frozen_rescores_unchanged'] &= s['events']==s['source_trace']['events']
  data=read(r['raw_result']);b=data.get('budget')
  if b and b['total_E'] is not None:checks['per_term_budgets_sum'] &= math.isclose(sum(b['terms'].values()),b['total_E'],rel_tol=1e-13,abs_tol=1e-14)
 cool=read('runs/phase_03/cli_cooling_01/result.json');cc=read('reports/phase_03/cli_cooling_check_01.json');ce=read('reports/phase_03/cli_cooling_evaluate_01.json')
 checks['cli_all_four_paths_pass']=all(r['status']=='ok' for r in [read('runs/phase_03/cli_rescore_01/result.json'),cool,cc,ce])
 checks['cooling_resource_and_population_proof']=cc['fully_validated_within_model'] and cc['cooling_episodes']==3 and cc['cooled_atom_events']==6 and cool['counts']['cooling_CZ']==12 and cool['counts']['cooling_H']==24 and cool['counts']['transfer_atom_events']==32 and cool['initial_spare_atom_population']==256
 checks['cooling_replay_identical']=ce['budget']==cool['budget']
 prediction=read('runs/phase_03/pilot_03/prediction_vs_replay.json');checks['prediction_boundary_demonstrated']=abs(prediction['prediction_error_E'])<1e-13 and prediction['omitted_suffix_error_E']>0
 manifest=read('source_review/manifest.json')
 checks['original_papers_unchanged']=all(hashlib.sha256((ROOT.parent/entry['source']).read_bytes()).hexdigest()==entry['sha256'] for entry in manifest)
 extra=read('source_review/phase03_additional/manifest.json')
 checks['additional_primary_pdf_integrity']=hashlib.sha256((ROOT/'source_review/phase03_additional/Bluvstein_2022_coherent_transport.pdf').read_bytes()).hexdigest()==extra['sha256']
 artifact=read('runs/phase_03/research/research_manifest.json')['artifact']
 checks['author_artifact_integrity']=hashlib.sha256((ROOT/artifact['archive']).read_bytes()).hexdigest()==artifact['sha256'] and all(hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256'] for entry in artifact['files'])
 copies=['error_budget_pilot.csv','error_budget_pilot.json','error_budget_pilot.svg','error_budget_pilot.png']
 checks['report_exports_match_raw']=all((ROOT/'reports/phase_03'/name).read_bytes()==(ROOT/'runs/phase_03/pilot_03'/name).read_bytes() for name in copies)
 required=['reports/phase_03/model_specification.md','reports/phase_03/source_research.md','reports/phase_03/error_budget_pilot.md','reports/phase_03/worked_budget.md','reports/phase_03/validation_report.md','reports/phase_03/change_ledger.md','handoffs/phase_03.md','reports/decisions/D004_PHASE03_MODEL_AND_DEPENDENCY.md','configs/schemas/schedule_phase03_v1.schema.json']
 checks['deliverables_present']=all((ROOT/name).exists() for name in required)
 # Only project documents are checked; archived third-party README links are not ours.
 docs=[ROOT/'README.md',ROOT/'source_review/SOURCE_REVIEW.md']
 for base in ['plan','handoffs','reports/phase_03','reports/decisions']:docs.extend((ROOT/base).rglob('*.md'))
 issues=[];link_count=0
 for doc in sorted(set(docs)):
  body=doc.read_text(encoding='utf-8')
  for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',body):
   target=match.group(1).strip().strip('<>')
   if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
   part=target.partition('#')[0];dest=(doc.parent/unquote(part)).resolve() if part else doc
   link_count+=1
   if not dest.exists():issues.append({'document':str(doc.relative_to(ROOT)),'missing_target':target})
 checks['project_document_links']=not issues
 status=(ROOT/'plan/STATUS.md').read_text(encoding='utf-8')
 checks['phase01_not_marked_complete']='| 01 | in_progress |' in status and '| 01 | complete |' not in status
 checks['phase02_user_acceptance_explicit']='| 02 | complete |' in status and 'D004' in status
 complete=all(checks.values())
 result={'phase':'03','status':'complete' if complete else 'needs_revision','complete_within_declared_analytical_scope':complete,
         'checks':checks,'document_link_issues':issues,'documents_checked':len(set(docs)),'local_links_checked':link_count,
         'phase01_complete_claimed':False,'phase02_engineering_user_accepted':True,'native_physical_performance_gain_claimed':False,
         'cooling_is_hypothetical_primitive_contract':True,'pilot_status_counts':pilot['status_counts'],
         'evidence':{'tests':'reports/phase_03/tests_04/result.json','regression':'reports/phase_03/phase02_regression_01/result.json','pilot':'runs/phase_03/pilot_03/error_budget_pilot.json'},'command':sys.argv}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 if complete and args.finalize:
  replacements={
   'README.md':[('Phase03 model/tests/pilot delivered; final evidence gate pending.','Phase03 model complete within its declared analytical scope; [final gate](reports/phase_03/gate_01.json) passes.')],
   'plan/STATUS.md':[('Phase03 model/tests/pilot delivered; final evidence gate pending.','Phase03 model complete within declared analytical scope; [final gate](../reports/phase_03/gate_01.json) passes.'),
                      ('| 03 | in_progress | Codex /root | Accepted02 foundation, D004 | Separate model/profiles;16 passing groups,14-group regression,56-row pilot; final evidence gate pending |','| 03 | complete | Codex /root | Accepted02 foundation, D004 | gate_01 passes:16 model groups,14 unchanged regression groups,56-row pilot; analytical/surrogate/primitive limits explicit; native physical coverage remains limited |')],
   'handoffs/phase_03.md':[('**Status: in_progress; final evidence gate pending.**','**Status: complete within the declared analytical model scope.** [Final gate](../reports/phase_03/gate_01.json) passes.')],
   'reports/phase_03/validation_report.md':[('Final evidence gate pending.','[Final evidence gate](gate_01.json) passes; Phase03 is complete within its declared analytical scope.')],
   'plan/phases/03_MOVEMENT_ERROR_MODEL.md':[('Final evidence gate pending.','[Final gate](../../reports/phase_03/gate_01.json) passes; Phase03 is complete within the declared analytical scope.')]
  }
  for name,pairs in replacements.items():
   path=ROOT/name;body=path.read_text(encoding='utf-8')
   for old,new in pairs:
    if old not in body:raise ValueError('Missing finalization anchor '+name)
    body=body.replace(old,new)
   path.write_text(body,encoding='utf-8',newline='\n')
  with (ROOT/'handoffs/phase_03.md').open('a',encoding='utf-8') as f:
   f.write('\nFinal tested acceptance command:\n\n```powershell\n& btp_work/.venv/Scripts/python.exe -B -X utf8 btp_work/tools/check_phase03.py --out btp_work/reports/phase_03/gate_01.json --finalize\n```\n\nAll final gate checks pass. Phase01 benchmark/dataset completion is not claimed.\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('checks','evidence')}))
 if not complete:print(json.dumps({'failed_checks':[k for k,v in checks.items() if not v]}))
 return 0 if complete else 1


if __name__=='__main__':raise SystemExit(main())