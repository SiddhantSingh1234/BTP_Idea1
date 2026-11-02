"""NEW Phase04 declared analytic fixtures; not tuned against pilot benchmarks."""
from implementation.trace.model import circuit_from_pairs,evidence_profile
from implementation.adapters.upstream import build_trace
from implementation.lookahead.events import FutureEventIndex
from implementation.lookahead.potential import FuturePotential
from implementation.movement_error.schedule import make_schedule
from implementation.movement_error.evaluator import evaluate


def serialized_case():
    layers=[[(0,1),(2,3)],[(0,2),(1,3)],[(0,3),(1,2)],[(0,1),(2,3)]]
    schedule=[(f'Time {i+1}',pairs) for i,pairs in enumerate(layers)]
    return {'schedule':schedule,'circuit':circuit_from_pairs(4,[p for layer in layers for p in layer]),
            'layout':[[(1,1),(1,2)]],'geometry':{'rows':4,'columns':4,'r_int':1,'r_blk':2,'spacing_um':3.0}}


def worse_horizon_example(physics_profile):
    # Both future CZs are already in range; a longer-looking distance surrogate
    # can spend transport unnecessarily even though its own geometric score falls.
    circuit=circuit_from_pairs(3,[(0,1),(0,2)]);schedule=[('Time 1',[]),('Time 2',[(0,1)]),('Time 3',[(0,2)])]
    index=FutureEventIndex(schedule,3,circuit);anchors={0:(0,0),1:(0,3),2:(4,1)};free=[(0,2),(2,1)];out={}
    for h in (1,2):
        events=index.query(0,0,h);potential=FuturePotential.from_events(events,anchors,gamma=1,spacing_um=1)
        site,scores=potential.choose(free,(0,0))
        groups=[{'kind':'initialize','items':[{'qubit':q,'site':list(p)} for q,p in anchors.items()]}]
        if site!=anchors[0]:groups.append({'kind':'move','items':[{'qubit':0,'from':list(anchors[0]),'to':list(site),'cause':'explicit_nonparking'}]})
        groups.extend([{'kind':'gate','items':[{'qubits':[0,1],'sites':[list(site),list(anchors[1])]}]},
                       {'kind':'gate','items':[{'qubits':[0,2],'sites':[list(site),list(anchors[2])]}]}])
        hw=evidence_profile(6,5,6);hw.update(columns=4,spacing_um=1.0,interaction_radius_um=5.0,restriction_radius_um=6.0,
             min_atom_separation_um=.5,slm_aod_shared_plane=True,profile_id='phase04_horizon_counterexample.v1',
             source='Analytic single-plane counterexample, not a device benchmark')
        trace=build_trace(groups,circuit,hw,timing='two_transfer_stages');retimed=make_schedule(trace,physics_profile,'retime');result=evaluate(retimed)
        out[str(h)]={'chosen_site':list(site),'candidate_scores':scores,'trace':trace,'schedule':retimed,'result':result}
    return out