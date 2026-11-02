"""Trace v1 helpers. Coordinates are grid indices; explicit spacing converts um."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

SCHEMA_VERSION = "neutral_atom_trace.v1"


def fingerprint(value):
    data=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def circuit_from_pairs(n, pairs):
    last, depths, gates = {}, {}, []
    for i,pair in enumerate(pairs):
        a,b=map(int,pair)
        if a==b or min(a,b)<0 or max(a,b)>=n:
            raise ValueError('Invalid CZ operands')
        dependencies=sorted({last[q] for q in [a,b] if q in last})
        layer=1+max([depths[q] for q in [a,b] if q in depths] or [0])
        gate={'gate_id':f'g{i:06}','gate_type':'cz','qubits':[a,b],
              'dependencies':dependencies,'logical_layer':layer}
        gates.append(gate)
        for q in [a,b]:
            last[q],depths[q]=gate['gate_id'],layer
    return {'format':'cz_circuit.v1','num_qubits':int(n),'gates':gates}


def read_cz_qasm(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    text=re.sub(r'//[^\n]*','',text)
    registers=[];pairs=[]
    for statement in text.split(';'):
        statement=statement.strip()
        if not statement or statement=='OPENQASM 2.0' or statement=='include "qelib1.inc"':
            continue
        m=re.fullmatch(r'qreg\s+(\w+)\[(\d+)\]',statement)
        if m:
            registers.append((m[1],int(m[2])));continue
        m=re.fullmatch(r'cz\s+(\w+)\[(\d+)\]\s*,\s*(\w+)\[(\d+)\]',statement)
        if m and len(registers)==1 and m[1]==m[3]==registers[0][0]:
            pairs.append((int(m[2]),int(m[4])));continue
        raise ValueError('Unsupported normalized QASM statement: '+statement)
    if len(registers)>1:
        raise ValueError('Only one normalized quantum register is supported')
    return circuit_from_pairs(registers[0][1] if registers else 0,pairs)


def evidence_profile(grid=11,r_int=2,r_blk=4):
    return {'profile_id':'legacy_geometry_evidence.v1','rows':grid,'columns':grid,
        'coordinate_unit':'grid_index','spacing_um':3.0,
        'interaction_radius_um':r_int*3.0,'restriction_radius_um':r_blk*3.0,
        'min_atom_separation_um':None,'slm_aod_shared_plane':None,
        'addressing':'individual','aod_count':1,'cooling_supported':False,
        'cz_duration_us':0.2,'transfer_stage_duration_us':20.0,'move_speed_um_per_us':0.55,
        'gates_require_trap':'SLM','allow_move_gate_overlap':False,'coordinate_tolerance':1e-9,
        'legacy_T2_us':1.5e6,'legacy_f_cz':0.995,'legacy_f_transfer':1.0,
        'assumptions':['Physical minimum separation and cross-plane geometry not established by native logs'],
        'source':'Pinned RFT/DasAtom legacy constants; no new heating/cooling/acceleration model'}


def save_trace(directory, trace):
    directory=Path(directory)
    if directory.exists():
        raise FileExistsError('Trace output directory already exists')
    directory.mkdir(parents=True)
    metadata=dict(trace['metadata'])
    payload=''.join(json.dumps(e,sort_keys=True,allow_nan=False)+'\n' for e in trace['events'])
    metadata['events_sha256']=hashlib.sha256(payload.encode()).hexdigest()
    (directory/'events.jsonl').write_text(payload,encoding='utf-8',newline='\n')
    (directory/'metadata.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def load_trace(directory):
    directory=Path(directory)
    metadata=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
    payload=(directory/'events.jsonl').read_bytes()
    if hashlib.sha256(payload).hexdigest()!=metadata.get('events_sha256'):
        raise ValueError('Trace event checksum mismatch')
    events=[json.loads(line) for line in payload.decode().splitlines() if line.strip()]
    return {'metadata':metadata,'events':events}
