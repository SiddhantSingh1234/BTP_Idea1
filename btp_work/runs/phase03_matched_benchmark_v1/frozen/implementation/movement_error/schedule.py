"""NEW Phase 03: immutable source envelope, explicit retiming/cooling transform."""
from copy import deepcopy
import json
import math
from pathlib import Path
from implementation.trace.model import fingerprint
from implementation.validation.checker import check_trace
from implementation.movement_error.profiles import validate_profile
from implementation.movement_error.physics import movement_time, heating_increment

SCHEDULE_SCHEMA='neutral_atom_schedule.phase03.v1'


class UnsupportedSchedule(ValueError):
    pass


def decision_records(events):
    return [{k:e.get(k) for k in ('kind','logical_qubit_ids','gate_id','gate_type','from_sites','to_sites','sites')}
            for e in events if e['kind'] in ('move','gate')]


def cooling_suboperations(hot, cold, sites, bank, start, profile):
    """Two CNOTs with a prepared |0> target: 2CZ+4H, then two transfers."""
    noise=profile['noise'];c=profile['cooling'];clock=start;ops=[]
    bank_index=int(bank.rsplit('_',1)[1])
    ops.append({'kind':'register_cold_bank','bank_id':bank,'start_us':clock,'duration_us':c['bank_registration_us'],
                'from_z_um':(bank_index+1)*c['bank_storage_plane_pitch_um'],'to_z_um':c['dock_offset_um'],'population':'entire_bank'})
    clock+=c['bank_registration_us']
    ops.append({'kind':'prepare_cold_bank','bank_id':bank,'start_us':clock,'duration_us':c['bank_preparation_us'],
                'prepared_n':c['cold_n'],'prepared_state':'zero','population':'entire_bank'})
    clock+=c['bank_preparation_us']
    for old,new,site in zip(hot,cold,sites):
        for kind,atoms in [('h',[new]),('cz',[old,new]),('h',[new]),('h',[old]),('cz',[old,new]),('h',[old])]:
            duration=noise['h_duration_us'] if kind=='h' else noise['cz_duration_us']
            ops.append({'kind':kind,'atom_ids':atoms,'start_us':clock,'duration_us':duration,'site':site})
            clock+=duration
    for atoms,source,target in [(hot,'AOD0',c['sink_resource']),(cold,bank,'AOD0')]:
        ops.append({'kind':'transfer','atom_ids':list(atoms),'trap_from':source,'trap_to':target,
                    'start_us':clock,'duration_us':noise['transfer_duration_us']})
        clock+=noise['transfer_duration_us']
    return ops,clock-start


