"""Separate deterministic correctness control; never replaces a native route.

Preserves DasAtom embeddings and gate groups, replacing transitions by serial
unit-grid steps through vacant sites. This is a conservative model control,
not a performance heuristic or implementation of proposed lookahead/repair.
"""
from collections import deque
import copy
from implementation.adapters.upstream import build_trace


class UnsupportedVacancyRoute(ValueError):pass


def grid_path(start,target,occupied,rows,columns):
    queue=deque([start]);parent={start:None}
    while queue:
        current=queue.popleft()
        if current==target:
            path=[]
            while current is not None:path.append(current);current=parent[current]
            return list(reversed(path))
        for dx,dy in [(-1,0),(0,-1),(0,1),(1,0)]:
            candidate=(current[0]+dx,current[1]+dy)
            if 0<=candidate[0]<rows and 0<=candidate[1]<columns and candidate not in occupied and candidate not in parent:
                parent[candidate]=current;queue.append(candidate)
    return None


def vacancy_transition(initial,target,rows,columns):
    """Evacuate both embeddings to the same staging map, reverse target path.

    The construction is deliberately conservative and can report unsupported
    when no separate accessible staging region exists. It is not a complete
    solver for every grid puzzle and makes no route-quality claim.
    """
    initial={q:tuple(p) for q,p in enumerate(initial)}
    target={q:tuple(p) for q,p in enumerate(target)}
    if initial.keys()!=target.keys() or len(set(initial.values()))!=len(initial) or len(set(target.values()))!=len(target):
        raise ValueError('Embedding must be injective')
    moving=sorted(q for q in initial if initial[q]!=target[q])
    if not moving:return []
    all_sites=list(initial.values())+list(target.values())
    min_x=min(p[0] for p in all_sites);max_x=max(p[0] for p in all_sites)
    min_y=min(p[1] for p in all_sites);max_y=max(p[1] for p in all_sites)
    vacant=[(x,y) for x in reversed(range(rows)) for y in reversed(range(columns))
        if not (min_x<=x<=max_x and min_y<=y<=max_y)]
    if len(vacant)<len(moving):raise UnsupportedVacancyRoute('Insufficient separate staging region')
    staging={q:p for q,p in zip(moving,vacant)}
    def evacuate(embedding):
        positions=dict(embedding);remaining=set(moving);steps=[]
        while remaining:
            occupied=set(positions.values());progress=False
            for q in sorted(remaining):
                path=grid_path(positions[q],staging[q],occupied-{positions[q]},rows,columns)
                if path is None:continue
                for a,b in zip(path,path[1:]):
                    steps.append({'kind':'move','items':[{'qubit':q,'from':a,'to':b,'cause':'correctness_staging'}]})
                    positions[q]=b
                remaining.remove(q);progress=True;break
            if not progress:raise UnsupportedVacancyRoute('No accessible staging path; no partial correction accepted')
        return positions,steps
    first,forward=evacuate(initial);second,backward=evacuate(target)
    if first!=second:raise ValueError('Staging maps differ')
    reversed_steps=[]
    for group in reversed(backward):
        item=group['items'][0]
        reversed_steps.append({'kind':'move','items':[{**item,'from':item['to'],'to':item['from']}]})
    return forward+reversed_steps


def corrected_trace(native,circuit,profile,origin):
    embeddings=native['embeddings'];groups=[]
    if not embeddings:raise UnsupportedVacancyRoute('No native embedding')
    groups.append({'kind':'initialize','items':[{'qubit':q,'site':p} for q,p in enumerate(embeddings[0])]})
    for i,embedding in enumerate(embeddings):
        for j,pairs in enumerate(native['gate_groups'][i]):
            groups.append({'kind':'gate','placement_batch':f'partition{i}_group{j}',
                'items':[{'qubits':[a,b],'sites':[embedding[a],embedding[b]]} for a,b in pairs]})
        if i+1<len(embeddings):
            transition=vacancy_transition(embedding,embeddings[i+1],profile['rows'],profile['columns'])
            for group in transition:group['placement_batch']=f'corrected_transition{i}_to{i+1}'
            groups.extend(transition)
    profile=copy.deepcopy(profile)
    profile.update(profile_id='vacancy_control_single_plane_assumption.v1',
        min_atom_separation_um=profile['spacing_um'],slm_aod_shared_plane=True,
        source='Pinned geometry; shared plane and one-site clearance are explicit model assumptions, not device calibration')
    profile['assumptions']=['Single plane; minimum separation equals site spacing; orthogonal unit-grid moves; no cooling']
    trace=build_trace(groups,circuit,profile,{**origin,'kind':'dasatom_corrected_vacancy_v1'},timing='two_transfer_stages')
    trace['metadata'].update(expected_final_positions={f'a{q}':p for q,p in enumerate(embeddings[-1])},
        correction_policy='serial_staging_grid_v1',source_native_placement_and_gate_groups_preserved=True,
        native_routing_choices_preserved=False,corrected_control_not_native_measurement=True)
    for event in trace['events']:
        if event['kind']=='move':event['provenance']['positions']='derived_by_vacancy_grid_control'
    return trace
