"""NEW Phase 03 event-time error accounting; historical scorer is imported unchanged."""
from collections import Counter
import math
from implementation.metrics.legacy import measure_trace
from implementation.trace.model import fingerprint
from implementation.movement_error.checker import validate_schedule
from implementation.movement_error.physics import (zero_budget, neglog_fidelity, heating_increment,
    movement_loss_cost, heating_gate_cost, angular_frequency)


def finite(value):
    return value if math.isfinite(value) else None


def budget_json(terms):
    total=sum(terms.values());f=math.exp(-total)
    return {'terms':{k:finite(v) for k,v in terms.items()},'terms_infinite':{k:math.isinf(v) for k,v in terms.items()},
            'total_E':finite(total),'total_E_infinite':math.isinf(total),'fidelity_proxy':f,
            'fidelity_underflow':f==0.0 and math.isfinite(total)}


def evaluate(schedule, *, include_audit=True):
    check=validate_schedule(schedule);p=schedule['profile'];source=schedule['source_trace'];events=schedule['events']
    legacy=measure_trace(source)['legacy']
    result={'schema_version':'movement_error_result.phase03.v1','phase':'03','operation':schedule['operation'],
            'schedule_sha256':fingerprint(schedule),'source_trace_sha256':schedule['source_trace_sha256'],
            'profile_sha256':schedule['profile_sha256'],'profile_id':p['profile_id'],
            'computation_scope':p['computation_scope'],'historical_source_score':legacy,
            'validation':check,'status':check['status'],'valid_for_comparison':False,
            'assumptions':schedule['assumptions']+p['assumptions'],'budget':None}
    if p['scorer']=='legacy':
        b=zero_budget();hw=source['metadata']['hardware'];G=legacy['scored_CZ'];B=legacy['four_per_block_transfer_alias']
        if G:b['E_native_gate']=G*neglog_fidelity(hw['legacy_f_cz'])
        if B:b['E_transfer']=B*neglog_fidelity(hw['legacy_f_transfer'])
        b['E_decoherence']=legacy['idle_proxy_us']/hw['legacy_T2_us']
        result.update(budget=budget_json(b),historical_accounting_only=True,
                      legacy_profile_parameters_from_frozen_source=True)
        return result
    if any(e.get('start_us') is None or e.get('duration_us') is None for e in events):
        result['unavailable_reason']='Untimed evidence requires an explicitly labelled schedule reconstruction'
        return result
    fatal_codes={'malformed_schedule','malformed_event','malformed_physical_replay','logical_overlap','physical_atom_overlap'}
    if any(v['code'] in fatal_codes for v in check['violations']):
        result['unavailable_reason']='Malformed or overlapping operations do not define a unique event-time state'
        return result
    init=next(e for e in events if e['kind']=='initialize');qs=init['logical_qubit_ids'];h=p['heating'];noise=p['noise'];ex=p['exposure']
    n={a:h.get('initial_n_by_qubit',{}).get(str(q),h['initial_n']) for a,q in zip(init['atom_ids'],qs)}
    carrier=dict(zip(qs,init['atom_ids']));terms=zero_budget();count=Counter();audit=[];warnings=[]
    cooling_transfer_E=0.0;cooling_heating_E=0.0
    start=init['start_us'];end=max((e['start_us']+e['duration_us'] for e in events),default=start);span=end-start
    if span<0:raise ValueError('Negative execution span')
    exposure={q:span*ex['rates']['stationary'] for q in qs}
    exposure_by_mode={q:dict.fromkeys(ex['rates'],0.0) for q in qs}
    for q in qs:exposure_by_mode[q]['stationary']=span
    intervals={q:[] for q in qs}
    for e in events:
        if e['kind']=='initialize':continue
        mode=e['kind'] if e['kind'] in ex['rates'] else 'stationary'
        for q in e['logical_qubit_ids']:
            if q not in exposure:continue
            dt=e['duration_us'];exposure[q]+=dt*(ex['rates'][mode]-ex['rates']['stationary'])
            if mode!='stationary':
                exposure_by_mode[q]['stationary']-=dt;exposure_by_mode[q][mode]+=dt
            intervals[q].append({'start_us':e['start_us'],'end_us':e['start_us']+dt,'mode':mode,'event_id':e['event_id']})
    per_qubit={str(q):{'T2_us':ex['T2_by_qubit_us'].get(str(q),ex['T2_us']),
                        'weighted_exposure_us':exposure[q], 'mode_durations_us':exposure_by_mode[q],
                        'E_decoherence':exposure[q]/ex['T2_by_qubit_us'].get(str(q),ex['T2_us'])} for q in qs}
    terms['E_decoherence']=sum(item['E_decoherence'] for item in per_qubit.values())
    boundaries=[]
    for i,e in enumerate(events):
        if e['kind']=='initialize':continue
        boundaries.append((e['start_us'],1,i));boundaries.append((e['start_us']+e['duration_us'],2 if e['duration_us']==0 else 0,i))
    spacing=source['metadata']['hardware']['spacing_um']
    try:
        for time,boundary,i in sorted(boundaries):
            e=events[i];kind=e['kind'];atoms=e['atom_ids'];delta=zero_budget();before={a:n[a] for a in atoms}
            if boundary==1:
                if kind=='gate':
                    count['native_CZ']+=1;delta['E_native_gate']=neglog_fidelity(noise['f_cz'])
                    delta['E_heating_gate']=heating_gate_cost(sum(n[a] for a in atoms),p)
                elif kind=='transfer':
                    count['transfer_atom_events']+=len(atoms);count['transfer_stages']+=1
                    delta['E_transfer']=len(atoms)*neglog_fidelity(noise['f_transfer']) if atoms else 0.0
                elif kind=='cooling':
                    cold=e['cold_atom_ids'];population=len(atoms);count['cooling_episodes']+=1;count['cooled_atom_events']+=population
                    count['cooling_CZ']+=2*population;count['cooling_H']+=4*population
                    delta['E_cooling_gate']=2*population*neglog_fidelity(noise['f_cz'])+4*population*neglog_fidelity(noise['f_h'])
                    for old,new in zip(atoms,cold):
                        n[new]=p['cooling']['cold_n']
                        delta['E_heating_gate']+=2*heating_gate_cost(n[old]+n[new],p)
                    delta['E_transfer']=2*population*neglog_fidelity(noise['f_transfer'])
                    count['transfer_atom_events']+=2*population;count['transfer_stages']+=2
                    count['cooling_transfer_atom_events']+=2*population;count['cooling_transfer_stages']+=2
                    cooling_transfer_E+=delta['E_transfer'];cooling_heating_E+=delta['E_heating_gate']
            else:
                if kind=='move':
                    count['movement_batches']+=1
                    for a,origin,target in zip(atoms,e['from_sites'],e['to_sites']):
                        d=math.dist(origin,target)*spacing
                        if d==0:count['zero_displacement_records']+=1;continue
                        count['moved_atom_events']+=1
                        n[a]+=heating_increment(d,e['duration_us'],h)
                        if h['loss_enabled']:delta['E_movement_loss']+=movement_loss_cost(n[a],h['loss_capacity'])
                        if n[a]>p['cooling']['threshold_n']:
                            warnings.append({'code':'threshold_exceeded','event_id':e['event_id'],'atom_id':a,'n':n[a],
                                             'behavior':'cooling only if explicitly scheduled; otherwise continue heating/loss'})
                elif kind=='cooling':
                    for q,new in zip(e['logical_qubit_ids'],e['cold_atom_ids']):carrier[q]=new;n[new]=p['cooling']['cold_n']
            for key,value in delta.items():terms[key]+=value
            if include_audit and (kind in ('move','gate','cooling','transfer')):
                audit.append({'event_id':e['event_id'],'time_us':time,'boundary':'start' if boundary==1 else 'complete',
                              'kind':kind,'n_before':before,'n_after':{a:n[a] for a in atoms+e.get('cold_atom_ids',[])},
                              'incremental_terms':{k:finite(v) for k,v in delta.items()},
                              'incremental_terms_infinite':{k:math.isinf(v) for k,v in delta.items()}})
    except (ValueError,KeyError,OverflowError,ZeroDivisionError) as exc:
        result.update(status='invalid',unavailable_reason='Nonphysical or undefined event factor: '+str(exc),warnings=warnings)
        return result
    result.update(budget=budget_json(terms),per_qubit_exposure=per_qubit,counts=dict(count),makespan_us=span,
                  final_n_by_physical_atom=n,final_physical_carriers=carrier,warnings=warnings,
                  cooling_diagnostics={'extra_transfer_E':finite(cooling_transfer_E),'extra_heating_E':finite(cooling_heating_E),
                                       'already_in_main_terms':True,'not_an_additional_error_term':True},
                  surrogate_heating=h['law']=='atomique_surrogate',
                  resource_track='hypothetical_registered_cold_banks' if p['cooling']['enabled'] else 'basic_no_cooling',
                  initial_spare_atom_population=p['cooling']['bank_count']*source['metadata']['hardware']['rows']*source['metadata']['hardware']['columns'])
    if include_audit:result['event_audit']=audit
    result['valid_for_comparison']=result['status']=='ok'
    return result