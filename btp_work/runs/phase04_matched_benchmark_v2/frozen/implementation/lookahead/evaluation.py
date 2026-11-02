"""NEW Phase04 evaluation adapter; all physics delegates to the Phase03 model."""
from copy import deepcopy
import math
from implementation.trace.model import evidence_profile
from implementation.adapters.upstream import rft_groups,build_trace
from implementation.validation.checker import check_trace
from implementation.metrics.legacy import measure_trace
from implementation.movement_error.schedule import make_schedule
from implementation.movement_error.evaluator import evaluate


def pilot_geometry_profile(geometry):
    """Declared testing contract shared by all policies, not native device evidence."""
    hw=evidence_profile(geometry['rows'],geometry['r_int'],geometry['r_blk']);hw['columns']=geometry['columns'];hw['spacing_um']=geometry.get('spacing_um',3.0)
    hw.update(profile_id='phase04_declared_two_plane_testing.v1',min_atom_separation_um=hw['spacing_um'],slm_aod_shared_plane=False,
              slm_aod_plane_offset_um=hw['spacing_um'],
              assumptions=['NEW Phase04 testing geometry: separate SLM/AOD planes with one-spacing clearance, ordinary trap-transfer primitives',
                           'Shared single-AOD progress; all policies use identical geometry; no measured native plane separation is claimed'])
    return hw


def evaluate_compilation(compilation,circuit,geometry,physics_profile):
    groups,diagnostics=rft_groups(compilation['instructions']);hw=pilot_geometry_profile(geometry)
    origin={'kind':'rft_phase04_controlled','physical_source':'new controlled compile under declared geometry, not a native device observation',
            'core_sha256':compilation['core_sha256'],'lookahead_options':deepcopy(compilation['lookahead_options']),
            'baseline_options':deepcopy(compilation['baseline_options']),'routing_seed':compilation['routing_seed'],
            'original_register_complete':True}
    trace=build_trace(groups,deepcopy(circuit),hw,origin=origin,timing='two_transfer_stages',diagnostics=diagnostics)
    trace['metadata']['assumptions']+=hw['assumptions']
    validation=check_trace(trace);metrics=measure_trace(trace)
    schedule=make_schedule(trace,physics_profile,'retime');result=evaluate(schedule)
    gates=[e for e in trace['events'] if e['kind']=='gate'];previous={};unchanged=0;repeat=0
    for e in gates:
        pair=tuple(sorted(e['logical_qubit_ids']));mapping=dict(zip(e['logical_qubit_ids'],e.get('sites',[]) or []));sites=tuple((q,tuple(mapping[q])) for q in pair)
        if pair in previous:
            repeat+=1;unchanged+=int(previous[pair]==sites)
        previous[pair]=sites
    return {'trace':trace,'source_validation':validation,'metrics':metrics,'schedule':schedule,'result':result,
            'unchanged_pair_reoccurrences':unchanged,'pair_reoccurrences':repeat,
            'accepted_schedule':validation['status']=='ok' and result['status']=='ok' and result['valid_for_comparison'],
            'geometry_is_declared_testing_model':True,'native_physical_validity_claimed':False}