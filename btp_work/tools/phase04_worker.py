"""NEW Phase04 short isolated compile/evaluation worker. Never invokes Phase01 controllers."""
import argparse,hashlib,json,os,sys,time,tracemalloc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.trace.model import save_trace,fingerprint
from implementation.lookahead.events import FutureEventIndex
from implementation.lookahead.integration import compile_schedule,direct_source_control,reachable_bytes
from implementation.lookahead.evaluation import evaluate_compilation
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.schedule import write_json_new


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--request',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
 out=args.out.resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a new Phase04 worker output under btp_work')
 request=json.loads(args.request.read_text(encoding='utf-8'));out.mkdir(parents=True);case=request['case'];seed=request['routing_seed'];cfg=request['config'];opts=case['baseline_options']
 repeats=request['timing_repeats']
 if type(repeats) is not int or not 1<=repeats<=3:raise ValueError('Short pilot worker supports1-3 timing repeats')
 t0=time.perf_counter();direct=direct_source_control(case['schedule'],case['circuit']['num_qubits'],case['layout'],case['geometry'],opts,routing_seed=seed)
 samples=[];first=None
 for repeat in range(repeats):
  start=time.perf_counter();c=compile_schedule(case['schedule'],case['circuit']['num_qubits'],case['layout'],case['geometry'],opts,cfg,circuit=case['circuit'],routing_seed=seed)
  elapsed=time.perf_counter()-start;digest=hashlib.sha256(c['instructions'].encode()).hexdigest()
  if first is None:first=c;first_hash=digest
  elif digest!=first_hash:raise AssertionError('Fixed-seed timing repeat changed decisions')
  samples.append({'repeat':repeat,'planner_seconds':c['planner_seconds'],'compile_wrapper_seconds':elapsed,
                  'event_index_build_seconds':c['statistics']['event_index_build_seconds'],'query_seconds_total':c['statistics']['query_seconds_total'],
                  'instructions_sha256':digest,'not_independent_quality_sample':True})
 start=time.perf_counter();evaluation=evaluate_compilation(first,case['circuit'],case['geometry'],load_profile(ROOT/'configs/hardware/extended_no_cooling.json'))
 scoring=time.perf_counter()-start
 # Separate memory diagnostic: never mix tracemalloc overhead into timing samples.
 tracemalloc.start();idx=FutureEventIndex(case['schedule'],case['circuit']['num_qubits'],case['circuit']);current,peak=tracemalloc.get_traced_memory();table_bytes=reachable_bytes(idx)
 tracemalloc.reset_peak();base=tracemalloc.get_traced_memory()[0];queries=0
 for layer in range(len(case['schedule'])):
  for q in range(case['circuit']['num_qubits']):idx.query(q,layer,cfg['h']);queries+=1
 after,query_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
 memory={'index_reachable_bytes':table_bytes,'index_build_tracemalloc_current_bytes':current,'index_build_tracemalloc_peak_bytes':peak,
         'query_tracemalloc_peak_increment_bytes':max(0,query_peak-base),'diagnostic_query_count':queries,
         'definition':'Python allocations/reachable graph in a separate diagnostic; excludes process RSS and imported native libraries'}
 legacy_equal=first['instructions']==direct['instructions'];rng_equal=first['random_state_after_sha256']==direct['random_state_after_sha256']
 if cfg['lookahead_policy']=='legacy_exact' and not (legacy_equal and rng_equal):raise AssertionError('Exact legacy compatibility failed')
 first['instructions_sha256']=first_hash
 (out/'instructions.txt').write_text(first['instructions'],encoding='utf-8',newline='\n')
 (out/'direct_control_instructions.txt').write_text(direct['instructions'],encoding='utf-8',newline='\n')
 write_json_new(out/'compilation.json',first,ROOT);save_trace(out/'trace',evaluation['trace'])
 write_json_new(out/'schedule.json',evaluation['schedule'],ROOT);write_json_new(out/'evaluation.json',evaluation['result'],ROOT)
 write_json_new(out/'validation.json',evaluation['source_validation'],ROOT);write_json_new(out/'metrics.json',evaluation['metrics'],ROOT)
 result={'schema':'lookahead_attempt.phase04.v1','case_id':case['case_id'],'variant':cfg['variant_id'],'routing_seed':seed,
         'status':evaluation['result']['status'],'accepted_schedule':evaluation['accepted_schedule'],
         'legacy_exact_schedule_equal':legacy_equal,'legacy_rng_after_equal':rng_equal,
         'direct_source_control_seconds':direct['planner_seconds'],'timing_samples':samples,'memory_diagnostic':memory,
         'statistics':first['statistics'],'instructions_sha256':first_hash,
         'input_circuit_sha256':fingerprint(case['circuit']),'layout_sha256':fingerprint(case['layout']),'request_sha256':hashlib.sha256(args.request.read_bytes()).hexdigest(),
         'profile_sha256':evaluation['result']['profile_sha256'],'core_sha256':first['core_sha256'],
         'E':(evaluation['result'].get('budget') or {}).get('total_E'),'F_proxy':(evaluation['result'].get('budget') or {}).get('fidelity_proxy'),
         'makespan_us':evaluation['result'].get('makespan_us'),'moved_atom_events':evaluation['metrics']['moved_atom_events'],
         'transfer_atom_events':evaluation['result'].get('counts',{}).get('transfer_atom_events',0),
         'routing_batches':evaluation['metrics']['routing_batches'],'sum_atom_distance_um':evaluation['metrics']['sum_atom_distance_um'],
         'unchanged_pair_reoccurrences':evaluation['unchanged_pair_reoccurrences'],'pair_reoccurrences':evaluation['pair_reoccurrences'],
         'validation_scoring_seconds':scoring,'worker_seconds_excluding_imports':time.perf_counter()-t0,
         'geometry_is_declared_testing_model':True,'native_physical_validity_claimed':False,'hash_seed':os.environ.get('PYTHONHASHSEED'),
         'threads':1,'python':sys.version}
 write_json_new(out/'result.json',result,ROOT);print(json.dumps({'case':case['case_id'],'variant':cfg['variant_id'],'seed':seed,'status':result['status'],'E':result['E']}))
 return 0 if result['accepted_schedule'] else 2


if __name__=='__main__':raise SystemExit(main())