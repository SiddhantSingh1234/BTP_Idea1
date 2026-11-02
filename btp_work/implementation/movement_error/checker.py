"""NEW Phase 03 independent schedule validator; no planner/scorer acceptance imports.

The v1 projection is justified only for a shared monotone progress function.
Registered cooling is an explicit primitive contract, not optical-control proof.
"""
from copy import deepcopy
import math
from implementation.trace.model import fingerprint
from implementation.validation.checker import check_trace
from implementation.movement_error.profiles import validate_profile


def validate_schedule(schedule):
    failures=[];unsupported=[];tol=1e-8
    def fail(code,event=None,detail=None):
        failures.append({'code':code,'event_id':event.get('event_id') if isinstance(event,dict) else event,'detail':detail})
    try:
        if schedule['schema_version']!='neutral_atom_schedule.phase03.v1':raise ValueError('Schedule schema')
        p=validate_profile(schedule['profile']);source=schedule['source_trace'];events=schedule['events']
        if fingerprint(p)!=schedule['profile_sha256']:fail('profile_hash')
        if fingerprint(source)!=schedule['source_trace_sha256']:fail('source_trace_hash')
        source_check=check_trace(source)
        if source_check['status']=='invalid':fail('source_trace_invalid',detail=source_check['violations'])
        native_invalid=source['metadata'].get('origin',{}).get('upstream_status')=='invalid'
        corrected=(source['metadata'].get('origin',{}).get('kind')=='dasatom_corrected_vacancy_v1'
                   and source['metadata'].get('correction_policy')=='serial_staging_grid_v1'
                   and source['metadata'].get('corrected_control_not_native_measurement') is True)
        if native_invalid and not corrected:fail('original_native_status_invalid')
        if not isinstance(events,list) or not events:raise ValueError('Missing event stream')
        def decisions(es):
            return [{k:e.get(k) for k in ('kind','logical_qubit_ids','gate_id','gate_type','from_sites','to_sites','sites')}
                    for e in es if e['kind'] in ('move','gate')]
        ds=fingerprint(decisions(source['events']))
        if ds!=schedule['source_decisions_sha256'] or ds!=fingerprint(decisions(events)):fail('placement_or_gate_decisions_changed')
        if schedule['operation']=='rescore' and events!=source['events']:fail('rescore_changed_events')
        if schedule['operation'] not in ('rescore','retime','retime_and_cool'):fail('operation')
        if schedule['operation']!='retime_and_cool' and any(e['kind']=='cooling' for e in events):fail('cooling_transform_not_declared')
        original_hardware=source['metadata']['hardware'];spacing=original_hardware['spacing_um']
        initial=[e for e in events if e['kind']=='initialize']
        if len(initial)!=1 or events[0]['kind']!='initialize':raise ValueError('Initialization must occur exactly once, first')
        init=initial[0];num=source['metadata']['circuit']['num_qubits']
        if set(init['logical_qubit_ids'])!=set(range(num)):fail('initial_qubits')
        if len(set(init['atom_ids']))!=len(init['atom_ids']):fail('initial_atom_identity')
        carrier=dict(zip(init['logical_qubit_ids'],init['atom_ids']))
        positions=dict(zip(init['logical_qubit_ids'],init['to_sites']))
        n={q:p['heating'].get('initial_n_by_qubit',{}).get(str(q),p['heating']['initial_n']) for q in carrier}
        if set(map(int,p['heating'].get('initial_n_by_qubit',{})))-set(carrier):fail('unknown_initial_n_override')
        if set(map(int,p['exposure']['T2_by_qubit_us']))-set(carrier):fail('unknown_T2_override')
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        return {'status':'invalid','violations':failures+[{'code':'malformed_schedule','detail':str(exc)}],
                'fully_validated_within_model':False,'coverage':{'unsupported':['replay_not_started']}}
    if p['scorer']=='legacy':
        return {'status':'invalid' if failures else source_check['status'],'violations':failures,'fully_validated_within_model':False,
                'historical_accounting_only':True,'source_validation':source_check,'coverage':{'unsupported':['legacy_not_physical_model']}}
    required_fields={'event_id','kind','logical_layer','placement_batch','routing_batch','start_us','duration_us','resources','atom_ids','logical_qubit_ids','provenance'}
    if any(not isinstance(e,dict) or not required_fields.issubset(e) for e in events):
        return {'status':'invalid','violations':failures+[{'code':'malformed_event','detail':'Missing required event fields'}],
                'fully_validated_within_model':False,'coverage':{'unsupported':['replay_not_started']}}
    if any(e.get('start_us') is None or e.get('duration_us') is None for e in events):
        return {'status':'invalid' if failures else 'unsupported','violations':failures,'fully_validated_within_model':False,
                'source_validation':source_check,'coverage':{'unsupported':['physical_timing_unobserved']}}
    identifiers=set();previous=-1;intervals=[];average_speed=0.0
    for e in events:
        try:
            identifier=e['event_id'];s=e['start_us'];t=e['duration_us']
            if identifier in identifiers:fail('duplicate_event',e)
            identifiers.add(identifier)
            if any(type(v) not in (float,int) or not math.isfinite(v) or v<0 for v in (s,t)):raise ValueError('Invalid time')
            if s<previous-tol:fail('nonmonotone_event_time',e)
            previous=s
            qs=e['logical_qubit_ids'];atoms=e['atom_ids']
            if len(qs)!=len(atoms) or len(set(qs))!=len(qs) or len(set(atoms))!=len(atoms):fail('event_population',e)
            if e['kind']!='initialize':intervals.append((s,s+t,e))
            if e['kind']=='move':
                lengths=[math.dist(a,b)*spacing for a,b in zip(e['from_sites'],e['to_sites'])]
                if len(lengths)!=len(qs):fail('move_shapes',e)
                d=max(lengths,default=0.0)
                if d and t<=0:fail('movement_time',e);continue
                if t:average_speed=max(average_speed,d/t)
                tr=e.get('trajectory') or {};family=tr.get('family')
                if tr.get('kind')=='shared_linear_progress':family='linear'
                elif tr.get('kind')=='shared_phase03_progress':
                    if tr.get('movement')!=p['movement'] or tr.get('distance_um')!=d:fail('trajectory_parameters',e)
                else:unsupported.append('unrecognized_continuous_trajectory')
                if family not in ('linear','cubic','triangular'):unsupported.append('trajectory_family')
                if p['heating']['law']=='atomique_cubic' and family!='cubic':fail('heating_trajectory_mismatch',e)
                if schedule['operation']!='rescore':
                    m=p['movement'];a=m['acceleration_um_per_us2'];v=m['velocity_cap_um_per_us'];required=0.0
                    if family!=m['family']:fail('retimed_trajectory_family',e)
                    if d:
                        if family=='cubic':required=max(math.sqrt(6*d/a),1.5*d/v if v else 0)
                        elif family=='triangular':required=2*math.sqrt(d/a) if v is None or d<=v*v/a else d/v+v/a
                        else:required=d/m['speed_um_per_us']
                        required=max(required,m['minimum_duration_us'])
                    if t+tol<required:fail('trajectory_bound',e,{'required_us':required,'actual_us':t})
                if d and p['heating']['law']!='disabled' and p['heating']['multiplier']>0:
                    if 2*math.pi*p['heating']['cyclic_frequency_khz']*.001*t<p['heating']['asymptotic_omega_T_min']:
                        unsupported.append('heating_asymptotic_regime')
            elif e['kind']=='gate' and t+tol<p['noise']['cz_duration_us']:fail('gate_duration',e)
            elif e['kind']=='transfer' and t+tol<p['noise']['transfer_duration_us']:fail('transfer_duration',e)
            elif e['kind'] not in ('initialize','gate','transfer','wait','cooling'):fail('unknown_event_kind',e)
        except (KeyError,TypeError,ValueError,IndexError) as exc:fail('malformed_event',e,str(exc))
    if any(v['code']=='malformed_event' for v in failures):
        return {'status':'invalid','violations':failures,'fully_validated_within_model':False,'source_validation':source_check,
                'coverage':{'unsupported':['malformed_event_stops_physical_replay']}}
    active=[]
    for start,end,e in sorted(intervals,key=lambda item:item[0]):
        active=[x for x in active if x[1]>start+tol]
        for s1,e1,other in active:
            if min(end,e1)-max(start,s1)<=tol:continue
            if set(e['logical_qubit_ids'])&set(other['logical_qubit_ids']):fail('logical_overlap',e,other['event_id'])
            atoms=set(e['atom_ids']+e.get('cold_atom_ids',[]));other_atoms=set(other['atom_ids']+other.get('cold_atom_ids',[]))
            if atoms&other_atoms:fail('physical_atom_overlap',e,other['event_id'])
            if set(e['resources'])&set(other['resources']):fail('resource_overlap',e,other['event_id'])
        active.append((start,end,e))
    # Replay completion before start at equal timestamps. This is separate from scorer replay.
    boundaries=[];used_banks=set();retired=set();cool_population=0
    for index,e in enumerate(events):
        if e['kind']=='initialize':continue
        if e['duration_us']==0 and e['kind'] not in ('move','wait'):fail('zero_operation_duration',e)
        boundaries.append((e['start_us'],1,index))
        boundaries.append((e['start_us']+e['duration_us'],2 if e['duration_us']==0 else 0,index))
    for _,boundary,index in sorted(boundaries):
        e=events[index];kind=e['kind'];qs=e['logical_qubit_ids']
        try:
            if boundary==1:
                if e['atom_ids']!=[carrier[q] for q in qs]:fail('stale_physical_carrier',e)
                if set(e['atom_ids'])&retired:fail('retired_atom_reused',e)
                if kind=='cooling':
                    c=p['cooling'];bank=e['bank_id'];hot=e['atom_ids'];cold=e['cold_atom_ids'];sites=e['sites']
                    if not c['enabled']:fail('cooling_resources_absent',e)
                    legal_banks={f'cold_bank_{i}' for i in range(c['bank_count'])}
                    if bank not in legal_banks or bank in used_banks:fail('cold_bank_exhaustion_or_reuse',e)
                    used_banks.add(bank)
                    if e.get('reset_n')!=c['cold_n']:fail('cooling_reset',e)
                    if e.get('handoff')!={'from_atom_ids':hot,'to_atom_ids':cold,'cold_state':'zero','primitive':c['primitive']}:fail('cooling_state_handoff',e)
                    if [positions[q] for q in qs]!=sites:fail('cooling_dock_site',e)
                    expected_cold=[f'{bank}:r{int(s[0])}:c{int(s[1])}' for s in sites]
                    if cold!=expected_cold or len(set(cold))!=len(qs):fail('cold_atom_identity',e)
                    if set(cold)&set(carrier.values()):fail('cold_atom_not_fresh',e)
                    if set(e['resources'])!={'AOD0',bank,c['sink_resource'],c['controller_resource']}:fail('cooling_resource_reservation',e)
                    if c['dock_offset_um']>original_hardware['interaction_radius_um']+tol:fail('cooling_CZ_range',e)
                    minimum=original_hardware.get('min_atom_separation_um')
                    if minimum is not None and c['dock_offset_um']+tol<minimum:fail('cooling_cross_plane_clearance',e)
                    # The previous move must load/cool exactly the same nonzero set.
                    prev=events[index-1] if index else {}
                    if prev.get('kind')!='move' or abs(prev['start_us']+prev['duration_us']-e['start_us'])>tol:fail('cooling_event_order',e)
                    else:
                        moved=[q for q,a,b in zip(prev['logical_qubit_ids'],prev['from_sites'],prev['to_sites']) if a!=b]
                        if qs!=moved:fail('cooling_population',e)
                    if not any(n[q]>c['threshold_n'] for q in qs):fail('cooling_without_trigger',e)
                    ops=e['suboperations'];j=0;clock=e['start_us']
                    register=ops[j];j+=1
                    index_bank=int(bank.rsplit('_',1)[1])
                    if register!={'kind':'register_cold_bank','bank_id':bank,'start_us':clock,'duration_us':c['bank_registration_us'],
                                  'from_z_um':(index_bank+1)*c['bank_storage_plane_pitch_um'],'to_z_um':c['dock_offset_um'],'population':'entire_bank'}:fail('cold_bank_registration',e)
                    clock+=c['bank_registration_us']
                    prepare=ops[j];j+=1
                    if prepare!={'kind':'prepare_cold_bank','bank_id':bank,'start_us':clock,'duration_us':c['bank_preparation_us'],
                                 'prepared_n':c['cold_n'],'prepared_state':'zero','population':'entire_bank'}:fail('cold_bank_preparation',e)
                    clock+=c['bank_preparation_us']
                    for old,new,site in zip(hot,cold,sites):
                        expected=[('h',[new]),('cz',[old,new]),('h',[new]),('h',[old]),('cz',[old,new]),('h',[old])]
                        for k,atoms in expected:
                            op=ops[j];j+=1;duration=p['noise']['h_duration_us'] if k=='h' else p['noise']['cz_duration_us']
                            if op.get('kind')!=k or op.get('atom_ids')!=atoms or op.get('site')!=site:fail('cooling_gate_sequence',e)
                            if abs(op['start_us']-clock)>tol or abs(op['duration_us']-duration)>tol:fail('cooling_suboperation_time',e)
                            clock+=duration
                    for atoms,source_trap,target in [(hot,'AOD0',c['sink_resource']),(cold,bank,'AOD0')]:
                        op=ops[j];j+=1;duration=p['noise']['transfer_duration_us']
                        if op.get('kind')!='transfer' or op.get('atom_ids')!=atoms or op.get('trap_from')!=source_trap or op.get('trap_to')!=target:fail('cooling_transfer_sequence',e)
                        if abs(op['start_us']-clock)>tol or abs(op['duration_us']-duration)>tol:fail('cooling_suboperation_time',e)
                        clock+=duration
                    if j!=len(ops) or abs(clock-e['start_us']-e['duration_us'])>tol:fail('cooling_total_time_or_double_count',e)
                    cool_population+=len(qs)
            else:
                if kind=='move':
                    for q,a,b in zip(qs,e['from_sites'],e['to_sites']):
                        d=math.dist(a,b)*spacing
                        if d and e['duration_us']>0 and p['heating']['law']!='disabled':
                            w=2*math.pi*p['heating']['cyclic_frequency_khz']*.001
                            n[q]+=p['heating']['multiplier']*.5*(6*d/(p['heating']['x_zpf_um']*w*w*e['duration_us']**2))**2
                        positions[q]=b
                elif kind=='cooling':
                    retired.update(e['atom_ids'])
                    for q,new in zip(qs,e['cold_atom_ids']):carrier[q]=new;n[q]=p['cooling']['cold_n']
        except (KeyError,TypeError,ValueError,IndexError,ZeroDivisionError) as exc:fail('malformed_physical_replay',e,str(exc))
    # Prove geometry under the unchanged logical decisions, with monotone reparameterization.
    projection=deepcopy(source);pm=projection['metadata'];hw=pm['hardware']
    hw['cooling_supported']=False;hw['aod_count']=1
    hw['move_speed_um_per_us']=max(average_speed*1.000001,1e-9)
    hw['cz_duration_us']=p['noise']['cz_duration_us'];hw['transfer_stage_duration_us']=p['noise']['transfer_duration_us']
    pm['hardware_sha256']=fingerprint(hw);pe=[]
    initial_alias=dict(zip(init['atom_ids'],[f'a{q}' for q in init['logical_qubit_ids']]))
    if pm.get('expected_final_positions') is not None:
        pm['expected_final_positions']={initial_alias.get(a,a):site for a,site in pm['expected_final_positions'].items()}
    for e in events:
        item=deepcopy(e);item['atom_ids']=[f'a{q}' for q in item['logical_qubit_ids']]
        if item['kind']=='cooling':item['kind']='wait'
        if item['kind']=='move' and (item.get('trajectory') or {}).get('kind') in ('shared_phase03_progress','shared_linear_progress'):
            item['trajectory']={'kind':'shared_linear_progress','proof':'Same geometric progress interval; timing bounds checked independently by Phase03'}
        pe.append(item)
    projection['events']=pe
    base=check_trace(projection)
    failures.extend(base['violations']);unsupported.extend(base['coverage']['unsupported'])
    status='invalid' if failures else ('unsupported' if unsupported else 'ok')
    return {'status':status,'violations':failures,'fully_validated_within_model':status=='ok',
            'source_validation':source_check,'geometry_projection_validation':base,
            'coverage':{'checked':['trajectory_bounds','completion_before_start','physical_carrier_handoff','finite_cold_banks','cooling_suboperations','resources','shared_progress_geometry_projection'],
                        'unsupported':sorted(set(unsupported)),'primitive_assumptions':['Registered cold-bank geometry and trap handovers are a declared hypothetical primitive, not measured optical-control evidence']},
            'original_native_status_invalid':native_invalid,'corrected_control':corrected,
            'cooling_episodes':len(used_banks),'cooled_atom_events':cool_population,'final_physical_carriers':carrier,'final_n_by_qubit':n}