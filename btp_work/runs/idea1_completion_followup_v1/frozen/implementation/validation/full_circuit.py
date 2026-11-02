"""Explicit logical-gate restoration and independent physical-slot simulation.

Native CZ logs are unchanged. This sidecar restores omitted one-qubit gates
from the full CZ-basis precursor, preserving each wire's original dependencies.
Transport permutations are bookkeeping, never charged as physical SWAP gates.
"""
from collections import defaultdict, deque
import hashlib
import math
from pathlib import Path


def full_operations(circuit, normalized):
    """Match precursor CZ occurrences and build original per-qubit queues."""
    operations=[];queues=defaultdict(deque);pairs=[]
    for instruction in circuit.data:
        name=instruction.operation.name
        qubits=[circuit.find_bit(q).index for q in instruction.qubits]
        if instruction.clbits or name not in ['cz','h','s','t','rx','ry','rz']:
            raise ValueError('Unsupported full-circuit operation: '+name)
        operation={'operation_id':f'o{len(operations):06}','name':name,'qubits':qubits,
            'parameters':[float(p) for p in instruction.operation.params]}
        if name=='cz':
            gate=normalized['gates'][len(pairs)] if len(pairs)<len(normalized['gates']) else None
            if gate is None or set(gate['qubits'])!=set(qubits):
                raise ValueError('Full precursor CZ skeleton differs from frozen normalized input')
            operation['gate_id']=gate['gate_id'];pairs.append(qubits)
        elif len(qubits)!=1:
            raise ValueError('Unexpected operation arity')
        operations.append(operation)
        for q in qubits:queues[q].append(operation)
    if len(pairs)!=len(normalized['gates']):raise ValueError('Missing precursor CZ')
    return operations,queues


def restore_operations(trace, precursor):
    """Emit full operations on current sorted occupied physical slots."""
    n=trace['metadata']['circuit']['num_qubits']
    if precursor.num_qubits!=n:raise ValueError('Full original register not represented by native trace')
    source_ops,queues=full_operations(precursor,trace['metadata']['circuit'])
    positions={};carriers={};output=[];done=set();initialized=False
    def ordered():return sorted(positions,key=lambda a:(positions[a],a))
    def emit(operation,event_id):
        if operation['operation_id'] in done:raise ValueError('Repeated restored operation')
        slots=ordered();logical_to_atom={q:a for a,q in carriers.items()}
        atoms=[logical_to_atom[q] for q in operation['qubits']]
        output.append({**operation,'kind':'logical_gate','physical_slots':[slots.index(a) for a in atoms],
            'atom_ids':atoms,'sites':[list(positions[a]) for a in atoms],
            'native_event_id':event_id,
            'provenance':'native_CZ_identity' if operation['name']=='cz' else 'restored_from_original_precursor'})
        done.add(operation['operation_id'])
        for q in operation['qubits']:
            if not queues[q] or queues[q][0]['operation_id']!=operation['operation_id']:raise ValueError('Original dependency inversion')
            queues[q].popleft()
    def singles(q,event_id):
        while queues[q] and queues[q][0]['name']!='cz':emit(queues[q][0],event_id)
    for event in trace['events']:
        if event['kind']=='initialize':
            if initialized:raise ValueError('Repeated initialization')
            initialized=True
            positions=dict(zip(event['atom_ids'],map(tuple,event['to_sites'])))
            carriers=dict(zip(event['atom_ids'],event['logical_qubit_ids']))
            slots=ordered()
            if set(carriers.values())!=set(range(n)):raise ValueError('Incomplete logical map')
            output.append({'kind':'transport_permutation','new_slot_to_old_slot':[carriers[a] for a in slots],
                'native_event_id':event['event_id'],'provenance':'initial_physical_slot_basis'})
        elif event['kind']=='move':
            before=ordered()
            for a,p,q in zip(event['atom_ids'],event['from_sites'],event['to_sites']):
                if positions.get(a)!=tuple(p):raise ValueError('Movement source mismatch')
                positions[a]=tuple(q)
            after=ordered()
            output.append({'kind':'transport_permutation','new_slot_to_old_slot':[before.index(a) for a in after],
                'native_event_id':event['event_id'],'provenance':'transport_of_stable_carriers'})
        elif event['kind']=='gate':
            if event.get('gate_type')!='cz':raise ValueError('Native scope must be CZ-only')
            operands=[carriers[a] for a in event['atom_ids']]
            if operands!=event['logical_qubit_ids']:raise ValueError('Native carrier/logical mismatch')
            for q in operands:singles(q,event['event_id'])
            heads=[queues[q][0] if queues[q] else None for q in operands]
            if any(h is None or h.get('gate_id')!=event['gate_id'] or h['name']!='cz' for h in heads):
                raise ValueError('Native CZ cannot satisfy full original dependencies')
            emit(heads[0],event['event_id'])
        elif event['kind'] not in ['transfer','wait']:
            raise ValueError('Unsupported native event for semantic restoration')
    if not initialized:raise ValueError('Missing initialization')
    for q in range(n):singles(q,'after_native_trace')
    if any(queues[q] for q in range(n)) or len(done)!=len(source_ops):raise ValueError('Incomplete full-circuit restoration')
    output.append({'kind':'transport_permutation','new_slot_to_old_slot':[ordered().index(next(a for a in carriers if carriers[a]==q)) for q in range(n)],
        'native_event_id':'logical_output_basis','provenance':'explicit_final_permutation_undo'})
    return output


