"""Independent analytic examples, frozen adversarial fixtures, real adapters."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
import os
sys.dont_write_bytecode=True
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS','QISKIT_NUM_PROCS']:
    os.environ[key]='1'
os.environ['QISKIT_PARALLEL']='FALSE'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from implementation.adapters.upstream import adapt_run,build_trace,rft_groups
from implementation.trace.model import fingerprint,load_trace,save_trace
from implementation.validation.checker import check_trace,closest_separation
from implementation.metrics.legacy import measure_trace


class Acceptance(unittest.TestCase):
    def test_analytic_known_examples(self):
        # Hand geometry: diagonal segments cross halfway; horizontal parallel
        # paths stay two units apart; a point projects to the segment midpoint.
        d,u=closest_separation((0,0),(2,2),(0,2),(2,0));self.assertAlmostEqual(d,0);self.assertAlmostEqual(u,.5)
        d,u=closest_separation((0,0),(2,0),(0,2),(2,2));self.assertAlmostEqual(d,2)
        d,u=closest_separation((0,0),(2,0),(1,1),(1,1));self.assertAlmostEqual(d,1);self.assertAlmostEqual(u,.5)
        d,u=closest_separation((0,0),(1,0),(2,0),(2,0));self.assertAlmostEqual(d,1);self.assertAlmostEqual(u,1)

    def test_all_frozen_adversarial_fixtures(self):
        directories=sorted((ROOT/'tests/fixtures/trace_v1').iterdir());self.assertGreaterEqual(len(directories),20)
        for directory in directories:
            with self.subTest(fixture=directory.name):
                expected=json.loads((directory/'expected.json').read_text())
                result=check_trace(load_trace(directory))
                self.assertEqual(result['status'],expected['status'],result)
                codes={e['code'] for e in result['violations']}
                self.assertTrue(set(expected['required_violation_codes']).issubset(codes),codes)
                if expected['status']=='ok':self.assertTrue(result['fully_validated_within_model'])
                else:self.assertFalse(result['fully_validated_within_model'])

    def test_metric_distinctions_on_parallel_fixture(self):
        result=measure_trace(load_trace(ROOT/'tests/fixtures/trace_v1/valid_parallel'))
        self.assertEqual(result['moved_atom_events'],2)
        self.assertEqual(result['sum_atom_distance_um'],2)
        self.assertEqual(result['sum_batch_max_distance_um'],1)
        self.assertEqual(result['inferred_transfer_atom_events'],4)
        self.assertEqual(result['inferred_transfer_stages'],2)
        self.assertEqual(result['observed_transfer_atom_events'],0)
        self.assertAlmostEqual(result['makespan_us'],3.2)
        self.assertEqual(result['legacy']['four_per_block_transfer_alias'],4)
        self.assertAlmostEqual(result['legacy']['runtime_proxy_us'],5.2)

    def test_parking_and_final_permutation(self):
        trace=load_trace(ROOT/'tests/fixtures/trace_v1/valid_parking_cycle')
        result=check_trace(trace);metrics=measure_trace(trace)
        self.assertEqual(result['semantics']['physical_output_slot_to_logical_qubit'],[1,0])
        self.assertTrue(result['semantics']['equivalent']);self.assertEqual(metrics['explicit_parking_atom_events'],1)
        self.assertFalse(result['semantics']['full_original_circuit_checked'])

    def test_real_adapters_against_independent_saved_outputs(self):
        cases=[('rft','smoke_rft_qft5_01'),('dasatom','smoke_dasatom_qft5_01'),
               ('rft','smoke_rft_tableII_01'),('dasatom','smoke_dasatom_tableII_03')]
        for algorithm,name in cases:
            with self.subTest(run=name):
                directory=ROOT/'runs/phase_00'/name
                source=json.loads((directory/'result.json').read_text())
                trace=adapt_run(directory,algorithm);check=check_trace(trace);metrics=measure_trace(trace)
                self.assertTrue(check['structural_valid'],check)
                self.assertEqual(check['status'],'unsupported');self.assertFalse(check['fully_validated_within_model'])
                reference=source.get('boundary_replay',source.get('native_boundary_replay',{}))
                if reference.get('final_positions'):
                    expected={f'a{q}':p for q,p in reference['final_positions'].items()}
                    self.assertEqual(check['final_positions'],expected)
                if algorithm=='rft':
                    native=source['native_metrics']
                    self.assertAlmostEqual(metrics['legacy']['fidelity_proxy'],native['Fidelity (DasAtom Model)'],places=14)
                    self.assertEqual(metrics['legacy']['gate_stages'],native['Num Gate Cycles'])
                    self.assertEqual(metrics['legacy']['movement_blocks'],native['Num Movement Ops'])
                    self.assertAlmostEqual(metrics['sum_batch_max_distance_um'],native['Total Move Distance'],places=10)
                else:
                    score=source['native_metrics']['native_score']
                    self.assertAlmostEqual(metrics['legacy']['fidelity_proxy'],score[1],places=14)
                    self.assertAlmostEqual(metrics['legacy']['runtime_proxy_us'],score[3],places=10)
                if 'tableII' in name and algorithm=='dasatom':
                    self.assertFalse(trace['metadata']['origin']['original_register_complete'])
                    self.assertIn('original_declared_register',check['coverage']['unsupported'])

    def test_score_log_space_and_parameter_rejection(self):
        trace=load_trace(ROOT/'tests/fixtures/trace_v1/valid_parallel')
        trace['metadata']['legacy_scored_CZ']=200000
        result=measure_trace(trace)['legacy'];self.assertGreater(result['negative_log_fidelity'],900)
        self.assertEqual(result['fidelity_proxy'],0);self.assertTrue(result['fidelity_underflow'])
        trace['metadata']['hardware']['legacy_f_cz']=0
        result=measure_trace(trace)['legacy'];self.assertTrue(result['negative_log_fidelity_infinite'])
        self.assertFalse(result['fidelity_underflow']);self.assertEqual(result['fidelity_proxy'],0)
        trace['metadata']['hardware']['legacy_f_cz']=1.01
        with self.assertRaises(ValueError):measure_trace(trace)

    def test_invalid_source_line_never_silently_disappears(self):
        groups,diagnostics=rft_groups('[SHUTTLING]\nERROR: failed route\nunknown operation')
        self.assertEqual({d['code'] for d in diagnostics},{'upstream_error','unknown_log_format'})

    def test_hashes_shapes_and_nonzero_motion_duration(self):
        base=load_trace(ROOT/'tests/fixtures/trace_v1/valid_parallel')
        changed=copy.deepcopy(base);changed['metadata']['hardware']['spacing_um']=2
        self.assertIn('hardware_hash',{v['code'] for v in check_trace(changed)['violations']})
        changed=copy.deepcopy(base);del changed['events'][-1]['start_us']
        self.assertIn('malformed_event',{v['code'] for v in check_trace(changed)['violations']})
        changed=copy.deepcopy(base);changed['events'][2]['duration_us']=0
        self.assertIn('movement_duration_or_speed',{v['code'] for v in check_trace(changed)['violations']})

    def test_atom_identity_and_gate_truth_detect_wrong_wire(self):
        changed=load_trace(ROOT/'tests/fixtures/trace_v1/no_CZ')
        changed['events'][0]['logical_qubit_ids']=[0,0]
        codes={v['code'] for v in check_trace(changed)['violations']}
        self.assertIn('duplicate_logical_state',codes)

    def test_saved_checksum_and_schema_contract(self):
        schema=json.loads((ROOT/'configs/schemas/trace_v1.schema.json').read_text())
        required=set(schema['$defs']['event']['required'])
        trace=load_trace(ROOT/'tests/fixtures/trace_v1/valid_parallel')
        for event in trace['events']:self.assertTrue(required.issubset(event))
        destination=self.output/'checksum_fixture';save_trace(destination,trace)
        self.assertEqual(load_trace(destination)['events'],trace['events'])
        path=destination/'events.jsonl';path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'checksum'):load_trace(destination)

    def test_full_original_QFT_for_both_real_adapters(self):
        from implementation.validation.full_circuit import verify_original
        raw=ROOT/'benchmarks/current_baseline_v1/raw/fig4_qft/qft_5.qasm'
        for algorithm in ['rft','dasatom']:
            with self.subTest(algorithm=algorithm):
                trace=adapt_run(ROOT/f'runs/phase_00/smoke_{algorithm}_qft5_01',algorithm)
                result=verify_original(trace,raw)
                self.assertTrue(result['comparison']['equivalent_up_to_global_phase'])
                self.assertLess(result['comparison']['maximum_absolute_error'],1e-12)
                self.assertFalse(result['comparison']['physical_validity_implied'])
                self.assertTrue(any(o.get('provenance')=='restored_from_original_precursor' for o in result['operations']))

    def test_full_gate_noncommutation_and_wrong_permutation_are_detected(self):
        from qiskit import QuantumCircuit,transpile
        from qiskit.quantum_info import Operator
        from implementation.validation.full_circuit import restore_operations,simulate,compare_matrices
        from implementation.trace.model import circuit_from_pairs,evidence_profile
        original=QuantumCircuit(2);original.h(0);original.rx(.37,1);original.cz(0,1);original.ry(.21,0)
        precursor=transpile(original,basis_gates=['cz','h','s','t','rx','ry','rz'],optimization_level=0)
        profile=evidence_profile(5)
        groups=[{'kind':'initialize','items':[{'qubit':0,'site':[0,0]},{'qubit':1,'site':[0,2]}]},
            {'kind':'move','items':[{'qubit':0,'from':[0,0],'to':[2,0]}]},
            {'kind':'move','items':[{'qubit':1,'from':[0,2],'to':[0,0]}]},
            {'kind':'move','items':[{'qubit':0,'from':[2,0],'to':[0,2]}]},
            {'kind':'gate','items':[{'qubits':[0,1],'sites':[[0,2],[0,0]]}]}]
        trace=build_trace(groups,circuit_from_pairs(2,[(0,1)]),profile)
        operations=restore_operations(trace,precursor);expected=Operator(original).data
        self.assertTrue(compare_matrices(expected,simulate(operations,2,float(precursor.global_phase)))['equivalent_up_to_global_phase'])
        without_h=[o for o in operations if o.get('name')!='h']
        self.assertFalse(compare_matrices(expected,simulate(without_h,2,float(precursor.global_phase)))['equivalent_up_to_global_phase'])
        wrong=copy.deepcopy(operations);wrong[-1]['new_slot_to_old_slot']=[0,1]
        self.assertFalse(compare_matrices(expected,simulate(wrong,2,float(precursor.global_phase)))['equivalent_up_to_global_phase'])
        bad=copy.deepcopy(trace);bad['events'][-1]['gate_id']='not_the_required_CZ'
        with self.assertRaisesRegex(ValueError,'dependencies'):restore_operations(bad,precursor)

    def test_audit_accounts_for_censored_omissions_without_inventing_results(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('phase02_follow',ROOT/'tools/follow_phase02_audit.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        plan={'jobs':[{'id':'a'},{'id':'b'},{'id':'c'}]}
        rows=[{'job_id':'a'}];omitted=[{'job_id':'b'}]
        result=module.account_jobs(plan,rows,omitted,False)
        self.assertFalse(result['all_jobs_accounted']);self.assertEqual(result['unaccounted_jobs'],['c'])
        rows.append({'job_id':'c'});result=module.account_jobs(plan,rows,omitted,True)
        self.assertTrue(result['all_jobs_accounted']);self.assertFalse(result['first_pass_dataset_audit_complete'])
        result=module.account_jobs(plan,rows,omitted,False)
        self.assertTrue(result['first_pass_dataset_audit_complete']);self.assertEqual(result['attempted_jobs'],2)
        source=json.loads((ROOT/'runs/phase_00/smoke_rft_qft5_01/result.json').read_text())
        trace=adapt_run(ROOT/'runs/phase_00/smoke_rft_qft5_01','rft')
        metrics=measure_trace(trace);self.assertTrue(module.compare_legacy(source,metrics)['all_match'])
        metrics['legacy']['runtime_proxy_us']+=1
        self.assertFalse(module.compare_legacy(source,metrics)['all_match'])

    def test_corrected_control_preserves_embeddings_and_rejects_full_grid(self):
        from implementation.adapters.vacancy_control import corrected_trace,vacancy_transition,UnsupportedVacancyRoute
        from implementation.trace.model import circuit_from_pairs,evidence_profile
        native={'embeddings':[[[0,0],[0,2]],[[0,2],[0,0]]],
            'gate_groups':[[[[0,1]]],[[[0,1]]]]}
        trace=corrected_trace(native,circuit_from_pairs(2,[(0,1),(0,1)]),evidence_profile(5),{'kind':'fixture'})
        validation=check_trace(trace)
        self.assertEqual(validation['status'],'ok',validation)
        self.assertEqual(validation['final_positions'],{'a0':[0,2],'a1':[0,0]})
        self.assertEqual(validation['observed_gate_count'],2)
        self.assertTrue(trace['metadata']['corrected_control_not_native_measurement'])
        self.assertFalse(trace['metadata']['native_routing_choices_preserved'])
        self.assertEqual(vacancy_transition([[0,0]],[[0,0]],1,1),[])
        with self.assertRaises(UnsupportedVacancyRoute):
            vacancy_transition([[0,0],[0,1]],[[0,1],[0,0]],1,2)
        actual=load_trace(ROOT/'runs/phase_02/dasatom_corrected_vacancy_qft10_01/trace')
        result=check_trace(actual)
        self.assertEqual(result['status'],'ok');self.assertEqual(result['observed_gate_count'],105)
        self.assertTrue(result['fully_validated_within_model']);self.assertFalse(result['source_physical_evidence_complete'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output must be under btp_work')
    if out.exists():raise FileExistsError('Output already exists')
    out.mkdir(parents=True)
    Acceptance.output=out
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance)
    with (out/'unittest.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for base in ['implementation','tests/fixtures/trace_v1'] for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'successful':result.wasSuccessful(),'artifact_sha256':hashes,
        'command':sys.argv,'python':sys.version,'full_baseline_audit_complete':False}
    (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='artifact_sha256'}))
    if not result.wasSuccessful():print((out/'unittest.txt').read_text())
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