def make_schedule(trace, profile, operation='rescore'):
    p=validate_profile(profile)
    if operation not in ('rescore','retime','retime_and_cool'):raise ValueError('Unknown operation')
    if p['scorer']=='legacy' and operation!='rescore':raise ValueError('Legacy scorer never retimes')
    if operation=='retime_and_cool' and not p['cooling']['enabled']:
        raise UnsupportedSchedule('Cooling requested without physical spare resources')
    source=deepcopy(trace)
    result={'schema_version':SCHEDULE_SCHEMA,'phase':'03','operation':operation,
            'source_trace':source,'source_trace_sha256':fingerprint(source),
            'source_decisions_sha256':fingerprint(decision_records(source['events'])),
            'profile':p,'profile_sha256':fingerprint(p),'source_validation':check_trace(source),
            'events':deepcopy(source['events']),'transform_log':[],
            'assumptions':['Phase 03 model; source decisions remain fixed; no compiler optimization'],
            'native_physical_evidence_complete':source['metadata'].get('physical_evidence_complete',False)}
    if operation=='rescore':return result
    if p['scorer']!='extended':raise ValueError('Only extended schedules can be transformed')
    events=[];clock=0.0;carrier={};n={};banks_used=0
    initial=[e for e in source['events'] if e['kind']=='initialize']
    if len(initial)!=1:raise ValueError('Exactly one initialize event required')
    for a,q in zip(initial[0]['atom_ids'],initial[0]['logical_qubit_ids']):
        carrier[q]=a;n[a]=p['heating'].get('initial_n_by_qubit',{}).get(str(q),p['heating']['initial_n'])
    reconstruct=source['metadata'].get('timing_policy')=='evidence'
    if reconstruct and any(e['kind']=='transfer' for e in source['events']):
        raise UnsupportedSchedule('Mixed evidence/explicit transfer policy requires an explicit adapter')
    if reconstruct:result['assumptions'].append('NEW schedule reconstruction: one load/unload stage per nonzero movement; not native evidence')
    # Supported retiming input is serial routing/transfer stages with parallel CZ batches.
    previous_end=0.0;previous_batch=None
    for e in source['events']:
        if e['kind']=='initialize' or e.get('start_us') is None:continue
        batch=e.get('gate_batch') if e['kind']=='gate' else None
        if e['start_us']<previous_end-1e-8 and not (batch is not None and batch==previous_batch):
            raise UnsupportedSchedule('Retimer does not silently serialize independent overlapping stages')
        previous_end=max(previous_end,e['start_us']+e['duration_us']);previous_batch=batch
    def emit(event, duration, parent, start=None):
        nonlocal clock
        e=deepcopy(event);e['event_id']=f'p3_e{len(events):07}';e['parent_event_id']=parent
        e['start_us']=clock if start is None else start;e['duration_us']=duration
        e['atom_ids']=[carrier[q] for q in e['logical_qubit_ids']]
        e['provenance']={**e.get('provenance',{}),'phase03':'derived_schedule_transform'}
        events.append(e)
        result['transform_log'].append({'event_id':e['event_id'],'parent_event_id':parent,'kind':e['kind'],
                                        'start_us':e['start_us'],'duration_us':duration,'action':'added' if event.get('phase03_added') else 'retimed'})
        return e
    def transfer_for(move, movers, source_trap, target_trap):
        nonlocal clock
        if not movers:return
        e={k:deepcopy(v) for k,v in move.items() if k in ('logical_layer','placement_batch','routing_batch','source_group_index')}
        e.update(kind='transfer',logical_qubit_ids=movers,resources=['AOD0'],trap_from=source_trap,trap_to=target_trap,
                 provenance={'transfer':'inferred_Phase03_two_stage_policy'},phase03_added=True)
        emit(e,p['noise']['transfer_duration_us'],move['event_id']);clock+=p['noise']['transfer_duration_us']
    i=0
    while i<len(source['events']):
        original=source['events'][i];kind=original['kind'];parent=original['event_id']
        if kind=='initialize':
            e=emit(original,0,parent);e['trap_to']='SLM';clock=0.0;i+=1;continue
        if kind=='gate':
            group=[original];i+=1
            while i<len(source['events']) and source['events'][i]['kind']=='gate' and original.get('gate_batch') is not None and source['events'][i].get('gate_batch')==original.get('gate_batch'):
                group.append(source['events'][i]);i+=1
            for gate in group:emit(gate,p['noise']['cz_duration_us'],gate['event_id'],clock)
            clock+=p['noise']['cz_duration_us'];continue
        if kind=='transfer':
            emit(original,p['noise']['transfer_duration_us'],parent);clock+=p['noise']['transfer_duration_us'];i+=1;continue
        if kind=='wait':
            if original.get('duration_us') is None:raise UnsupportedSchedule('Untimed wait cannot be retimed')
            emit(original,original['duration_us'],parent);clock+=original['duration_us'];i+=1;continue
        if kind!='move':raise UnsupportedSchedule('Unsupported source operation '+kind)
        ds=[math.dist(a,b)*source['metadata']['hardware']['spacing_um'] for a,b in zip(original['from_sites'],original['to_sites'])]
        movers=[q for q,d in zip(original['logical_qubit_ids'],ds) if d>0]
        if reconstruct:transfer_for(original,movers,'SLM','AOD0')
        duration=movement_time(max(ds,default=0),p['movement'])
        e=emit(original,duration,parent)
        e['trajectory']={'kind':'shared_phase03_progress','family':p['movement']['family'],'distance_um':max(ds,default=0),'movement':deepcopy(p['movement'])}
        clock+=duration
        for q,d in zip(e['logical_qubit_ids'],ds):n[carrier[q]]+=heating_increment(d,duration,p['heating'])
        if operation=='retime_and_cool' and movers and any(n[carrier[q]]>p['cooling']['threshold_n'] for q in movers):
            c=p['cooling']
            if banks_used>=c['bank_count']:raise UnsupportedSchedule('Finite prepared cold banks exhausted; no implicit refill')
            # Standard reconstruction unloads each batch. Retained nonbatch AOD occupancy is not inferred.
            if not reconstruct:
                following=source['events'][i+1] if i+1<len(source['events']) else {}
                if following.get('kind')!='transfer' or following.get('trap_from')!='AOD0' or set(following['logical_qubit_ids'])!=set(movers):
                    raise UnsupportedSchedule('Cooling requires explicit whole-loaded-batch unload policy')
            bank=f'cold_bank_{banks_used}';banks_used+=1
            sites=[site for q,site,d in zip(e['logical_qubit_ids'],e['to_sites'],ds) if d>0]
            hot=[carrier[q] for q in movers];cold=[f'{bank}:r{int(s[0])}:c{int(s[1])}' for s in sites]
            subops,dt=cooling_suboperations(hot,cold,sites,bank,clock,p)
            cool={k:deepcopy(v) for k,v in original.items() if k in ('logical_layer','placement_batch','routing_batch')}
            cool.update(kind='cooling',logical_qubit_ids=movers,resources=['AOD0',bank,c['sink_resource'],c['controller_resource']],
                        cold_atom_ids=cold,bank_id=bank,sites=sites,suboperations=subops,reset_n=c['cold_n'],
                        handoff={'from_atom_ids':hot,'to_atom_ids':cold,'cold_state':'zero','primitive':c['primitive']},phase03_added=True)
            emit(cool,dt,parent);clock+=dt
            for q,new in zip(movers,cold):carrier[q]=new;n[new]=c['cold_n']
        if reconstruct:transfer_for(original,movers,'AOD0','SLM')
        i+=1
    result['events']=events
    result['assumptions'].append('Cooling, if present, uses the explicitly hypothetical registered-bank primitive')
    return result


def write_json_new(path, value, root):
    path=Path(path).resolve();root=Path(root).resolve()
    if not path.is_relative_to(root):raise ValueError('All output must stay inside btp_work')
    if path.exists():raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')