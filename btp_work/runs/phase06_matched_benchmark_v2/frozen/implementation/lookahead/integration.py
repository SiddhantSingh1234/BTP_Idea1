"""NEW Phase04 checked parking hooks over an isolated immutable pinned core.

No source file is patched, no global module used by the live worker is modified.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib,itertools,math,random,sys,time,types
from pathlib import Path
from implementation.lookahead.events import FutureEventIndex
from implementation.lookahead.potential import validate_options,FuturePotential

ROOT=Path(__file__).resolve().parents[2]
CORE=ROOT/'vendor/NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a/src/compiler_core.py'
CORE_SHA256='24651482cf223c1a84d0aeecb1493ee2024e25c2da9bebd37d035023e3ff71bb'
_serial=itertools.count()


def reachable_bytes(value):
    """Measured Python reachable graph size; shared referents counted once, not RSS."""
    seen=set();stack=[value];total=0
    while stack:
        obj=stack.pop();identity=id(obj)
        if identity in seen:continue
        seen.add(identity);total+=sys.getsizeof(obj)
        if isinstance(obj,dict):stack.extend(obj.keys());stack.extend(obj.values())
        elif isinstance(obj,(tuple,list,set,frozenset)):stack.extend(obj)
        elif hasattr(obj,'__dict__'):stack.append(vars(obj))
        else:
            for field in getattr(type(obj),'__slots__',()):
                if hasattr(obj,field):stack.append(getattr(obj,field))
    return total


class LookaheadContext:
    def __init__(self,schedule,n,circuit,config,spacing_um=3.0):
        self.config=validate_options(config);self.policy=self.config['lookahead_policy'];self.spacing_um=spacing_um
        t=time.perf_counter();self.index=FutureEventIndex(schedule,n,circuit);self.build_seconds=time.perf_counter()-t
        self.completed=set();self.active=frozenset();self.layer=-1;self.snapshot={};self.active_targets={};self.decisions=[];self.batches=[]
        self.query_seconds=0.0;self.query_count=0;self.potential_seconds=0.0;self.legacy_build_seconds=0.0;self.legacy_table_bytes=0
        self.index_bytes=reachable_bytes(self.index);self.original_pick=None

    def begin_layer(self,name):
        layer=self.index.layer_by_name[name]
        if layer<=self.layer or self.active or len(self.completed)!=self.index.prefix_counts[layer]:raise ValueError('Unconsumed predecessor layer or invalid layer transition')
        self.layer=layer

    def begin_batch(self,active_pairs_to_map,finished_batch_indices,current_positions,active_targets):
        if self.active:raise ValueError('Previous batch not complete')
        if len(set(finished_batch_indices))!=len(finished_batch_indices):raise ValueError('Duplicate active gate')
        self.active=frozenset(self.index.gate_id(self.layer,active_pairs_to_map[i]) for i in finished_batch_indices)
        if self.active&self.completed:raise ValueError('Gate already consumed')
        self.snapshot={q:tuple(pos) for q,pos in current_positions.items()}
        self.active_targets={q:tuple(pos) for q,pos in active_targets.items()};self.snapshot.update(self.active_targets)
        self.batches.append({'logical_layer':self.layer,'active_gate_ids':sorted(self.active),'completed_count':len(self.completed),
                             'current_positions':{str(q):list(p) for q,p in current_positions.items()},
                             'committed_active_targets':{str(q):list(p) for q,p in self.active_targets.items()}})

    def complete_batch(self,pairs):
        got={self.index.gate_id(self.layer,pair) for pair in pairs}
        if got!=set(self.active) or got&self.completed:raise ValueError('Completion differs from committed active batch')
        self.completed.update(got);self.active=frozenset()

    def pick(self,**kwargs):
        q=kwargs['qubit'];available=kwargs['available_positions'];evicted=kwargs['is_evicted'];t=time.perf_counter()
        if self.policy=='legacy_exact':
            chosen=self.original_pick(**kwargs)
            self.potential_seconds+=time.perf_counter()-t
            self.decisions.append({'policy':'legacy_exact','logical_layer':self.layer,'qubit':q,'is_evicted':evicted,
                                   'chosen_site':list(chosen) if chosen is not None else None,'candidate_count':len(available),
                                   'delegates_original_picker':True,'completed_gate_ids':sorted(self.completed),'active_gate_ids':sorted(self.active)})
            return chosen
        t0=time.perf_counter();events=self.index.query(q,self.layer,self.config['h'],completed=self.completed,active=self.active)
        self.query_seconds+=time.perf_counter()-t0;self.query_count+=1
        potential=FuturePotential.from_events(events,self.snapshot,gamma=self.config['gamma'],spacing_um=self.spacing_um)
        chosen,candidates=potential.choose(available,kwargs['center_of_mass'])
        self.potential_seconds+=time.perf_counter()-t
        self.decisions.append({'policy':'next_events','logical_layer':self.layer,'qubit':q,'is_evicted':evicted,
                               'chosen_site':list(chosen) if chosen is not None else None,'candidate_count':len(available),
                               'events':events,'resolved_anchors':[{'gate_id':gid,'partner':partner,'delta':delta,'site':list(anchor),
                                                                  'origin':'committed_active' if partner in self.active_targets else 'current'}
                                                                 for gid,partner,delta,anchor in potential.resolved],
                               'missing_anchor_gate_ids':list(potential.missing_gate_ids),'fallback':not bool(potential.resolved),
                               'candidate_scores':candidates,'completed_gate_ids':sorted(self.completed),'active_gate_ids':sorted(self.active)})
        return chosen

    def statistics(self):
        return {'event_index_build_seconds':self.build_seconds,'event_index_reachable_bytes':self.index_bytes,
                'legacy_RFT_build_seconds':self.legacy_build_seconds,'legacy_RFT_reachable_bytes':self.legacy_table_bytes,
                'query_count':self.query_count,'query_seconds_total':self.query_seconds,'parking_seconds_total_including_queries':self.potential_seconds,
                'parking_calls':len(self.decisions),'eviction_calls':sum(d['is_evicted'] for d in self.decisions),
                'missing_anchor_events':sum(len(d.get('missing_anchor_gate_ids',[])) for d in self.decisions),
                'completed_gate_count':len(self.completed),'gate_count':self.index.gate_count,
                'no_future_chosen_positions_accessed':True,'table_size_definition':'sys.getsizeof of reachable Python index graph, shared objects once; not RSS'}


def load_core(context=None):
    raw=CORE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CORE_SHA256:raise ValueError('Pinned core identity changed')
    source=raw.decode('utf-8');patch_log=[]
    def replace_once(old,new,label):
        nonlocal source
        if source.count(old)!=1:raise ValueError('Hook anchor changed: '+label)
        source=source.replace(old,new);patch_log.append(label)
    if context is not None:
        replace_once('        # Get right-filled info for this timestamp',
                     '        phase04_context.begin_layer(timestamp_name)\n        # Get right-filled info for this timestamp','layer_entry')
        replace_once('            final_target_positions.update(active_qubit_targets)',
                     '            final_target_positions.update(active_qubit_targets)\n            phase04_context.begin_batch(active_pairs_to_map, finished_batch_indices, current_qubit_positions, active_qubit_targets)','committed_batch_snapshot')
        replace_once('            # Remove executed pairs from pending',
                     '            phase04_context.complete_batch(executed_pairs)\n            # Remove executed pairs from pending','batch_completion')
        replace_once('right_filled_table = build_right_filled_table(schedule, num_qubits)',
                     "right_filled_table = build_right_filled_table(schedule, num_qubits) if phase04_context.policy == 'legacy_exact' else None",'legacy_table_only_for_legacy')
    name=f'_btp_phase04_core_{next(_serial)}';module=types.ModuleType(name);module.__file__=str(CORE);sys.modules[name]=module
    module.phase04_context=context
    exec(compile(source,str(CORE)+('.phase04_hooks' if context else ''),'exec'),module.__dict__)
    if context is not None:
        context.original_pick=module._pick_idle_position;module._pick_idle_position=context.pick
        original_builder=module.build_right_filled_table
        def measured_legacy_builder(*args,**kwargs):
            t=time.perf_counter();table=original_builder(*args,**kwargs);context.legacy_build_seconds+=time.perf_counter()-t
            context.legacy_table_bytes=reachable_bytes(table);return table
        module.build_right_filled_table=measured_legacy_builder
    module.phase04_hook_log=patch_log;module.phase04_loaded_sha256=hashlib.sha256(source.encode()).hexdigest()
    return module


def compile_schedule(schedule,num_qubits,layout,geometry,baseline_options,config,*,circuit=None,routing_seed=42):
    if baseline_options.get('enable_rft_hungarian_bias',False):raise ValueError('Phase04 holds assignment future bias disabled')
    if baseline_options.get('idle_parking_mode','rft_greedy')!='rft_greedy':raise ValueError('Selected RFT parking baseline required')
    if any(v<1 for v in (geometry['rows'],geometry['columns'])):raise ValueError('Invalid grid')
    schedule=[(name,[tuple(pair) for pair in pairs]) for name,pairs in schedule]
    context=LookaheadContext(schedule,num_qubits,circuit,config,geometry.get('spacing_um',3.0));module=load_core(context)
    options=module.CompilerOptions(**baseline_options);slots=[[tuple(p) for p in slot] for slot in layout]
    busiest=module.find_busiest_pairs(schedule);canonical=module.create_initial_mapping(busiest,slots)
    random.seed(routing_seed);state_before=hashlib.sha256(repr(random.getstate()).encode()).hexdigest();t=time.perf_counter()
    instructions=module.generate_hardware_instructions(schedule,canonical,busiest,num_qubits,geometry['rows'],geometry['columns'],slots,
                                                         geometry['r_blk'],geometry['r_int'],options=options)
    seconds=time.perf_counter()-t
    if len(context.completed)!=context.index.gate_count:raise ValueError('Compiler did not complete the requested gate set')
    text='\n'.join(instructions)+'\n'
    return {'instructions':text,'decisions':context.decisions,'batches':context.batches,'statistics':context.statistics(),
            'planner_seconds':seconds,'core_sha256':CORE_SHA256,'hooked_source_sha256':module.phase04_loaded_sha256,'hooks':module.phase04_hook_log,
            'routing_seed':routing_seed,'random_state_before_sha256':state_before,
            'random_state_after_sha256':hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),
            'baseline_options':asdict(options),'lookahead_options':dict(config)}


def direct_source_control(schedule,num_qubits,layout,geometry,baseline_options,*,routing_seed=42):
    schedule=[(name,[tuple(pair) for pair in pairs]) for name,pairs in schedule]
    module=load_core();options=module.CompilerOptions(**baseline_options);slots=[[tuple(p) for p in slot] for slot in layout]
    busiest=module.find_busiest_pairs(schedule);canonical=module.create_initial_mapping(busiest,slots)
    random.seed(routing_seed);t=time.perf_counter()
    instructions=module.generate_hardware_instructions(schedule,canonical,busiest,num_qubits,geometry['rows'],geometry['columns'],slots,
                                                         geometry['r_blk'],geometry['r_int'],options=options)
    return {'instructions':'\n'.join(instructions)+'\n','planner_seconds':time.perf_counter()-t,
            'random_state_after_sha256':hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),'core_sha256':CORE_SHA256}