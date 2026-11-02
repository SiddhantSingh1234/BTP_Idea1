"""Vacancy-aware DasAtom routing under the original discrete geometry contract.

Preserve native transitions that already satisfy the declared model. Correct
only failed transitions, never assign new active interaction sites or optimize
a future/score objective. No compiler predicate is imported by the validator.
"""
from collections import deque
import copy
import math
from implementation.adapters.upstream import build_trace
from implementation.trace.model import circuit_from_pairs,evidence_profile


class RoutingUnsupported(ValueError):pass
class CapacityUnsupported(ValueError):pass


def point_segment_squared(point,start,end):
    dx=end[0]-start[0];dy=end[1]-start[1]
    denominator=dx*dx+dy*dy
    if not denominator:return (point[0]-start[0])**2+(point[1]-start[1])**2
    fraction=max(0,min(1,((point[0]-start[0])*dx+(point[1]-start[1])*dy)/denominator))
    return (point[0]-start[0]-fraction*dx)**2+(point[1]-start[1]-fraction*dy)**2


def pair_clear(a,b,minimum_squared=None):
    _,p,q=a;_,r,s=b
    for axis in [0,1]:
        old=p[axis]-r[axis];new=q[axis]-s[axis]
        if (old==0)!=(new==0) or old*new<0:return False
    if minimum_squared is None:return True
    relative=(p[0]-r[0],p[1]-r[1]);end=(q[0]-s[0],q[1]-s[1])
    return point_segment_squared((0,0),relative,end)>=minimum_squared-1e-10


def batch_safe(batch,positions,rows,columns,minimum_squared=None):
    qubits=[m[0] for m in batch]
    if len(set(qubits))!=len(qubits):return False
    proposed=dict(positions)
    for q,start,end in batch:
        if q not in positions or tuple(start)!=positions[q]:return False
        if not all(type(v) in (int,float) and math.isfinite(v) and v==round(v) for v in end):return False
        if not (0<=end[0]<rows and 0<=end[1]<columns):return False
        proposed[q]=tuple(end)
        if minimum_squared is not None:
            for stationary,site in positions.items():
                if stationary not in qubits and point_segment_squared(site,start,end)<minimum_squared-1e-10:return False
    if len(set(proposed.values()))!=len(proposed):return False
    return all(pair_clear(a,b,minimum_squared) for i,a in enumerate(batch) for b in batch[i+1:])


def find_path(start,target,occupied,rows,columns):
    queue=deque([start]);parent={start:None}
    while queue:
        site=queue.popleft()
        if site==target:
            result=[]
            while site is not None:result.append(site);site=parent[site]
            return result[::-1]
        for dx,dy in [(-1,0),(0,-1),(0,1),(1,0)]:
            nxt=(site[0]+dx,site[1]+dy)
            if 0<=nxt[0]<rows and 0<=nxt[1]<columns and nxt not in occupied and nxt not in parent:
                parent[nxt]=site;queue.append(nxt)
    return None


def compressed_segments(path):
    if len(path)<2:return []
    result=[];start=path[0];previous=path[0];direction=None
    for site in path[1:]:
        step=(site[0]-previous[0],site[1]-previous[1])
        if direction is not None and step!=direction:result.append((start,previous));start=previous
        direction=step;previous=site
    result.append((start,previous));return result


