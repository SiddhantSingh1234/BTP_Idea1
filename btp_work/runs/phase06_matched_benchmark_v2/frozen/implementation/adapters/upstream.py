"""Adapt RFT logs and native DasAtom arrays without changing planning choices."""
from __future__ import annotations
import ast
from collections import defaultdict,deque
import hashlib
import json
import math
from pathlib import Path
import re
from implementation.trace.model import SCHEMA_VERSION,circuit_from_pairs,evidence_profile,fingerprint,read_cz_qasm


def rft_groups(text):
    groups=[];diagnostics=[];current=None;layer=None;placement=None
    def flush():
        nonlocal current
        if current is not None:
            groups.append(current)
        current=None
    for number,line in enumerate(text.splitlines(),1):
        stripped=line.strip()
        if not stripped: continue
        if 'ERROR' in stripped:
            diagnostics.append({'code':'upstream_error','line':number,'text':stripped});continue
        if stripped.startswith('--- Processing'):
            flush()
            m=re.search(r'Time\s+(\d+)',stripped)
            layer=int(m[1]) if m else None
            m=re.search(r'Batch\s+(\d+)',stripped)
            placement=f'layer{layer}_batch{m[1] if m else 1}'
            continue
        if stripped.startswith('--- Batch Separator'):
            flush();continue
        kind=next((k for token,k in [('[INITIAL PLACEMENT]','initialize'),('[SHUTTLING]','move'),('[EXECUTE','gate')] if stripped.startswith(token)),None)
        if kind:
            flush();current={'kind':kind,'items':[],'logical_layer':layer,'placement_batch':placement,'source_line':number};continue
        if stripped=='No shuttling required.' or stripped.startswith('No two-qubit'):
            continue
        if stripped.startswith('[LAYOUT_SLOTS:'):
            continue
        place=re.fullmatch(r'PLACE(?: active| idle)? qubit (\d+) at position (\([^)]*\))',stripped)
        move=re.fullmatch(r'SHUTTLE qubit (\d+) from (\([^)]*\)) to (\([^)]*\))(?: \(to break cycle\))?',stripped)
        gate=re.fullmatch(r'CZ q\[(\d+)\],\s*q\[(\d+)\](?: \(at locations (\([^)]*\)), (\([^)]*\))\))?',stripped)
        if current and current['kind']=='initialize' and place:
            current['items'].append({'qubit':int(place[1]),'site':ast.literal_eval(place[2])});continue
        if current and current['kind']=='move' and move:
            current['items'].append({'qubit':int(move[1]),'from':ast.literal_eval(move[2]),'to':ast.literal_eval(move[3]),
                'cause':'cycle_break' if 'to break cycle' in stripped else 'unknown_upstream_move'});continue
        if current and current['kind']=='gate' and gate:
            current['items'].append({'qubits':[int(gate[1]),int(gate[2])],
                'sites':[ast.literal_eval(gate[3]),ast.literal_eval(gate[4])] if gate[3] else None});continue
        diagnostics.append({'code':'unknown_log_format','line':number,'text':stripped})
    flush()
    return groups,diagnostics


def dasatom_groups(native):
    embeddings=native['embeddings'];groups=[]
    if len(native['gate_groups'])!=len(embeddings) or len(native['movement_list'])!=max(0,len(embeddings)-1):
        raise ValueError('Native partition/group/transition array lengths disagree')
    if embeddings and any(len(e)!=len(embeddings[0]) for e in embeddings):
        raise ValueError('Native embeddings change atom population')
    if embeddings:
        groups.append({'kind':'initialize','items':[{'qubit':q,'site':p} for q,p in enumerate(embeddings[0])],
            'placement_batch':'initial','logical_layer':None})
    for i,embedding in enumerate(embeddings):
        for j,pairs in enumerate(native['gate_groups'][i]):
            groups.append({'kind':'gate','items':[{'qubits':[int(a),int(b)],'sites':[embedding[a],embedding[b]]} for a,b in pairs],
                'placement_batch':f'partition{i}_group{j}','logical_layer':None})
        if i<len(native['movement_list']):
            for j,moves in enumerate(native['movement_list'][i]):
                groups.append({'kind':'move','items':[{'qubit':int(q),'from':a,'to':b,'cause':'unknown_upstream_move'} for q,a,b in moves],
                    'placement_batch':f'transition{i}_to{i+1}','logical_layer':None})
    return groups,[]


