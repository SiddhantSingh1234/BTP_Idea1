"""NEW Phase03 fixed small pilot. Reads frozen sources; never runs a compiler."""
import argparse,copy,csv,hashlib,json,math,os,platform,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'));sys.dont_write_bytecode=True
from implementation.adapters.upstream import adapt_run
from implementation.trace.model import load_trace,save_trace,fingerprint
from implementation.metrics.legacy import measure_trace
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.schedule import make_schedule,write_json_new,UnsupportedSchedule
from implementation.movement_error.evaluator import evaluate
from implementation.movement_error.physics import local_batch_cost,TERMS
from phase_03_acceptance import route_fixture


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a fresh pilot output directory under btp_work')
    out.mkdir(parents=True);raw=out/'raw';raw.mkdir()
    profiles={name:load_profile(ROOT/'configs/hardware'/(name+'.json')) for name in ('legacy_rft','frozen_ideal','transfer_only','linear_surrogate','extended_no_cooling','extended_registered_cooling','zap_triangular_surrogate')}
    sources={};records=[];rows=[];started=time.perf_counter()
    for key,algorithm,run in [('qft5_rft','rft','smoke_rft_qft5_01'),('qft5_dasatom','dasatom','smoke_dasatom_qft5_01'),
                              ('tableII_rft','rft','smoke_rft_tableII_01'),('tableII_dasatom','dasatom','smoke_dasatom_tableII_03')]:
        path=ROOT/'runs/phase_00'/run
        sources[key]=adapt_run(path,algorithm,timing='two_transfer_stages')
        records.append({'case':key,'algorithm':algorithm,'source_run':str(path.relative_to(ROOT)),
                        'worker_result_sha256':hashlib.sha256((path/'result.json').read_bytes()).hexdigest(),
                        'frozen_policy':'Phase02 two_transfer_stages; derived times/traps, never observed native physical timing'})
    sources['qft10_dasatom_corrected']=load_trace(ROOT/'runs/phase_02/dasatom_corrected_vacancy_qft10_01/trace')
    records.append({'case':'qft10_dasatom_corrected','algorithm':'dasatom_corrected_vacancy_v1','source_trace':'runs/phase_02/dasatom_corrected_vacancy_qft10_01/trace',
                    'not_native_algorithm_output':True,'original_native_invalid_retained':True})
    sources['synthetic_heating']=route_fixture(5)
    records.append({'case':'synthetic_heating','algorithm':'fixed_synthetic_route','purpose':'Exercise cooling and loss; not a compiled benchmark; 2 atoms,5 parallel15um batches'})
    for key,trace in sources.items():save_trace(raw/'sources'/key,trace)
    write_json_new(out/'pilot_manifest.json',{'phase':'03','predeclared_cases':records,'profile_ids':list(profiles),
        'scope':'Normalized CZ skeleton; conditional native diagnostics; corrected/synthetic tracks separate',
        'no_weight_tuning':True,'no_compilers_executed':True,'phase01_completion_claimed':False,
        'python':sys.version,'platform':platform.platform(),'command':sys.argv},ROOT)
    def run(case,p,operation,label):
        destination=raw/'evaluations'/case/label
        before=fingerprint(sources[case]);t0=time.perf_counter()
        try:
            s=make_schedule(sources[case],p,operation);t1=time.perf_counter();r=evaluate(s)
        except UnsupportedSchedule as exc:
            r={'status':'unsupported','reason':str(exc),'budget':None};s=None;t1=time.perf_counter()
        if before!=fingerprint(sources[case]):raise AssertionError('Source mutated')
        if s is not None:write_json_new(destination/'schedule.json',s,ROOT)
        write_json_new(destination/'result.json',r,ROOT)
        b=r.get('budget') or {};terms=b.get('terms') or {}
        row={'case':case,'variant':label,'operation':operation,'profile_id':p['profile_id'],'profile_sha256':fingerprint(p),
             'status':r['status'],'valid_for_comparison':r.get('valid_for_comparison',False),
             'source_trace_sha256':before,'source_status':r.get('validation',{}).get('source_validation',{}).get('status'),
             'original_native_status':sources[case]['metadata'].get('origin',{}).get('upstream_status'),
             'num_qubits':sources[case]['metadata']['circuit']['num_qubits'],'CZ':len(sources[case]['metadata']['circuit']['gates']),
             'circuit_sha256':sources[case]['metadata']['circuit_sha256'],'makespan_us':r.get('makespan_us'),
             **{key:terms.get(key) for key in TERMS},'total_E':b.get('total_E'),'total_E_infinite':b.get('total_E_infinite'),
             'F_proxy':b.get('fidelity_proxy'),'underflow':b.get('fidelity_underflow'),
             'legacy_source_E':r.get('historical_source_score',{}).get('negative_log_fidelity'),
             'cooled_atom_events':r.get('counts',{}).get('cooled_atom_events',0),'cooling_episodes':r.get('counts',{}).get('cooling_episodes',0),
             'transfer_atom_events':r.get('counts',{}).get('transfer_atom_events'),
             'initial_spare_atom_population':r.get('initial_spare_atom_population',0),'surrogate':r.get('surrogate_heating',False),
             'transform_seconds':t1-t0,'validation_scoring_seconds':time.perf_counter()-t1,
             'raw_result':str((destination/'result.json').relative_to(ROOT)),'raw_schedule':str((destination/'schedule.json').relative_to(ROOT)) if s else None}
        rows.append(row);return r
    for case in sources:
        for name,operation in [('legacy_rft','rescore'),('frozen_ideal','rescore'),('transfer_only','rescore'),('linear_surrogate','rescore'),
                                ('extended_no_cooling','retime'),('extended_registered_cooling','retime_and_cool'),('zap_triangular_surrogate','retime')]:
            p=copy.deepcopy(profiles[name])
            if case=='synthetic_heating':p['movement']['acceleration_um_per_us2']=.05;p['heating']['initial_n']=3
            run(case,p,operation,name)
    # Fixed sensitivity grid, no data-driven parameter selection.
    for frequency in (40,80):
        for multiplier in (.5,1,2):
            p=copy.deepcopy(profiles['extended_no_cooling']);p['heating'].update(cyclic_frequency_khz=frequency,multiplier=multiplier)
            run('qft5_rft',p,'retime',f'sensitivity_f{frequency}_heat{multiplier}')
    for acceleration in (.0005,.002,2.75):
        p=copy.deepcopy(profiles['extended_no_cooling']);p['movement']['acceleration_um_per_us2']=acceleration
        run('qft5_rft',p,'retime',f'sensitivity_acceleration_{acceleration}')
    for fidelity in (1,.9932):
        p=copy.deepcopy(profiles['extended_no_cooling']);p['noise']['f_transfer']=fidelity
        run('qft5_rft',p,'retime',f'sensitivity_transfer_{fidelity}')
    p=copy.deepcopy(profiles['extended_no_cooling']);p['exposure']['T2_us']=15e6
    run('qft5_rft',p,'retime','sensitivity_effective_coherence_15s')
    for threshold in (12,25):
        p=copy.deepcopy(profiles['extended_registered_cooling']);p['movement']['acceleration_um_per_us2']=.05;p['heating']['initial_n']=3;p['cooling']['threshold_n']=threshold
        run('synthetic_heating',p,'retime_and_cool',f'sensitivity_cooling_threshold_{threshold}')
    with (out/'error_budget_pilot.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    # Honest conditional rank table: unsupported native rows never become physical rankings.
    rank=[]
    for variant in ('legacy_rft','frozen_ideal','transfer_only','linear_surrogate','extended_no_cooling','extended_registered_cooling','zap_triangular_surrogate'):
        pair=[r for r in rows if r['case'] in ('qft5_rft','qft5_dasatom') and r['variant']==variant]
        if all(r['total_E'] is not None and r['status']!='invalid' for r in pair):
            ordered=sorted(pair,key=lambda x:x['total_E']);rank.append({'variant':variant,'conditional_order':[r['case'] for r in ordered],
            'E':[r['total_E'] for r in ordered],'accepted_physical_comparison':all(r['valid_for_comparison'] for r in pair),
            'limitation':'Native logs omit physical evidence; conditional analytical route-skeleton diagnostic only'})
        else:rank.append({'variant':variant,'conditional_order':None,'accepted_physical_comparison':False,'limitation':'Invalid/undefined model factor; no ranking'})
    write_json_new(out/'rankings.json',rank,ROOT)
    # Prediction and full suffix replay with one extra gate demonstrate the API boundary.
    p=copy.deepcopy(profiles['extended_no_cooling']);p['heating']['initial_n']=3
    pred=local_batch_cost({0:3,1:3},{0:15,1:15},p,next_cz_pairs=[(0,1)])
    one=make_schedule(route_fixture(1),p,'retime');actual=evaluate(one)
    base=-math.log(.995)-math.log1p(-p['heating']['lambda']*.005*6)+2*.2/1.5e6
    extra=copy.deepcopy(route_fixture(1));g=copy.deepcopy(extra['events'][-1]);g['gate_id']='g000001';g['dependencies']=['g000000'];g['event_id']='suffix_extra';g['gate_batch']='suffix_extra';g['start_us']+=g['duration_us'];extra['events'].append(g)
    circ=copy.deepcopy(extra['metadata']['circuit']);new=copy.deepcopy(circ['gates'][0]);new.update(gate_id='g000001',dependencies=['g000000'],logical_layer=2);circ['gates'].append(new);extra['metadata']['circuit']=circ;extra['metadata']['circuit_sha256']=fingerprint(circ);extra['metadata']['source_counts']['gate_stages']=2
    suffix=evaluate(make_schedule(extra,p,'retime'));base2=2*base
    comparison={'prediction':pred,'one_next_gate_replay_delta_E':actual['budget']['total_E']-base,
                'prediction_error_E':pred['total_E']-(actual['budget']['total_E']-base),
                'two_next_gate_replay_delta_E':suffix['budget']['total_E']-base2,
                'omitted_suffix_error_E':suffix['budget']['total_E']-base2-pred['total_E'],
                'interpretation':'Prediction is local; an omitted future CZ adds heating-dependent error. Use full replay to accept repairs.'}
    write_json_new(out/'prediction_vs_replay.json',comparison,ROOT)
    # Exportable scientific budget figure for the declared synthetic resource tracks.
    os.environ['MPLCONFIGDIR']=str(out/'matplotlib_config')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    selected=[r for r in rows if r['case']=='synthetic_heating' and r['variant'] in ('extended_no_cooling','extended_registered_cooling')]
    fig,ax=plt.subplots(figsize=(8,4));bottom=[0.,0.]
    for term in TERMS:
        values=[r[term] or 0 for r in selected];ax.bar(['No cooling','Explicit extra cooling hardware'],values,bottom=bottom,label=term.removeprefix('E_'))
        bottom=[a+b for a,b in zip(bottom,values)]
    ax.set_ylabel('Negative log success proxy E');ax.set_title('Fixed high-heating synthetic route; different hardware tracks');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'error_budget_pilot.png',dpi=160);fig.savefig(out/'error_budget_pilot.svg');plt.close(fig)
    files=list((ROOT/'implementation/movement_error').glob('*.py'))+list((ROOT/'configs/hardware').glob('*.json'))+[Path(__file__).resolve()]
    summary={'rows':len(rows),'status_counts':dict(__import__('collections').Counter(r['status'] for r in rows)),
             'wall_seconds':time.perf_counter()-started,'code_and_profiles_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
             'rankings':rank,'all_original_native_invalid_statuses_retained':True,'phase01_completion_claimed':False,'rows_data':rows}
    write_json_new(out/'error_budget_pilot.json',summary,ROOT)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('rows_data','rankings','code_and_profiles_sha256')}))


if __name__=='__main__':main()