def simulate(operations,n,global_phase=0.0):
    """NumPy basis-column simulator; no Qiskit compiled-circuit simulator used."""
    import numpy as np
    state=np.eye(1<<n,dtype=complex)
    basis=np.arange(1<<n)
    for operation in operations:
        if operation['kind']=='transport_permutation':
            permutation=operation['new_slot_to_old_slot']
            if sorted(permutation)!=list(range(n)):raise ValueError('Invalid transport permutation')
            new_indices=np.zeros(1<<n,dtype=int)
            for new,old in enumerate(permutation):new_indices|=((basis>>old)&1)<<new
            target=np.empty_like(state);target[new_indices,:]=state;state=target;continue
        qubits=operation['physical_slots'];name=operation['name'];params=operation['parameters']
        if name=='cz':
            selected=(((basis>>qubits[0])&1)&((basis>>qubits[1])&1)).astype(bool)
            state[selected,:]*=-1;continue
        angle=params[0] if params else 0.0;c=math.cos(angle/2);s=math.sin(angle/2)
        matrix={'h':np.array([[1,1],[1,-1]])/math.sqrt(2),
            's':np.diag([1,1j]),'t':np.diag([1,np.exp(1j*math.pi/4)]),
            'rx':np.array([[c,-1j*s],[-1j*s,c]]),
            'ry':np.array([[c,-s],[s,c]]),
            'rz':np.diag([np.exp(-1j*angle/2),np.exp(1j*angle/2)])}[name]
        q=qubits[0];zero=basis[((basis>>q)&1)==0];one=zero|(1<<q)
        a=state[zero,:].copy();b=state[one,:].copy()
        state[zero,:]=matrix[0,0]*a+matrix[0,1]*b
        state[one,:]=matrix[1,0]*a+matrix[1,1]*b
    return state*complex(math.cos(global_phase),math.sin(global_phase))


def compare_matrices(expected,actual,tolerance=1e-9):
    import numpy as np
    overlap=np.vdot(expected,actual)
    phase=overlap/abs(overlap) if abs(overlap)>1e-15 else 1
    error=float(np.max(np.abs(actual-phase*expected)))
    return {'equivalent_up_to_global_phase':error<=tolerance,'maximum_absolute_error':error,
        'tolerance':tolerance,'global_phase_relative':float(np.angle(phase))}


def verify_original(trace,original_path,max_qubits=8):
    """Returns an explicitly reconstructed logical realization and proof result."""
    from qiskit import QuantumCircuit,transpile,qasm2
    from qiskit.quantum_info import Operator
    original_path=Path(original_path)
    raw=QuantumCircuit.from_qasm_file(str(original_path))
    if raw.num_qubits>max_qubits:raise ValueError('Exhaustive unitary limit exceeded')
    precursor=transpile(raw,basis_gates=['cz','h','s','t','rx','ry','rz'],optimization_level=0,seed_transpiler=42)
    operations=restore_operations(trace,precursor)
    compiled=simulate(operations,raw.num_qubits,float(precursor.global_phase))
    reference=Operator(raw).data
    comparison=compare_matrices(reference,compiled)
    comparison.update(format='original_circuit_check.v1',num_qubits=raw.num_qubits,basis_states=1<<raw.num_qubits,
        full_original_circuit_checked=True,semantic_scope='original_QASM_with_explicit_one_qubit_restoration',
        native_one_qubit_output_present=False,restoration_is_schedule_transformation=True,
        physical_validity_implied=False,original_sha256=hashlib.sha256(original_path.read_bytes()).hexdigest(),
        original_operation_count=len(raw.data),restored_operation_count=sum(o['kind']=='logical_gate' for o in operations),
        reference_engine='Qiskit Operator(original QASM)',compiled_engine='independent NumPy physical-slot basis simulation')
    return {'comparison':comparison,'operations':operations,'transpiled_full_qasm':qasm2.dumps(precursor)}
