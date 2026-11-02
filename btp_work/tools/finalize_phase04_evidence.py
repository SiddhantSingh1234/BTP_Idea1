"""NEW Phase04 final evidence: reuse unchanged compiled cases, replay current model.

No timing is fabricated: old compile samples retain their original paths/hashes.
Only the standalone vacancy counterexample is regenerated after its fixture fix.
"""
import argparse,copy,hashlib,importlib.util,json,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.trace.model import fingerprint
from implementation.movement_error.schedule import write_json_new
from implementation.movement_error.evaluator import evaluate
from implementation.movement_error.profiles import load_profile
from implementation.lookahead.fixtures import worse_horizon_example


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-pilot',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
 source=args.source_pilot.resolve();out=args.out.resolve()
 if not source.is_relative_to(ROOT) or not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use existing source/new output inside btp_work')
 t0=time.perf_counter();old=json.loads((source/'pilot_results.json').read_text());manifest=json.loads((source/'pilot_manifest.json').read_text())
 changed={name:{'compiled_sha256':h,'current_sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()} for name,h in old['artifact_sha256'].items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h}
 if set(changed)!={'implementation\\lookahead\\fixtures.py'} and set(changed)!={'implementation/lookahead/fixtures.py'}:raise ValueError('Only standalone fixture changes may reuse cached compiles: '+str(changed))
 spec=importlib.util.spec_from_file_location('_phase04_frozen_cases',ROOT/'tools/run_phase04_pilot.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 current_cases=module.cases()
 if fingerprint(current_cases)!=fingerprint(manifest['cases']):raise ValueError('A compiled case/input/layout/options changed; fresh compilation is required')
 out.mkdir(parents=True);replay=[]
 for row in old['rows']:
  cached=json.loads((ROOT/row['raw_result']).read_text());schedule=json.loads((ROOT/row['raw_schedule']).read_text());original=json.loads((ROOT/row['raw_result']).with_name('evaluation.json').read_text())
  fresh=evaluate(schedule,include_audit=False)
  if fresh['status']!='ok' or fresh['budget']!=original['budget']:raise AssertionError('Cached schedule does not replay identically')
  instructions=(ROOT/row['raw_result']).with_name('instructions.txt')
  if hashlib.sha256(instructions.read_bytes()).hexdigest()!=row['instructions_sha256']:raise AssertionError('Cached instruction integrity')
  record={'case':row['case'],'variant':row['variant'],'seed':row['seed'],'status':fresh['status'],'budget_identical':True,
          'cached_result':row['raw_result'],'cached_result_sha256':hashlib.sha256((ROOT/row['raw_result']).read_bytes()).hexdigest(),
          'schedule_sha256':hashlib.sha256((ROOT/row['raw_schedule']).read_bytes()).hexdigest(),'compiled_timing_reused_without_relabelling':True}
  replay.append(record)
 write_json_new(out/'cached_replay.json',{'records':replay,'all_identical':True,'fresh_compile_attempts':0,'source_cases_unchanged':True,'fixture_module_change':changed},ROOT)
 counter=worse_horizon_example(load_profile(ROOT/'configs/hardware/extended_no_cooling.json'));cs={}
 for h,item in counter.items():
  if item['result']['status']!='ok':raise AssertionError('Refined counterexample invalid')
  occupied={(0,0),(0,3),(4,1)}
  if tuple(item['chosen_site']) in occupied:raise AssertionError('Candidate is not vacant')
  write_json_new(out/'counterexample'/('h'+h)/'schedule.json',item['schedule'],ROOT);write_json_new(out/'counterexample'/('h'+h)/'result.json',item['result'],ROOT)
  cs[h]={'chosen_site':item['chosen_site'],'candidate_scores':item['candidate_scores'],'E':item['result']['budget']['total_E'],
         'makespan_us':item['result']['makespan_us'],'status':'ok','destination_initially_vacant':True}
 if cs['2']['E']<=cs['1']['E']:raise AssertionError('Expected nonmonotonic E example')
 write_json_new(out/'nonmonotonic_horizon.json',cs,ROOT)
 for name in ['pilot_results.csv','pilot_results.svg','pilot_results.png','legacy_compatibility.json']:shutil.copyfile(source/name,out/name)
 current_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((ROOT/'implementation/lookahead').glob('*.py'))+list((ROOT/'configs/variants').glob('lookahead.*.json'))+[ROOT/'tools/phase04_worker.py',ROOT/'tools/run_phase04_pilot.py',Path(__file__).resolve()]}
 result=copy.deepcopy(old);result.update(evidence_mode='cached_compiles_current_replay_refined_vacancy_fixture',source_compilation_pilot=str(source.relative_to(ROOT)),
     source_compilation_artifact_sha256=old['artifact_sha256'],artifact_sha256=current_hashes,fresh_compile_attempts=0,current_validation_replay_count=len(replay),
     source_compilation_pilot_wall_seconds=old['wall_seconds'],wall_seconds=time.perf_counter()-t0,
     timing_reuse_note='Original compile samples remain unchanged in referenced source records; wall_seconds here measures replay only.',
     prior_pilot_versions_preserved=True)
 final_manifest=copy.deepcopy(manifest);final_manifest.update(evidence_mode=result['evidence_mode'],source_compilation_pilot=result['source_compilation_pilot'],
   compiled_cases_reused=len(replay),fresh_compile_attempts=0,fixture_only_changes=changed,case_dictionary_hash_unchanged=True,
   note='First complete pilot retained as canonical compilation evidence, not selected by score/time. Later development pilot and all timing samples remain archived.')
 write_json_new(out/'pilot_manifest.json',final_manifest,ROOT);write_json_new(out/'pilot_results.json',result,ROOT)
 print(json.dumps({'replayed_schedules':len(replay),'all_budgets_identical':True,'fresh_compile_attempts':0,'new_counterexample':cs,'replay_seconds':result['wall_seconds']}))


if __name__=='__main__':main()