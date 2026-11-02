"""Freeze adversarial trace-v1 fixtures; never overwrites an existing suite."""
import copy
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from implementation.adapters.upstream import build_trace,rft_groups
from implementation.trace.model import circuit_from_pairs,evidence_profile,fingerprint,save_trace


def fixture_cases():
    profile=evidence_profile(5,2,4)
    profile.update(profile_id='synthetic_single_plane.v1',spacing_um=1.0,
        interaction_radius_um=2.0,restriction_radius_um=4.0,
        min_atom_separation_um=1.0,slm_aod_shared_plane=True,
        move_speed_um_per_us=1.0,transfer_stage_duration_us=1.0,
        source='Analytic testing model, not a measured device',assumptions=['All traps share a plane; common linear movement progress'])
    def make(positions,movements=(),pairs=(),gate_groups=None):
        groups=[{'kind':'initialize','items':[{'qubit':q,'site':p} for q,p in enumerate(positions)]}]
        for moves in movements:
            groups.append({'kind':'move','items':[{'qubit':q,'from':a,'to':b,'cause':cause} for q,a,b,cause in moves]})
        end=dict(enumerate(positions))
        for moves in movements:
            for q,a,b,cause in moves: end[q]=b
        for batch in (gate_groups if gate_groups is not None else [[p] for p in pairs]):
            groups.append({'kind':'gate','items':[{'qubits':list(p),'sites':[end[p[0]],end[p[1]]]} for p in batch]})
        return build_trace(groups,circuit_from_pairs(len(positions),pairs),copy.deepcopy(profile),timing='two_transfer_stages')
    cases={}
    def add(name,trace,status='ok',codes=()):
        cases[name]={'trace':trace,'expected':{'status':status,'required_violation_codes':list(codes)}}
    U='explicit_nonparking'
    parallel=make([(0,0),(0,2)],[[[0,(0,0),(1,0),U],[1,(0,2),(1,2),U]]],[(0,1)])
    add('valid_parallel',parallel)
    add('row_reversal',make([(0,0),(0,2)],[[[0,(0,0),(0,2),U],[1,(0,2),(0,0),U]]]),'invalid',['aod_line_order_or_equality','continuous_collision'])
    add('same_source_line_diverges',make([(0,0),(0,2)],[[[0,(0,0),(1,0),U],[1,(0,2),(2,2),U]]]),'invalid',['aod_line_order_or_equality'])
    add('destination_lines_merge',make([(0,0),(2,2)],[[[0,(0,0),(1,0),U],[1,(2,2),(1,2),U]]]),'invalid',['aod_line_order_or_equality'])
    add('two_atom_midpath_collision',make([(0,0),(2,0)],[[[0,(0,0),(2,2),U],[1,(2,0),(0,2),U]]]),'invalid',['continuous_collision'])
    add('moving_stationary_collision',make([(0,0),(1,1)],[[[0,(0,0),(2,2),U]]]),'invalid',['continuous_collision'])
    add('blocked_destination',make([(0,0),(0,2)],[[[0,(0,0),(0,2),U]]]),'invalid',['duplicate_occupancy','continuous_collision'])
    parking=make([(0,0),(0,2)],[[[0,(0,0),(2,0),'cycle_break']],[[1,(0,2),(0,0),U]],[[0,(2,0),(0,2),U]]],[(0,1)])
    add('valid_parking_cycle',parking)
    full=make([(0,0),(0,1),(1,0),(1,1)],[[[0,(0,0),(0,1),U]]])
    full['metadata']['hardware'].update(rows=2,columns=2)
    full['metadata']['hardware_sha256']=fingerprint(full['metadata']['hardware'])
    add('full_grid_cycle_without_vacancy',full,'invalid',['duplicate_occupancy'])
    missing=copy.deepcopy(parallel);missing['events']=[e for e in missing['events'] if e['kind']!='gate']
    add('missing_gate',missing,'invalid',['missing_gate','CZ_unitary_mismatch'])
    duplicate=copy.deepcopy(parallel);extra=copy.deepcopy(duplicate['events'][-1]);extra['event_id']='duplicate_cz';duplicate['events'].append(extra)
    add('duplicated_gate',duplicate,'invalid',['duplicate_gate'])
    inverted=make([(0,0),(0,1),(1,1)],pairs=[(0,1),(1,2)])
    inverted['events'][-2],inverted['events'][-1]=inverted['events'][-1],inverted['events'][-2]
    add('dependency_inversion',inverted,'invalid',['dependency_inversion'])
    add('insufficient_interaction_range',make([(0,0),(0,4)],pairs=[(0,1)]),'invalid',['interaction_range'])
    add('blockade_conflict',make([(0,0),(0,1),(1,0),(1,1)],pairs=[(0,1),(2,3)],gate_groups=[[(0,1),(2,3)]]),'invalid',['blockade_conflict'])
    add('no_CZ',make([(0,0),(2,2)]))
    add('zero_qubits',make([]))
    unknown=make([]);_,diagnostics=rft_groups('a future log format that is not supported')
    unknown['metadata']['diagnostics']=diagnostics
    add('unknown_log_format',unknown,'invalid',['unknown_log_format'])
    malformed=copy.deepcopy(parallel);malformed['events'][-1]['duration_us']=-1
    add('malformed_time_interval',malformed,'invalid',['malformed_event'])
    upstream=make([]);upstream['metadata']['diagnostics']=[{'code':'upstream_error','text':'ERROR: no empty cycle-breaking site'}]
    add('silent_upstream_ERROR',upstream,'invalid',['upstream_error'])
    partial=copy.deepcopy(parallel);partial['metadata']['expected_final_positions']={'a0':[0,0],'a1':[0,2]}
    add('partial_route_final_map',partial,'invalid',['final_mapping_mismatch'])
    retained=copy.deepcopy(parallel)
    # Leave a1 in the same AOD but omit it from the move; its shared row must follow.
    for event in retained['events']:
        if event['kind']=='move':
            for field in ['atom_ids','logical_qubit_ids','from_sites','to_sites','causes']: event[field]=event[field][:1]
    add('retained_AOD_shared_line',retained,'invalid',['aod_line_order_or_equality'])
    unsupported=copy.deepcopy(parallel)
    unsupported['events'][2]['trajectory']={'kind':'independent_non_linear_profiles'}
    add('unsupported_trajectory',unsupported,'unsupported')
    zero=make([(0,0)],[[[0,(0,0),(0,0),U]],[[0,(0,0),(0,0),U]]])
    add('no_progress_loop',zero,'invalid',['no_progress_batches'])
    bounds=make([(0,0)],[[[0,(0,0),(5,0),U]]])
    add('out_of_grid',bounds,'invalid',['malformed_event'])
    overlap=copy.deepcopy(parallel)
    for event in overlap['events']:
        if event['kind']=='gate':event['start_us']=1.0
    add('overlapping_move_and_gate',overlap,'invalid',['move_gate_overlap','overlapping_atom_intervals'])
    return cases


def main():
    out=ROOT/'tests/fixtures/trace_v1'
    if out.exists(): raise FileExistsError('Fixture suite already exists')
    cases=fixture_cases();out.mkdir(parents=True)
    for name,case in cases.items():
        directory=out/name;save_trace(directory,case['trace'])
        (directory/'expected.json').write_text(json.dumps(case['expected'],indent=2)+'\n',encoding='utf-8')
        circuit=case['trace']['metadata']['circuit']
        qasm='OPENQASM 2.0;\ninclude "qelib1.inc";\n'
        if circuit['num_qubits']:qasm+=f"qreg q[{circuit['num_qubits']}];\n"
        qasm+=''.join(f"cz q[{g['qubits'][0]}],q[{g['qubits'][1]}];\n" for g in circuit['gates'])
        (directory/'input.qasm').write_text(qasm,encoding='utf-8')
    print(json.dumps({'fixtures':len(cases),'directory':str(out)}))


if __name__=='__main__':main()
