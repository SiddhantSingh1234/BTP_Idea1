"""Independent discrete/CZ replay and analytic shared-progress path checks.

An OK result is limited to its declared model. Native evidence with omitted
transfers/trajectories is unsupported for full physical validation.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from itertools import combinations
import math
from implementation.trace.model import SCHEMA_VERSION, fingerprint


def closest_separation(a0, a1, b0, b1):
    """Minimum Euclidean distance for a common progress u in [0,1]."""
    r = [a-b for a,b in zip(a0,b0)]
    d = [(a-b)-(c-e) for a,b,c,e in zip(a1,a0,b1,b0)]
    denominator = sum(x*x for x in d)
    u = min(1.0,max(0.0,-sum(x*y for x,y in zip(r,d))/denominator)) if denominator else 0.0
    return math.sqrt(sum((x+u*y)**2 for x,y in zip(r,d))),u


def line_compatible(a0,a1,b0,b1,tolerance=1e-9):
    """Preserve <, = and > independently on both AOD axes."""
    def sign(x):
        return 0 if abs(x)<=tolerance else (1 if x>0 else -1)
    return all(sign(a0[k]-b0[k])==sign(a1[k]-b1[k]) for k in (0,1))


def check_trace(trace):
    errors=[]; unsupported=set(); checked=set(); unresolved_geometry=[]
    metadata=trace.get('metadata',{}); events=trace.get('events',[])
    def fail(code,event=None,detail=None):
        errors.append({'code':code,'event_id':event.get('event_id') if isinstance(event,dict) else event,'detail':detail})
    if metadata.get('schema_version')!=SCHEMA_VERSION:
        fail('schema_version')
    circuit=metadata.get('circuit',{}); profile=metadata.get('hardware',{})
    try:
        if metadata.get('circuit_sha256')!=fingerprint(circuit): fail('circuit_hash')
        if metadata.get('hardware_sha256')!=fingerprint(profile): fail('hardware_hash')
    except (ValueError,TypeError):
        fail('malformed_metadata_hash_input')
    for diagnostic in metadata.get('diagnostics',[]):
        fail(diagnostic.get('code','adapter_diagnostic'),detail=diagnostic)
    try:
        n=circuit['num_qubits']; expected=circuit['gates']
        if type(n) is not int or n<0 or not isinstance(expected,list): raise ValueError('num_qubits/gates')
        rows,columns=profile['rows'],profile['columns']
        if type(rows) is not int or type(columns) is not int or min(rows,columns)<1: raise ValueError('grid')
        for field in ['spacing_um','interaction_radius_um','restriction_radius_um']:
            if not math.isfinite(profile[field]) or profile[field]<=0: raise ValueError(field)
        for field in ['cz_duration_us','transfer_stage_duration_us','move_speed_um_per_us']:
            if field not in profile or not math.isfinite(profile[field]) or profile[field]<=0:raise ValueError(field)
        tolerance=profile.get('coordinate_tolerance',1e-9)
        if not math.isfinite(tolerance) or tolerance<0: raise ValueError('tolerance')
        separation=profile.get('min_atom_separation_um')
        if separation is not None and (not math.isfinite(separation) or separation<=0): raise ValueError('separation')
    except (KeyError,ValueError,TypeError,AttributeError) as exc:
        fail('malformed_metadata',detail=str(exc))
        return {'status':'invalid','violations':errors,'fully_validated_within_model':False,
                'coverage':{'checked':[],'unsupported':['replay_not_started']}}
    if profile.get('addressing')!='individual': unsupported.add('global_addressing')
    if profile.get('cooling_supported'): unsupported.add('cooling_not_implemented')
    if profile.get('aod_count',1)!=1:unsupported.add('multiple_AOD_trajectory_coupling')
    spacing=profile['spacing_um']; same_plane=profile.get('slm_aod_shared_plane')
    positions={}; logical={}; traps={}; seen_events=set(); seen_gates=Counter()
    gate_lookup={}; predecessors={}; last={}; actual_pairs=[]; intervals=[]; gate_groups=defaultdict(list); completed_gates=set()
    for gate in expected:
        try:
            identifier=gate['gate_id']; pair=gate['qubits']
            if identifier in gate_lookup or gate['gate_type']!='cz' or len(pair)!=2 or pair[0]==pair[1] or any(type(q) is not int or q<0 or q>=n for q in pair):
                raise ValueError('Invalid expected CZ')
            gate_lookup[identifier]=gate
            predecessors[identifier]={last[q] for q in pair if q in last}
            if set(gate.get('dependencies',[]))!=predecessors[identifier]: fail('circuit_dependencies',detail=identifier)
            for q in pair: last[q]=identifier
        except (KeyError,ValueError,TypeError) as exc:
            fail('malformed_circuit',detail=str(exc))
    if any(e['code']=='malformed_circuit' for e in errors):
        return {'status':'invalid','structural_valid':False,'violations':errors,'fully_validated_within_model':False,
                'coverage':{'checked':[],'unsupported':['replay_not_started']}}
    initialized=False; previous_start=-math.inf; zero_batches=0
    def site(value):
        if not isinstance(value,(list,tuple)) or len(value)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):
            raise ValueError('Invalid site')
        if any(abs(x-round(x))>tolerance for x in value): raise ValueError('Non-grid endpoint')
        if not (-tolerance<=value[0]<rows and -tolerance<=value[1]<columns): raise ValueError('Out-of-grid site')
        return tuple(round(x) for x in value)
    def occupancy(event):
        if separation is None:
            at_site=defaultdict(list)
            for a,p in positions.items():at_site[p].append(a)
            candidates=(pair for atoms_here in at_site.values() for pair in combinations(atoms_here,2))
        else:
            candidates=combinations(positions,2)
        for a,b in candidates:
            known=traps[a]!='unknown' and traps[b]!='unknown'
            co_planar=same_plane is True or (known and traps[a]==traps[b])
            distance=math.dist(positions[a],positions[b])*spacing
            if co_planar:
                if distance<=tolerance: fail('duplicate_occupancy',event,[a,b])
                elif separation is not None and distance+tolerance<separation: fail('minimum_separation_endpoint',event,[a,b])
            elif distance<=tolerance and (same_plane is None or not known):
                unsupported.add('coincident_sites_with_unobserved_traps')
                unresolved_geometry.append({'event_id':event.get('event_id'),'atoms':[a,b],
                    'site':list(positions[a]),'trap_states':[traps[a],traps[b]]})
    def known_trap(name):
        if name in ['SLM','unknown']:return True
        return isinstance(name,str) and name.startswith('AOD') and name[3:].isdigit() and int(name[3:])<profile.get('aod_count',1)
    for event in events:
        try:
            if not isinstance(event,dict): raise ValueError('Event must be an object')
            required_fields={'event_id','kind','logical_layer','placement_batch','routing_batch',
                'start_us','duration_us','resources','atom_ids','logical_qubit_ids','provenance'}
            if not required_fields.issubset(event):raise ValueError('Missing required event fields')
            identifier=event['event_id'];kind=event['kind']
            if not isinstance(identifier,str) or not identifier:raise ValueError('Invalid event ID')
            if not isinstance(event['resources'],list) or any(not isinstance(r,str) for r in event['resources']):raise ValueError('Invalid resources')
            if len(set(event['resources']))!=len(event['resources']):raise ValueError('Duplicate resource')
            if identifier in seen_events: fail('duplicate_event',event)
            seen_events.add(identifier)
            atoms=event['atom_ids']; qubits=event['logical_qubit_ids']
            if not isinstance(atoms,list) or any(not isinstance(a,str) for a in atoms) or len(set(atoms))!=len(atoms) or len(atoms)!=len(qubits): raise ValueError('Atom/qubit arrays')
            if any(type(q) is not int or not 0<=q<n for q in qubits): raise ValueError('Logical qubit index')
            start,duration=event.get('start_us'),event.get('duration_us')
            if start is None or duration is None:
                if start is not None or duration is not None: fail('malformed_time_interval',event)
                unsupported.add('timing_and_resources')
            else:
                if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in (start,duration)):
                    raise ValueError('Negative/nonfinite time interval')
                if start+tolerance<previous_start: fail('nonmonotone_event_time',event)
                previous_start=max(previous_start,start)
                if kind!='initialize': intervals.append((start,start+duration,event))
            if kind=='initialize':
                if initialized: fail('repeated_initialize',event)
                initialized=True
                if len(event['to_sites'])!=len(atoms): raise ValueError('Initialization array lengths')
                if set(qubits)!=set(range(n)): fail('missing_initial_qubits',event)
                for a,q,p in zip(atoms,qubits,event['to_sites']):
                    positions[a]=site(p);logical[a]=q;traps[a]=event.get('trap_to','unknown')
                    if not known_trap(traps[a]):fail('unknown_trap',event,traps[a])
                if len(set(logical.values()))!=len(logical): fail('duplicate_logical_state',event)
                occupancy(event);continue
            if not initialized: fail('uninitialized_trace',event);continue
            if any(a not in positions for a in atoms): fail('unknown_atom',event);continue
            if [logical[a] for a in atoms]!=qubits: fail('logical_carrier_mismatch',event)
            if kind=='transfer':
                source,target=event['trap_from'],event['trap_to']
                if source==target or source=='unknown' or target=='unknown' or not known_trap(source) or not known_trap(target): fail('invalid_transfer',event)
                if source.startswith('AOD') and target.startswith('AOD'):unsupported.add('inter_AOD_transfer')
                if duration is not None and duration+tolerance<profile.get('transfer_stage_duration_us',0):fail('transfer_duration',event)
                for a in atoms:
                    if traps[a]!=source: fail('transfer_prerequisite',event,a)
                    traps[a]=target
                occupancy(event)
            elif kind=='move':
                if len(event['from_sites'])!=len(atoms) or len(event['to_sites'])!=len(atoms): raise ValueError('Movement array lengths')
                origins={a:site(p) for a,p in zip(atoms,event['from_sites'])}
                destinations={a:site(p) for a,p in zip(atoms,event['to_sites'])}
                max_distance=max((math.dist(origins[a],destinations[a])*spacing for a in atoms),default=0)
                if duration is not None and max_distance>tolerance:
                    speed=profile.get('move_speed_um_per_us')
                    if duration<=0 or (speed is not None and duration*speed+tolerance<max_distance):fail('movement_duration_or_speed',event)
                for a in atoms:
                    if origins[a]!=positions[a]: fail('move_source_mismatch',event,a)
                    if origins[a]!=destinations[a] and not traps[a].startswith('AOD'):
                        if traps[a]=='unknown': unsupported.add('transfer_prerequisites')
                        else: fail('move_without_aod',event,a)
                zero_batches=zero_batches+1 if all(origins[a]==destinations[a] for a in atoms) else 0
                if zero_batches>1: fail('no_progress_batches',event)
                # Include retained AOD carriers: moving a shared line also moves them.
                coupled=list(atoms)+[a for a in positions if a not in atoms and traps[a].startswith('AOD')]
                for a,b in combinations(coupled,2):
                    aod_a=traps[a] if traps[a].startswith('AOD') else 'AOD0'
                    aod_b=traps[b] if traps[b].startswith('AOD') else 'AOD0'
                    if aod_a==aod_b and not line_compatible(positions[a],destinations.get(a,positions[a]),positions[b],destinations.get(b,positions[b]),tolerance):
                        fail('aod_line_order_or_equality',event,[a,b])
                checked.add('aod_order_equality_and_retained_carriers')
                trajectory=event.get('trajectory') or {}
                if trajectory.get('kind')!='shared_linear_progress': unsupported.add('continuous_trajectory')
                elif separation is None: unsupported.add('physical_minimum_separation')
                else:
                    for a,b in combinations(positions,2):
                        if a not in atoms and b not in atoms: continue
                        known=traps[a]!='unknown' and traps[b]!='unknown'
                        coplanar=same_plane is True or (known and traps[a]==traps[b])
                        if not coplanar:
                            if same_plane is None or not known: unsupported.add('cross_trap_geometry')
                            continue
                        distance,u=closest_separation(positions[a],destinations.get(a,positions[a]),positions[b],destinations.get(b,positions[b]))
                        if distance*spacing+tolerance<separation:
                            fail('continuous_collision',event,{'atoms':[a,b],'minimum_distance_um':distance*spacing,'progress':u})
                    checked.add('analytic_continuous_shared_progress')
                positions.update(destinations);occupancy(event)
            elif kind=='gate':
                gid=event.get('gate_id');pair=[logical[a] for a in atoms]
                if len(atoms)!=2 or event.get('gate_type')!='cz': fail('unsupported_gate',event);continue
                if duration is not None and duration+tolerance<profile.get('cz_duration_us',0):fail('gate_duration',event)
                required=gate_lookup.get(gid)
                if not required: fail('extra_gate',event)
                else:
                    if seen_gates[gid]: fail('duplicate_gate',event)
                    if set(pair)!=set(required['qubits']): fail('wrong_gate_operands',event)
                    if not predecessors[gid].issubset(completed_gates): fail('dependency_inversion',event)
                seen_gates[gid]+=1;completed_gates.add(gid);actual_pairs.append(pair)
                if event.get('sites') is not None and [site(p) for p in event['sites']]!=[positions[a] for a in atoms]: fail('gate_site_mismatch',event)
                for a in atoms:
                    if traps[a]=='unknown': unsupported.add('gate_trap_prerequisites')
                    elif traps[a]!=profile.get('gates_require_trap','SLM'): fail('gate_trap_prerequisite',event,a)
                if math.dist(positions[atoms[0]],positions[atoms[1]])*spacing>profile['interaction_radius_um']+tolerance: fail('interaction_range',event)
                group=event.get('gate_batch',identifier)
                for other,sites in gate_groups[group]:
                    if set(atoms)&set(other['atom_ids']): fail('parallel_gate_shared_atom',event)
                    if any(math.dist(positions[a],p)*spacing+tolerance<profile['restriction_radius_um'] for a in atoms for p in sites): fail('blockade_conflict',event)
                gate_groups[group].append((event,[positions[a] for a in atoms]))
            elif kind=='wait':
                pass
            elif kind=='cooling':
                unsupported.add('cooling_state_handoff')
            else:
                fail('unknown_event_kind',event,kind)
        except (KeyError,TypeError,ValueError,IndexError,AttributeError) as exc:
            fail('malformed_event',event,str(exc))
    if not initialized: fail('missing_initialize')
    for gid in gate_lookup:
        if not seen_gates[gid]: fail('missing_gate',detail=gid)
    # Independent temporal resource checks, also across different gate groups.
    active=[]
    for s2,e2,b in sorted(intervals,key=lambda item:item[0]):
        active=[item for item in active if item[1]>s2+tolerance]
        for s1,e1,a in active:
            if min(e1,e2)-max(s1,s2)<=tolerance: continue
            if set(a['atom_ids'])&set(b['atom_ids']): fail('overlapping_atom_intervals',b,a['event_id'])
            if set(a.get('resources',[]))&set(b.get('resources',[])): fail('resource_overlap',b,a['event_id'])
            if {a['kind'],b['kind']}=={'move','gate'} and not profile.get('allow_move_gate_overlap',False): fail('move_gate_overlap',b,a['event_id'])
            if a['kind']==b['kind']=='gate' and a.get('gate_batch')!=b.get('gate_batch'):
                if a.get('sites') and b.get('sites') and any(math.dist(p,q)*spacing+tolerance<profile['restriction_radius_um'] for p in a['sites'] for q in b['sites']): fail('blockade_conflict_timed',b,a['event_id'])
        active.append((s2,e2,b))
    final=metadata.get('expected_final_positions')
    if final is not None and {a:list(p) for a,p in positions.items()}!=final: fail('final_mapping_mismatch')
    if not metadata.get('origin',{}).get('original_register_complete',True): unsupported.add('original_declared_register')
    if separation is None: unsupported.add('physical_minimum_separation')
    if any(t=='unknown' for t in traps.values()): unsupported.add('trap_ownership')
    checked.update(['CZ_gate_identity_and_dependencies','logical_carrier_mapping','endpoint_grid_bounds','gate_geometry','final_mapping'])
    # Tiny CZ diagonal-unitary check, with explicit physical output permutation.
    # Compare all basis phases independently of the DAG/order check above.
    semantics={'level':'structural_CZ_only','full_original_circuit_checked':False}
    ordered=sorted(positions,key=lambda a:(positions[a],a))
    permutation=[logical[a] for a in ordered]
    semantics['physical_output_slot_to_logical_qubit']=permutation
    if n<=8 and len(permutation)==n and set(permutation)==set(range(n)):
        expected_pairs=[g['qubits'] for g in expected]
        mismatch=False
        for basis in range(1<<n):
            target_phase=sum(((basis>>a)&1)*((basis>>b)&1) for a,b in expected_pairs)%2
            physical_bits=[(basis>>q)&1 for q in permutation]
            slot={q:i for i,q in enumerate(permutation)}
            actual_phase=sum(physical_bits[slot[a]]*physical_bits[slot[b]] for a,b in actual_pairs)%2
            if actual_phase!=target_phase: mismatch=True;break
        semantics.update(level='exhaustive_CZ_basis_phases_with_final_permutation',basis_states=1<<n,equivalent=not mismatch)
        if mismatch: fail('CZ_unitary_mismatch')
    result={'status':'invalid' if errors else ('unsupported' if unsupported else 'ok'),
        'structural_valid':not errors,'violations':errors,
        'coverage':{'checked':sorted(checked),'unsupported':sorted(unsupported),'not_applicable':['unintended_global_pulses'] if profile.get('addressing')=='individual' else []},
        'fully_validated_within_model':not errors and not unsupported,
        'source_physical_evidence_complete':metadata.get('physical_evidence_complete',False),
        'unresolved_coincident_sites':unresolved_geometry,
        'model_assumptions':metadata.get('assumptions',[]),'semantics':semantics,
        'final_positions':{a:list(p) for a,p in positions.items()},'final_logical_mapping':logical,
        'observed_gate_count':sum(seen_gates.values())}
    return result