def route_transition(initial,target,rows,columns,native_batches=None):
    positions={q:tuple(p) for q,p in enumerate(initial)};goals={q:tuple(p) for q,p in enumerate(target)}
    if positions.keys()!=goals.keys() or len(set(positions.values()))!=len(positions) or len(set(goals.values()))!=len(goals):raise ValueError('Noninjective/inconsistent embeddings')
    for site in [*positions.values(),*goals.values()]:
        if not (0<=site[0]<rows and 0<=site[1]<columns):raise CapacityUnsupported('Embedding exceeds requested grid')
    if native_batches is not None:
        candidate=dict(positions);safe=True
        for batch in native_batches:
            if not batch_safe(batch,candidate,rows,columns):safe=False;break
            candidate.update({q:tuple(end) for q,start,end in batch})
        if safe and candidate==goals:return copy.deepcopy(native_batches),{'native_transition_reused':True,'correction_steps':0}
    output=[];pending={q for q in positions if positions[q]!=goals[q]};visited=set();limit=20*len(positions)+rows*columns;deferred={}
    def emit(q,path):
        for a,b in compressed_segments(path):
            batch=[[q,list(a),list(b)]]
            if not batch_safe(batch,positions,rows,columns):raise RoutingUnsupported('Internal unsafe waypoint rejected')
            output.append(batch);positions[q]=b
    def parking(q):
        # Legacy native logs do not specify a minimum path-clearance parameter.
        # Enforce vacant destinations and AOD line compatibility, and let the
        # independent checker label continuous-clearance evidence unsupported.
        occupied=set(positions.values());reserved=set(goals.values())
        candidates=[(x,y) for x in range(rows) for y in range(columns) if (x,y) not in occupied and (x,y) not in reserved]
        if candidates:
            chosen=min(candidates,key=lambda p:((p[0]-positions[q][0])**2+(p[1]-positions[q][1])**2,p))
            return [positions[q],chosen]
        return None

    iterations=0
    while pending:
        iterations+=1;signature=tuple(sorted(positions.items()))
        if iterations>limit or signature in visited:raise RoutingUnsupported('Bounded vacancy router made no progress')
        visited.add(signature);occupied=set(positions.values());ready=[q for q in sorted(pending) if goals[q] not in occupied and deferred.get(q) not in pending]
        batch=[]
        for q in ready:
            proposal=[q,list(positions[q]),list(goals[q])]
            if batch_safe(batch+[proposal],positions,rows,columns):batch.append(proposal)
        if batch:
            output.append(batch)
            for q,start,end in batch:positions[q]=tuple(end);pending.remove(q)
            continue
        progressed=False
        for q in ready:
            path=find_path(positions[q],goals[q],occupied-{positions[q]},rows,columns)
            if path:
                emit(q,path);pending.remove(q);progressed=True;break
        if progressed:continue
        # Break a cycle or open an obstructed empty destination. Include settled
        # blocking atoms only when no pending atom can reach a parking vacancy.
        candidates=[]
        if ready:
            for q in ready:
                relaxed=find_path(positions[q],goals[q],set(),rows,columns)
                if relaxed:
                    for site in relaxed[1:]:
                        candidates.extend((a,q) for a,p in positions.items() if p==site and a!=q)
        if not candidates:
            # Park only a current occupant of a pending destination. Re-parking
            # an unrelated already parked atom cannot resolve a dependency.
            for incoming in sorted(pending):
                candidates.extend((a,incoming) for a,p in positions.items() if p==goals[incoming] and a!=incoming)
        for q,trigger in dict.fromkeys(candidates):
            if deferred.get(q) in pending:continue
            path=parking(q)
            if path:
                emit(q,path);pending.add(q);deferred[q]=trigger;progressed=True;break
        if not progressed:raise RoutingUnsupported('No accessible vacancy; full/blocked grid cannot be silently repaired')
    if positions!=goals:raise RoutingUnsupported('Incomplete corrected transition')
    return output,{'native_transition_reused':False,'correction_steps':len(output)}


