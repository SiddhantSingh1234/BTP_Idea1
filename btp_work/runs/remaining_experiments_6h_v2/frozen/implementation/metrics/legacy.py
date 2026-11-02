"""Replay-independent geometric accounting and exact historical proxy inputs."""
from collections import Counter
from itertools import combinations
import math
from implementation.validation.checker import line_compatible


def measure_trace(trace):
    metadata=trace['metadata'];profile=metadata['hardware'];events=trace['events']
    spacing=profile['spacing_um'];moves=[e for e in events if e['kind']=='move']
    gates=[e for e in events if e['kind']=='gate'];transfers=[e for e in events if e['kind']=='transfer']
    distances=[];batch_maxima=[];by_atom=Counter();parking=0;unknown_cause=0;zero=0
    graph_vertices=0;graph_edges=0;possible_edges=0
    for event in moves:
        lengths=[math.dist(a,b)*spacing for a,b in zip(event['from_sites'],event['to_sites'])]
        distances.extend(lengths);batch_maxima.append(max(lengths,default=0))
        for a,d,cause in zip(event['atom_ids'],lengths,event.get('causes',['unknown']*len(lengths))):
            by_atom[a]+=d
            zero+=int(d==0);parking+=int(cause=='cycle_break' and d>0)
            unknown_cause+=int(cause not in ['cycle_break','explicit_nonparking'])
        k=len(lengths);graph_vertices+=k;possible_edges+=k*(k-1)//2
        for i,j in combinations(range(k),2):
            if not line_compatible(event['from_sites'][i],event['to_sites'][i],event['from_sites'][j],event['to_sites'][j],profile.get('coordinate_tolerance',1e-9)):
                graph_edges+=1
    source=metadata.get('source_counts',{})
    B=source.get('nonempty_movement_blocks',len(moves))
    H=source.get('gate_stages',len({e.get('gate_batch',e['event_id']) for e in gates}))
    N=metadata.get('legacy_scored_qubits',metadata['circuit']['num_qubits'])
    G=metadata.get('legacy_scored_CZ',len(metadata['circuit']['gates']))
    D=sum(batch_maxima);t_cz=profile['cz_duration_us'];alias=4*B
    runtime=H*t_cz+alias*profile['transfer_stage_duration_us']+D/profile['move_speed_um_per_us']
    idle=N*runtime-G*t_cz
    if not (0<=profile['legacy_f_cz']<=1 and 0<=profile['legacy_f_transfer']<=1 and profile['legacy_T2_us']>0):
        raise ValueError('Nonphysical legacy score parameters')
    gate_exponent=(-G*math.log(profile['legacy_f_cz']) if profile['legacy_f_cz'] else math.inf) if G else 0.0
    exponent=gate_exponent+idle/profile['legacy_T2_us']
    if alias:
        exponent+=-alias*math.log(profile['legacy_f_transfer']) if profile['legacy_f_transfer'] else math.inf
    score=math.exp(-exponent) if exponent<746 else 0.0
    timed=[e for e in events if e['kind']!='initialize']
    all_timed=all(e.get('start_us') is not None and e.get('duration_us') is not None for e in timed)
    makespan=(max(e['start_us']+e['duration_us'] for e in timed)-min(e['start_us'] for e in timed)) if timed and all_timed else (0.0 if not timed else None)
    inferred=[e for e in transfers if e.get('provenance',{}).get('transfer','').startswith('inferred')]
    observed=[e for e in transfers if e not in inferred]
    legacy={'gate_stages':H,'movement_blocks':B,'scored_qubits':N,'scored_CZ':G,
        'sum_batch_max_distance_um':D,'four_per_block_transfer_alias':alias,
        'runtime_proxy_us':runtime,'idle_proxy_us':idle,
        'negative_log_fidelity':exponent if math.isfinite(exponent) else None,
        'negative_log_fidelity_infinite':not math.isfinite(exponent),'fidelity_proxy':score,
        'fidelity_underflow':score==0 and math.isfinite(exponent),
        'accounting_only':True,'not_actual_atom_transfer_count':True}
    return {'metric_version':'trace_metrics.v1','trace_validity_not_implied':True,
        'required_CZ':len(metadata['circuit']['gates']),'observed_CZ':len(gates),
        'routing_batches':len(moves),'gate_stages':len({e.get('gate_batch',e['event_id']) for e in gates}),
        'move_records':len(distances),'moved_atom_events':len(distances)-zero,'zero_displacement_records':zero,
        'sum_atom_distance_um':sum(distances),'max_atom_event_distance_um':max(distances,default=0),
        'distance_by_atom_um':dict(by_atom),'sum_batch_max_distance_um':D,
        'observed_transfer_atom_events':sum(len(e['atom_ids']) for e in observed),
        'observed_transfer_stages':len(observed),'inferred_transfer_atom_events':sum(len(e['atom_ids']) for e in inferred),
        'inferred_transfer_stages':len(inferred),'transfer_evidence_complete':metadata.get('physical_evidence_complete',False),
        'explicit_parking_atom_events':parking,'move_records_with_unknown_cause':unknown_cause,
        'makespan_us':makespan,'makespan_provenance':'derived_under_declared_policy' if metadata.get('timing_policy')!='evidence' else 'native_timing_unobserved',
        'emitted_batch_line_conflict_graph':{'vertices_sum':graph_vertices,'edges_sum':graph_edges,'possible_edges_sum':possible_edges,
            'density':graph_edges/possible_edges if possible_edges else 0.0,'scope':'within_emitted_batches_only'},
        'planner_candidate_conflict_graph':None,'legacy':legacy}
