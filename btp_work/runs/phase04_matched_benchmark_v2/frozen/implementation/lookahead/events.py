"""NEW Phase04 sparse future-event index. No placement or planner imports."""
from bisect import bisect_left
from collections import defaultdict,deque
from dataclasses import dataclass


@dataclass(frozen=True,slots=True)
class FutureEvent:
    gate_id:str
    partner:int
    logical_layer:int


class FutureEventIndex:
    def __init__(self,schedule,num_qubits,circuit=None):
        if type(num_qubits) is not int or num_qubits<0:raise ValueError('Invalid register')
        self.num_qubits=num_qubits;self.layer_count=len(schedule);self.layer_by_name={};self.gate_by_key={};self.gate_layer={};self.prefix_counts=[]
        by_q=[[] for _ in range(num_qubits)];queues=defaultdict(deque);count=0
        if circuit is not None:
            if circuit['num_qubits']!=num_qubits:raise ValueError('Register mismatch')
            seen=set()
            for gate in circuit['gates']:
                if gate['gate_type']!='cz' or gate['gate_id'] in seen:raise ValueError('Invalid normalized gate identity')
                seen.add(gate['gate_id']);queues[tuple(sorted(gate['qubits']))].append(gate['gate_id'])
        for layer,(name,pairs) in enumerate(schedule):
            if name in self.layer_by_name:raise ValueError('Duplicate layer name')
            self.layer_by_name[name]=layer;self.prefix_counts.append(count);used=set()
            for pair in pairs:
                if len(pair)!=2 or any(type(q) is not int or q<0 or q>=num_qubits for q in pair) or pair[0]==pair[1]:raise ValueError('Invalid pair')
                a,b=pair
                if a in used or b in used:raise ValueError('Layer must be a matching; serialize dependencies first')
                used.update(pair);key=tuple(sorted(pair))
                if circuit is None:gid=f'g{count:06}'
                else:
                    if not queues[key]:raise ValueError('Schedule gate absent from circuit')
                    gid=queues[key].popleft()
                self.gate_by_key[(layer,key)]=gid;self.gate_layer[gid]=layer
                by_q[a].append(FutureEvent(gid,b,layer));by_q[b].append(FutureEvent(gid,a,layer));count+=1
        if any(queues.values()):raise ValueError('Circuit gates absent from schedule')
        self.prefix_counts.append(count);self.gate_count=count
        self.events_by_qubit=tuple(tuple(items) for items in by_q)
        self.layers_by_qubit=tuple(tuple(e.logical_layer for e in items) for items in by_q)

    def gate_id(self,layer,pair):
        return self.gate_by_key[(layer,tuple(sorted(pair)))]

    def query(self,qubit,logical_layer,h,*,completed=frozenset(),active=frozenset()):
        if type(h) is not int or h<1:raise ValueError('h must be positive')
        if type(qubit) is not int or not 0<=qubit<self.num_qubits:raise ValueError('Unknown qubit')
        if type(logical_layer) is not int or not 0<=logical_layer<=self.layer_count:raise ValueError('Unknown layer')
        items=self.events_by_qubit[qubit];start=bisect_left(self.layers_by_qubit[qubit],logical_layer);out=[]
        for index in range(start,len(items)):
            event=items[index]
            if event.gate_id in completed or event.gate_id in active:continue
            out.append({'gate_id':event.gate_id,'partner':event.partner,'logical_layer':event.logical_layer,
                        'logical_layer_delta':event.logical_layer-logical_layer})
            if len(out)==h:break
        return out