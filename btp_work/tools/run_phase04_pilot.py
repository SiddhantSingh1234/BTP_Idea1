"""NEW Phase04 fixed foreground pilot; short serial workers, no baseline controller."""
import argparse,copy,csv,hashlib,json,os,platform,statistics,subprocess,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.trace.model import read_cz_qasm,fingerprint,save_trace
from implementation.lookahead.integration import load_core
from implementation.lookahead.potential import load_options
from implementation.lookahead.fixtures import serialized_case,worse_horizon_example
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.schedule import write_json_new


def cases():
 baseline=json.loads((ROOT/'configs/baselines/rft_snapshot.json').read_text());core=load_core();out=[]
 geo={'rows':11,'columns':11,'r_int':2,'r_blk':4,'spacing_um':3.0}
 for case_id,run in [('qft5_ladder7','smoke_rft_qft5_01'),('tableII_ladder7','smoke_rft_tableII_01')]:
  path=ROOT/'runs/phase_00'/run/'normalized.qasm';_,schedule,n=core.analyze_qasm_file(str(path));circuit=read_cz_qasm(path)
  if n!=circuit['num_qubits']:raise AssertionError('Input register mismatch')
  out.append({'case_id':case_id,'schedule':schedule,'circuit':circuit,'layout':copy.deepcopy(baseline['layout']['frozen_slots']),
              'geometry':geo,'baseline_options':copy.deepcopy(baseline['options']),'input_path':str(path.relative_to(ROOT)),
              'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'input_kind':'frozen_normalized_benchmark','layout_policy':'frozen Phase00 six-slot11x11 layout'})
 fixture=json.loads((ROOT/'runs/phase_00/compiled_fixture_01/trace.json').read_text());path=ROOT/'benchmarks/phase_00/four_qubit_hand_trace.qasm'
 out.append({'case_id':'forced_eviction_ladder6','schedule':fixture['schedule'],'circuit':read_cz_qasm(path),'layout':fixture['physical_layout'],
             'geometry':{'rows':3,'columns':3,'r_int':1,'r_blk':2,'spacing_um':3.0},'baseline_options':fixture['options'],
             'input_path':str(path.relative_to(ROOT)),'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'input_kind':'existing_full_compiler_eviction_fixture','layout_policy':'frozen Phase00 fixture; ladder6 intentionally separate'})
 serial=serialized_case();serial.update(case_id='serialized_ladder7',baseline_options=copy.deepcopy(baseline['options']),
     input_path=None,input_sha256=fingerprint(serial['circuit']),input_kind='explicit_synthetic_serialization_fixture',layout_policy='one fixed slot to force same-layer sub-batches')
 out.append(serial);return out


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a new Phase04 pilot output directory')
 out.mkdir(parents=True);started=time.perf_counter();all_cases=cases();variants=['legacy_exact','next_events_h1','next_events_h2','next_events_h4','next_events_h8']
 configs={name:load_options(ROOT/'configs/variants'/('lookahead.'+name+'.json')) for name in variants}
 manifest={'schema':'lookahead_pilot.phase04.v1','phase':'04','cases':all_cases,'variants':configs,'development':'analytic/oracle fixtures only; no gamma tuning',
           'evaluation':'frozen QFT5/TableII plus declared eviction/serialization fixtures; a small pre-evaluation pilot, not Phase01 coverage',
           'routing_quality_seeds':[42,43],'layout_seed':42,'layout_seed_scope':'benchmark layout already frozen; no layout resampling',
           'timing_policy':'3 same-seed repeats at42;1 at43; never counted as independent quality samples',
           'gamma':.9,'weights':'uniform','assignment_future_bias':False,'workers':'serial foreground, below-normal priority,45s process timeout, one numerical thread',
           'geometry':'explicit identical two-trap-plane testing contract; not measured native geometry','physics_profile':'configs/hardware/extended_no_cooling.json',
           'phase01_controllers_invoked':False,'phase01_dataset_completion_claimed':False,'command':sys.argv,'python':sys.version,'platform':platform.platform()}
 write_json_new(out/'pilot_manifest.json',manifest,ROOT)
 rows=[];compat=[]
 env=dict(os.environ);env.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',QISKIT_PARALLEL='FALSE')
 tmp=out/'worker_tmp';tmp.mkdir();env['TEMP']=env['TMP']=str(tmp);env['XDG_CACHE_HOME']=str(out/'worker_cache')
 flags=(subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS) if sys.platform=='win32' else 0
 for case in all_cases:
  for seed in (42,43):
   for variant in variants:
    label=case['case_id']+'__'+variant+'__s'+str(seed);job=out/'raw'/label;job.mkdir(parents=True)
    req={'case':case,'config':configs[variant],'routing_seed':seed,'timing_repeats':3 if seed==42 else 1}
    request_path=job/'request.json';write_json_new(request_path,req,ROOT);worker=job/'worker';status=None;t0=time.perf_counter()
    with (job/'stdout.txt').open('w',encoding='utf-8') as stdout,(job/'stderr.txt').open('w',encoding='utf-8') as stderr:
     try:
      proc=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/phase04_worker.py'),'--request',str(request_path),'--out',str(worker)],
                           cwd=job,env=env,stdout=stdout,stderr=stderr,timeout=45,creationflags=flags)
      code=proc.returncode
     except subprocess.TimeoutExpired:
      code=None;status='timeout'
    if status=='timeout' or not (worker/'result.json').exists():
     row={'case':case['case_id'],'variant':variant,'seed':seed,'status':status or 'error','accepted_schedule':False,'E':None}
     write_json_new(job/'failure.json',{'status':row['status'],'exit_code':code,'wall_seconds':time.perf_counter()-t0,'censored':status=='timeout'},ROOT)
    else:
     result=json.loads((worker/'result.json').read_text());samples=result['timing_samples']
     row={'case':case['case_id'],'variant':variant,'seed':seed,'status':result['status'],'accepted_schedule':result['accepted_schedule'],
          'E':result['E'],'F_proxy':result['F_proxy'],'makespan_us':result['makespan_us'],'moved_atom_events':result['moved_atom_events'],
          'transfer_atom_events':result['transfer_atom_events'],'routing_batches':result['routing_batches'],'sum_atom_distance_um':result['sum_atom_distance_um'],
          'eviction_calls':result['statistics']['eviction_calls'],'parking_calls':result['statistics']['parking_calls'],
          'event_index_bytes':result['memory_diagnostic']['index_reachable_bytes'],
          'event_index_peak_allocation_bytes':result['memory_diagnostic']['index_build_tracemalloc_peak_bytes'],
          'query_peak_allocation_bytes':result['memory_diagnostic']['query_tracemalloc_peak_increment_bytes'],
          'event_index_build_seconds':result['statistics']['event_index_build_seconds'],'query_seconds_total':result['statistics']['query_seconds_total'],
          'query_count':result['statistics']['query_count'],'timing_sample_count':len(samples),
          'planner_median_seconds':statistics.median(s['planner_seconds'] for s in samples),
          'wrapper_median_seconds':statistics.median(s['compile_wrapper_seconds'] for s in samples),
          'direct_source_control_seconds':result['direct_source_control_seconds'],
          'legacy_schedule_equal':result['legacy_exact_schedule_equal'],'legacy_rng_equal':result['legacy_rng_after_equal'],
          'unchanged_pair_reoccurrences':result['unchanged_pair_reoccurrences'],'pair_reoccurrences':result['pair_reoccurrences'],
          'instructions_sha256':result['instructions_sha256'],'input_circuit_sha256':result['input_circuit_sha256'],'layout_sha256':result['layout_sha256'],
          'profile_sha256':result['profile_sha256'],'core_sha256':result['core_sha256'],
          'raw_result':str((worker/'result.json').relative_to(ROOT)),'raw_schedule':str((worker/'schedule.json').relative_to(ROOT)),
          'wall_seconds':time.perf_counter()-t0,'native_physical_validity_claimed':False}
     if variant=='legacy_exact':compat.append({'case':case['case_id'],'seed':seed,'schedule_equal':row['legacy_schedule_equal'],'rng_equal':row['legacy_rng_equal'],
                                               'input_circuit_sha256':row['input_circuit_sha256'],'raw_result':row['raw_result']})
    rows.append(row)
   print(json.dumps({'completed_case':case['case_id'],'seed':seed,'attempts':len(rows),'status_counts':dict(Counter(r['status'] for r in rows))}),flush=True)
   (out/'progress.json').write_text(json.dumps({'attempts_completed':len(rows),'planned':40,'phase01_controlled':False},indent=2)+'\n',encoding='utf-8')
 lookup={(r['case'],r['seed'],r['variant']):r for r in rows};h1_differences=[]
 for row in rows:
  legacy=lookup[(row['case'],row['seed'],'legacy_exact')];h1=lookup[(row['case'],row['seed'],'next_events_h1')]
  row['delta_E_vs_legacy']=row['E']-legacy['E'] if row.get('accepted_schedule') and legacy.get('accepted_schedule') else None
  row['delta_E_vs_generalized_h1']=row['E']-h1['E'] if row.get('accepted_schedule') and h1.get('accepted_schedule') else None
  if row['variant']=='next_events_h1':h1_differences.append({'case':row['case'],'seed':row['seed'],'schedule_equal_to_legacy':row.get('legacy_schedule_equal'),
    'delta_E':row['delta_E_vs_legacy'],'reason_scope':'Intentional pure-distance/anchor/cutoff/consumption/tie changes; never hidden as h>1 gain'})
 columns=sorted(set().union(*(set(r) for r in rows)))
 with (out/'pilot_results.csv').open('w',newline='',encoding='utf-8') as f:
  writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
 write_json_new(out/'legacy_compatibility.json',{'exact_controls':compat,'all_exact':len(compat)==8 and all(c['schedule_equal'] and c['rng_equal'] for c in compat),
                                                'generalized_h1_differences':h1_differences},ROOT)
 counter=worse_horizon_example(load_profile(ROOT/'configs/hardware/extended_no_cooling.json'));counter_summary={}
 for h,item in counter.items():
  dest=out/'counterexample'/('h'+h);write_json_new(dest/'schedule.json',item['schedule'],ROOT);write_json_new(dest/'result.json',item['result'],ROOT)
  counter_summary[h]={'chosen_site':item['chosen_site'],'candidate_scores':item['candidate_scores'],'E':item['result']['budget']['total_E'],
                      'makespan_us':item['result']['makespan_us'],'status':item['result']['status']}
 write_json_new(out/'nonmonotonic_horizon.json',counter_summary,ROOT)
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((ROOT/'implementation/lookahead').glob('*.py'))+list((ROOT/'configs/variants').glob('lookahead.*.json'))+[ROOT/'tools/phase04_worker.py',Path(__file__).resolve()]}
 summary={'schema':'lookahead_pilot_result.phase04.v1','attempts':len(rows),'status_counts':dict(Counter(r['status'] for r in rows)),
          'all_accepted':all(r.get('accepted_schedule',False) for r in rows),'legacy_controls_all_equal':len(compat)==8 and all(c['schedule_equal'] and c['rng_equal'] for c in compat),
          'generalized_h1_changed_schedules':sum(c['schedule_equal_to_legacy'] is False for c in h1_differences),
          'wall_seconds':time.perf_counter()-started,'artifact_sha256':hashes,'rows':rows,'phase01_results_modified':False}
 write_json_new(out/'pilot_results.json',summary,ROOT)
 os.environ['MPLCONFIGDIR']=str(out/'matplotlib_config')
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(10,4))
 for case in all_cases:
  selected=[lookup[(case['case_id'],42,v)] for v in variants]
  if all(r.get('accepted_schedule') for r in selected):
   axes[0].plot(range(5),[r['E'] for r in selected],marker='o',label=case['case_id'])
   axes[1].plot(range(5),[r['planner_median_seconds']*1000 for r in selected],marker='o',label=case['case_id'])
 for ax in axes:ax.set_xticks(range(5),['legacy','h1','h2','h4','h8']);ax.grid(alpha=.2)
 axes[0].set_ylabel('Negative log success proxy E');axes[1].set_ylabel('Planner median(ms),3 fixed-seed samples');axes[0].legend(fontsize=7)
 fig.suptitle('Phase04 fixed small pilot; identical declared testing geometry');fig.tight_layout();fig.savefig(out/'pilot_results.svg');fig.savefig(out/'pilot_results.png',dpi=150);plt.close(fig)
 print(json.dumps({k:v for k,v in summary.items() if k not in ('artifact_sha256','rows')}),flush=True)
 return 0 if summary['all_accepted'] and summary['legacy_controls_all_equal'] else 1


if __name__=='__main__':raise SystemExit(main())