def restore_idle_qubits(embeddings,declared_n,rows,columns):
    if declared_n>rows*columns:raise CapacityUnsupported('Declared register exceeds grid capacity')
    if not embeddings:
        return [[[q//columns,q%columns] for q in range(declared_n)]]
    native_n=len(embeddings[0])
    if native_n>declared_n or any(len(e)!=native_n for e in embeddings):raise ValueError('Embedding population mismatch')
    result=[[list(site) for site in embedding] for embedding in embeddings];needed=declared_n-native_n
    union={tuple(p) for e in embeddings for p in e}
    common=[(x,y) for x in reversed(range(rows)) for y in reversed(range(columns)) if (x,y) not in union]
    for i,embedding in enumerate(result):
        occupied={tuple(p) for p in embedding}
        for offset in range(needed):
            preferred=common[offset] if offset<len(common) else (tuple(result[i-1][native_n+offset]) if i else None)
            if preferred is None or preferred in occupied:
                preferred=next(((x,y) for x in reversed(range(rows)) for y in reversed(range(columns)) if (x,y) not in occupied),None)
            if preferred is None:raise CapacityUnsupported('No vacant site for declared idle qubit')
            embedding.append(list(preferred));occupied.add(preferred)
    return result


def repair_native(native,circuit,grid,r_int=2,r_blk=4,origin=None):
    declared_n=circuit['num_qubits'];original_n=len(native['embeddings'][0]) if native['embeddings'] else 0
    if native.get('actual_grid',grid)!=grid:raise CapacityUnsupported('Native expanded grid does not match requested hardware')
    embeddings=restore_idle_qubits(native['embeddings'],declared_n,grid,grid)
    if len(native['gate_groups'])!=len(native['embeddings']):raise ValueError('Native gate/embedding array lengths disagree')
    groups=[{'kind':'initialize','items':[{'qubit':q,'site':p} for q,p in enumerate(embeddings[0])]}]
    corrected_movements=[];reports=[]
    for i,embedding in enumerate(embeddings):
        stage_groups=native['gate_groups'][i] if i<len(native['gate_groups']) else []
        for j,pairs in enumerate(stage_groups):
            groups.append({'kind':'gate','placement_batch':f'partition{i}_group{j}',
                'items':[{'qubits':[a,b],'sites':[embedding[a],embedding[b]]} for a,b in pairs]})
        if i+1<len(embeddings):
            original=native.get('movement_list',[])
            batches,report=route_transition(embedding,embeddings[i+1],grid,grid,original[i] if i<len(original) else None)
            corrected_movements.append(batches);reports.append(report)
            for batch in batches:
                groups.append({'kind':'move','placement_batch':f'transition{i}_to{i+1}',
                    'items':[{'qubit':q,'from':a,'to':b,'cause':'unknown_upstream_move' if report['native_transition_reused'] else 'correctness_vacancy'} for q,a,b in batch]})
    profile=evidence_profile(grid,r_int,r_blk)
    profile.update(profile_id='corrected_dasatom_legacy_geometry.v2',
        source='Pinned legacy gate geometry; minimum continuous clearance and cross-trap plane geometry remain unresolved')
    profile['assumptions']=['Explicit batch load/move/unload reconstruction; physical minimum separation is not supplied by native logs']
    origin={**(origin or {}),'kind':'dasatom_corrected_v2','original_register_complete':True,
        'effective_qubits':declared_n,'input_declared_qubits':declared_n,'register_scope':'full_declared_CZ_only'}
    trace=build_trace(groups,circuit,profile,origin,timing='two_transfer_stages')
    trace['metadata'].update(expected_final_positions={f'a{q}':p for q,p in enumerate(embeddings[-1])},
        correction_policy='vacant_destinations_waypoints_and_idle_register.v2',
        register_repair={'original_native_qubits':original_n,'declared_qubits':declared_n,'restored_idle_qubits':declared_n-original_n},
        transition_reports=reports,corrected_control_not_native_measurement=True,
        original_active_embeddings_preserved=True)
    for event in trace['events']:
        if event['kind'] in ['move','initialize']:event['provenance']['positions']='native_or_explicitly_corrected; see transition_reports/register_repair'
    corrected={**copy.deepcopy(native),'embeddings':embeddings,'movement_list':corrected_movements,
        'actual_grid':grid,'variant':'dasatom_corrected_v2'}
    return trace,corrected