def build_trace(groups,circuit,profile,origin=None,timing='evidence',diagnostics=None):
    if timing not in ['evidence','two_transfer_stages']:
        raise ValueError('Unknown timing reconstruction policy')
    metadata={'schema_version':SCHEMA_VERSION,'circuit':circuit,'circuit_sha256':fingerprint(circuit),
        'hardware':profile,'hardware_sha256':fingerprint(profile),'origin':origin or {'kind':'synthetic_fixture'},
        'timing_policy':timing,'diagnostics':diagnostics or [],
        'atom_identity_policy':'One stable atom carrier per source logical qubit; no SWAP/cooling state transfer in native CZ-only scope',
        'physical_evidence_complete':False,
        'assumptions':(['SLM-to-AOD-to-SLM for nonzero movers; one concurrent load and unload stage per batch',
            'Shared normalized linear progress; times derived from declared profile, not observed'] if timing!='evidence' else
            ['Native logs do not expose trap transfers, physical timing or trajectories'])}
    events=[];clock=0.0;routing=0
    gate_queues=defaultdict(deque)
    for gate in circuit['gates']:
        gate_queues[tuple(sorted(gate['qubits']))].append(gate)
    def event(kind,**kw):
        e={'event_id':f'e{len(events):06}','kind':kind,'logical_layer':None,'placement_batch':None,'routing_batch':None,
            'start_us':None,'duration_us':None,'resources':[],'atom_ids':[],'logical_qubit_ids':[],
            'provenance':{'positions':'observed_or_explicit_fixture','timing':'unobserved'}}
        e.update(kw);events.append(e);return e
    for index,group in enumerate(groups):
        kind,items=group['kind'],group['items']
        common={'logical_layer':group.get('logical_layer'),'placement_batch':group.get('placement_batch'),
                'source_group_index':index}
        if kind=='initialize':
            qs=[i['qubit'] for i in items]
            event('initialize',**common,atom_ids=[f'a{q}' for q in qs],logical_qubit_ids=qs,
                to_sites=[list(i['site']) for i in items],trap_to='SLM' if timing!='evidence' else 'unknown',
                start_us=0.0,duration_us=0.0,provenance={'positions':'observed_or_explicit_fixture','trap':'assumed' if timing!='evidence' else 'unobserved','timing':'initial_loading_excluded'})
        elif kind=='move' and items:
            routing+=1;batch=f'move{routing:06}';qs=[i['qubit'] for i in items]
            movers=[i for i in items if tuple(i['from'])!=tuple(i['to'])]
            moving_qs=[i['qubit'] for i in movers]
            assumed=timing!='evidence'
            if assumed and movers:
                duration=profile['transfer_stage_duration_us']
                event('transfer',**common,routing_batch=batch,atom_ids=[f'a{q}' for q in moving_qs],logical_qubit_ids=moving_qs,
                    trap_from='SLM',trap_to='AOD0',start_us=clock,duration_us=duration,resources=['AOD0'],
                    provenance={'transfer':'inferred_by_two_transfer_stage_policy','timing':'derived'})
                clock+=duration
            distance=max(math.dist(i['from'],i['to'])*profile['spacing_um'] for i in items)
            duration=distance/profile['move_speed_um_per_us'] if assumed else None
            event('move',**common,routing_batch=batch,atom_ids=[f'a{q}' for q in qs],logical_qubit_ids=qs,
                from_sites=[list(i['from']) for i in items],to_sites=[list(i['to']) for i in items],
                start_us=clock if assumed else None,duration_us=duration,resources=['AOD0'],
                trajectory={'kind':'shared_linear_progress','provenance':'assumed'} if assumed else None,
                causes=[i.get('cause','unknown') for i in items],source_legacy_block=True,
                provenance={'positions':'observed_or_explicit_fixture','trajectory':'assumed' if assumed else 'unobserved','timing':'derived' if assumed else 'unobserved'})
            if assumed:
                clock+=duration
                if movers:
                    duration=profile['transfer_stage_duration_us']
                    event('transfer',**common,routing_batch=batch,atom_ids=[f'a{q}' for q in moving_qs],logical_qubit_ids=moving_qs,
                        trap_from='AOD0',trap_to='SLM',start_us=clock,duration_us=duration,resources=['AOD0'],
                        provenance={'transfer':'inferred_by_two_transfer_stage_policy','timing':'derived'})
                    clock+=duration
        elif kind=='gate':
            for item in items:
                pair=tuple(sorted(item['qubits']))
                expected=gate_queues[pair].popleft() if gate_queues[pair] else None
                event('gate',**{**common,'logical_layer':expected['logical_layer'] if expected else group.get('logical_layer')},
                    gate_batch=f'gate_stage{index:06}',gate_id=expected['gate_id'] if expected else f'unmatched_{len(events)}',
                    gate_type='cz',dependencies=expected['dependencies'] if expected else [],
                    atom_ids=[f'a{q}' for q in item['qubits']],logical_qubit_ids=item['qubits'],sites=item.get('sites'),
                    start_us=clock if timing!='evidence' else None,
                    duration_us=profile['cz_duration_us'] if timing!='evidence' else None,
                    resources=[],provenance={'gate':'observed','gate_identity':'FIFO_occurrence_for_same_CZ_pair',
                        'timing':'derived' if timing!='evidence' else 'unobserved'})
            if timing!='evidence' and items:
                clock+=profile['cz_duration_us']
    metadata['source_counts']={'gate_stages':sum(g['kind']=='gate' for g in groups),
        'nonempty_movement_blocks':sum(g['kind']=='move' and bool(g['items']) for g in groups)}
    return {'metadata':metadata,'events':events}


