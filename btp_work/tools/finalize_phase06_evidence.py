"""Independently reconstruct every Phase06 proposal and replay all final schedules."""
import argparse
from copy import deepcopy
import csv
import hashlib
import json
import platform
from pathlib import Path
import shutil
import statistics
import sys
import time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from implementation.assignment.costs import load_options as assignment_options
from implementation.assignment.integration import compile_schedule
from implementation.lookahead.potential import load_options as parking_options
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.evaluator import evaluate
from implementation.repair.replay import replay, plain
from implementation.repair.evaluation import bundle, total_E, prefix_invariant, local_objective
from implementation.repair.artifacts import write,write_bundle
from implementation.trace.model import fingerprint

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_bundle(path):
    path=Path(path);schedule=read(path/'schedule.json')
    return {'compilation':read(path/'compilation.json'),'evaluation':{'schedule':schedule,'result':read(path/'evaluation.json')},
            'recipe_sha256':read(path/'bundle.json')['recipe_sha256']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Use fresh output under btp_work')
    out.mkdir(parents=True);started=time.perf_counter()
    look=parking_options(ROOT/'configs/variants/lookahead.next_events_h4.json')
    profile=load_profile(ROOT/'configs/hardware/extended_no_cooling.json')
    checks=[];finals=[];accepted=[];traps=[];stragglers=[];conflicts=[];resources=[];raw_hashes={};replays=0;phase05_controls=0
    for split,source in [('development',ROOT/'runs/phase_06/development_01'),('evaluation',ROOT/'runs/phase_06/pilot_01')]:
        summary=read(source/'pilot_results.json')
        assert summary['all_accepted']
        for name,digest in summary['artifact_sha256'].items():assert sha(ROOT/name)==digest,name
        for recordpath in sorted((source/'raw').glob('*/attempt_*/attempt_record.json')):
            record=read(recordpath);assert record['status']=='ok'
            resources.append(record['peak_working_set_bytes'])
            for name,digest in record['worker_artifact_sha256'].items():
                assert sha(recordpath.parent/name)==digest,name
            raw_hashes[recordpath.relative_to(ROOT).as_posix()]=sha(recordpath)
        baseline_cache={}
        for row in summary['rows']:
            rawpath=ROOT/row['raw_result'];raw=read(rawpath)
            request=read(source/'requests'/(row['case']+'__s'+str(row['seed'])+'.json'))
            case=request['case'];cfg=assignment_options(ROOT/('configs/variants/assignment.'+row['preceding_assignment']+'.json'))
            basedir=rawpath.parent.parent/'baseline'
            baseline=load_bundle(basedir)
            if basedir not in baseline_cache:
                legacy=compile_schedule(case['schedule'],case['circuit']['num_qubits'],case['layout'],case['geometry'],
                    case['baseline_options'],look,cfg,profile,circuit=case['circuit'],routing_seed=row['seed'])
                assert legacy['instructions']==baseline['compilation']['instructions']
                assert legacy['random_state_after_sha256']==baseline['compilation']['random_state_after_sha256']
                phase05_controls+=1
                baseline_cache[basedir]=True
            final=load_bundle(raw['final_bundle_directory'])
            fresh=evaluate(final['evaluation']['schedule'],include_audit=False)
            assert fresh['status']=='ok' and fresh['valid_for_comparison']
            assert fresh['budget']==final['evaluation']['result']['budget']
            assert total_E(fresh)==row['E']
            assert row['E']<=row['baseline_E']+1e-12
            assert fingerprint(final['evaluation']['schedule'])==row['final_schedule_sha256']
            assert raw['baseline_input_unchanged'] and raw['caller_rng_restored']
            assert row['total_compile_validate_repair_seconds']==row['baseline_compile_validate_seconds']+row['repair_seconds']
            opts=raw['options'];assert raw['candidate_evaluations']<=opts['max_evaluations']
            assert len(raw['audit'])==raw['candidate_evaluations']
            assert raw['rounds']<=opts['max_rounds']
            assert sum(a['evaluation_seconds'] for a in raw['audit'])<=raw['repair_seconds']+1e-6
            if row['repair'] in ['disabled','zero']:
                assert row['original_schedule_sha256']==row['final_schedule_sha256']
                assert not raw['audit']
            parents={fingerprint(baseline['evaluation']['schedule']):baseline}
            for commit in raw['accepted_history']:
                value=load_bundle(commit['bundle_directory'])
                parents[commit['schedule_sha256']]=value
            for entry in raw['audit']:
                assert entry['incumbent_unchanged_after_trial'] and entry['caller_rng_restored_after_trial']
                parent=parents[entry['parent_schedule_sha256']]
                old=next(b for b in parent['compilation']['repair_boundaries'] if b['key']==entry['boundary_key'])
                try:
                    compiled=replay(case,look,cfg,profile,seed=row['seed'],overrides=entry['override_plan'],route_limit=opts['max_replay_route_calls'])
                    candidate=bundle(compiled,case,profile,baseline['recipe_sha256'])
                except Exception as exc:
                    assert entry.get('error',{}).get('type')==type(exc).__name__,entry
                    assert not entry['accepted']
                    checks.append({'split':split,'raw_result':row['raw_result'],'candidate_id':entry['candidate_id'],'expected_exception':type(exc).__name__})
                    continue
                # Disk JSON stores coordinate tuples as lists; compare the same
                # canonical representation, keeping exact hashes and all values.
                candidate['evaluation']['schedule']=plain(candidate['evaluation']['schedule'])
                replays+=1
                assert total_E(candidate['evaluation']['result'])==entry['actual_full_E']
                assert candidate['evaluation']['accepted_schedule']==entry['valid']
                assert fingerprint(candidate['evaluation']['schedule'])==entry['candidate_schedule_sha256']
                assert prefix_invariant(parent,candidate,old)['unchanged']==entry['prefix_unchanged']
                new=next(b for b in compiled['repair_boundaries'] if b['key']==old['key'])
                assert old['prefix_state']==new['prefix_state']
                local=local_objective(candidate,new)-local_objective(parent,old)
                assert abs(local-entry['local_E_delta'])<1e-12
                record={'split':split,'case':row['case'],'seed':row['seed'],'assignment':row['preceding_assignment'],
                    'budget':row['repair'],'raw_result':row['raw_result'],'candidate_id':entry['candidate_id'],
                    'accepted':entry['accepted'],'valid':entry['valid'],'prefix_unchanged':entry['prefix_unchanged'],
                    'before_E':entry['parent_full_E'],'after_E':entry['actual_full_E'],'local_E_delta':local,
                    'before_route':entry['before_route_metrics'],'after_route':entry['after_route_metrics'],
                    'proposal':entry['proposal'],'event_changes':entry['changed_events']}
                checks.append(record)
                if entry['accepted']:
                    assert entry['valid'] and entry['prefix_unchanged']
                    assert entry['actual_full_E']<entry['parent_full_E']-opts['improvement_tolerance_E']
                    accepted.append(record)
                    before=entry['before_route_metrics'];after=entry['after_route_metrics']
                    if max(after['largest_segment_um'].values(),default=0)<max(before['largest_segment_um'].values(),default=0) and after['move_time_us']<before['move_time_us']:
                        stragglers.append(record)
                    if after['actual_batches']<before['actual_batches'] and after['direct_conflict_edges']<before['direct_conflict_edges']:
                        conflicts.append(record)
                if entry.get('locally_better_globally_worse'):
                    assert not entry['accepted'] and local<0 and entry['actual_full_E']>entry['parent_full_E']
                    traps.append(record)
            finals.append({'split':split,**row})
        print(json.dumps({'audit_split':split,'finals':len(finals),'candidate_reconstructions':replays}),flush=True)
    assert accepted and traps and stragglers and conflicts
    # Save event-level before/after evidence, including an actual rejected local/global trap.
    examples={}
    for label,record in [('straggler',stragglers[0]),('conflict',conflicts[0]),('local_global_trap',traps[0])]:
        raw=read(ROOT/record['raw_result']);entry=next(a for a in raw['audit'] if a['candidate_id']==record['candidate_id'])
        paths=[Path(ROOT/record['raw_result']).parent.parent/'baseline']+[Path(c['bundle_directory']) for c in raw['accepted_history']]
        parent=next(load_bundle(path) for path in paths if fingerprint(read(path/'schedule.json'))==entry['parent_schedule_sha256'])
        source=ROOT/('runs/phase_06/development_01' if record['split']=='development' else 'runs/phase_06/pilot_01')
        case=read(source/'requests'/(record['case']+'__s'+str(record['seed'])+'.json'))['case']
        cfg=assignment_options(ROOT/('configs/variants/assignment.'+record['assignment']+'.json'))
        candidate=bundle(replay(case,look,cfg,profile,seed=record['seed'],overrides=entry['override_plan']),case,profile,parent['recipe_sha256'])
        before=parent['evaluation']['schedule']['events'];after=plain(candidate['evaluation']['schedule']['events'])
        event_diff=[{'index':i,'before':before[i] if i<len(before) else None,'after':after[i] if i<len(after) else None}
                    for i in range(max(len(before),len(after))) if i>=len(before) or i>=len(after) or before[i]!=after[i]]
        write(out/'examples'/label/'before_schedule.json',parent['evaluation']['schedule'])
        write(out/'examples'/label/'after_schedule.json',candidate['evaluation']['schedule'])
        write(out/'examples'/label/'evidence.json',{'record':record,'entry':entry,'event_diff':event_diff,
            'prefix_invariant':entry['prefix_evidence'],'rollback_kept_parent':not entry['accepted']})
        examples[label]=(out/'examples'/label/'evidence.json').relative_to(ROOT).as_posix()
    outcomes={}
    evaluation_rows=[r for r in finals if r['split']=='evaluation']
    for assignment in ['sum_distance','composite_bottleneck_expanded']:
        for budget in ['small','standard']:
            rows=[r for r in evaluation_rows if r['preceding_assignment']==assignment and r['repair']==budget]
            changes=[100*(r['E']/r['baseline_E']-1) for r in rows]
            outcomes[assignment+'/'+budget]={'compared':len(rows),'better':sum(r['delta_E']<-1e-12 for r in rows),
                'tie':sum(abs(r['delta_E'])<=1e-12 for r in rows),'worse':sum(r['delta_E']>1e-12 for r in rows),
                'mean_relative_E_change_percent':statistics.mean(changes),'maximum_relative_E_reduction_percent':-min(changes),
                'median_repair_seconds':statistics.median(r['repair_seconds'] for r in rows),
                'maximum_repair_seconds':max(r['repair_seconds'] for r in rows),
                'total_candidate_evaluations':sum(r['candidate_evaluations'] for r in rows),
                'accepted_repairs':sum(r['accepted_repairs'] for r in rows)}
    start=read(ROOT/'reports/phase_06/start_record.json')
    preserved={name:sha(ROOT/name)==digest for name,digest in start['frozen_artifact_sha256'].items()}
    assert all(preserved.values())
    write(out/'candidate_reconstruction.json',checks)
    raw_bytes=sum(p.stat().st_size for split in ['development_01','pilot_01'] for p in (ROOT/'runs/phase_06'/split).rglob('*') if p.is_file())
    audit={'status':'ok','final_schedules_replayed':len(finals),'candidate_evaluations_reconstructed':replays,
        'candidate_records':len(checks),'accepted_repairs':len(accepted),'local_global_traps_rejected':len(traps),
        'straggler_examples':len(stragglers),'conflict_batch_examples':len(conflicts),
        'phase05_exact_controls':phase05_controls,'frozen_files_checked':len(preserved),'all_frozen_files_identical':all(preserved.values()),
        'maximum_observed_process_family_peak_bytes':max(resources),'raw_bytes':raw_bytes,
        'outcomes':outcomes,'examples':examples,'attempt_record_sha256':raw_hashes,
        'independent_audit_seconds':time.perf_counter()-started,'audit_overhead_is_separate_from_measured_algorithm_cost':True,
        'source_sha256':sha(Path(__file__)),'command':sys.argv}
    write(out/'audit.json',audit)
    report=ROOT/'reports/phase_06'
    for name in ['pilot_results.csv','pilot_results.json','repair_audit.csv']:
        target=report/name
        if target.exists():raise FileExistsError(target)
        shutil.copyfile(ROOT/'runs/phase_06/pilot_01'/name,target)
    write(report/'runtime_environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
        'hardware_source':'../phase_05/runtime_environment.json','threads_per_worker':1,'routing_hash_seed_policy':'PYTHONHASHSEED=0 in isolated worker',
        'worker_wall_seconds':240,'process_family_memory_limit_bytes':4294967296,
        'peak_memory_definition':'observed sum of process-family peak working sets, not an allocation-proof hard cap'})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for ax,assignment in zip(axes,['sum_distance','composite_bottleneck_expanded']):
        for budget,marker in [('small','o'),('standard','s')]:
            rows=[r for r in evaluation_rows if r['preceding_assignment']==assignment and r['repair']==budget]
            ax.scatter([r['repair_seconds'] for r in rows],[100*(1-r['E']/r['baseline_E']) for r in rows],label=budget,marker=marker)
        ax.set_title(assignment.replace('_',' '));ax.set_xlabel('Complete repair work (seconds)');ax.set_ylabel('Full E reduction (%)');ax.axhline(0,color='grey',lw=.6);ax.legend()
    fig.savefig(report/'pilot_results.png',dpi=180);fig.savefig(report/'pilot_results.svg');plt.close(fig)
    print(json.dumps(audit));return 0
if __name__=='__main__':raise SystemExit(main())