def adapt_run(directory,algorithm,timing='evidence',profile=None):
    directory=Path(directory)
    result=json.loads((directory/'result.json').read_text(encoding='utf-8'))
    if result.get('algorithm')!=algorithm:
        raise ValueError('Requested adapter does not match run algorithm')
    normalized=directory/'normalized.qasm'
    circuit=read_cz_qasm(normalized)
    declared=circuit['num_qubits']
    geometry=result.get('geometry',{'rows':11,'r_int':2,'r_blk':4})
    profile=profile or evidence_profile(geometry['rows'],geometry['r_int'],geometry['r_blk'])
    files=[directory/'result.json',normalized]
    final=None
    if algorithm=='rft':
        path=directory/'instructions.txt';files.append(path)
        groups,diagnostics=rft_groups(path.read_text(encoding='utf-8'))
    elif algorithm=='dasatom':
        path=directory/'native_dasatom.json';files.append(path)
        native=json.loads(path.read_text(encoding='utf-8'))
        n=len(native['embeddings'][0]) if native['embeddings'] else 0
        circuit=circuit_from_pairs(n,[g['qubits'] for g in circuit['gates']])
        groups,diagnostics=dasatom_groups(native)
        if native['embeddings']:
            final={f'a{i}':site for i,site in enumerate(native['embeddings'][-1])}
    else:
        raise ValueError('Unknown source algorithm')
    origin={'kind':algorithm,'upstream_status':result['status'],
        'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'compiler_config':{k:result.get(k) for k in ['options','seed','hash_seed','threads','geometry','register_policy','routing_seed']},
        'source_files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
        'rft_revision':result.get('rft_revision'),'dasatom_revision':result.get('dasatom_revision'),
        'input_declared_qubits':result.get('input_declared_qubits',declared),
        'normalized_declared_qubits':declared,'effective_qubits':circuit['num_qubits'],
        'original_register_complete':result.get('input_declared_qubits',declared)==circuit['num_qubits'],
        'register_scope':'source_native_CZ_only','module_providers':result.get('module_providers',{})}
    trace=build_trace(groups,circuit,profile,origin,timing,diagnostics)
    trace['metadata']['expected_final_positions']=final
    trace['metadata']['legacy_scored_qubits']=circuit['num_qubits'] if algorithm=='dasatom' else result.get('num_qubits',circuit['num_qubits'])
    trace['metadata']['legacy_scored_CZ']=result.get('native_metrics',{}).get('Num CZ Gates',len(circuit['gates']))
    return trace
