"""Paper coverage, immutable reuse, corrected routing and register regressions."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode=True
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS','QISKIT_NUM_PROCS']:os.environ[key]='1'
os.environ['QISKIT_PARALLEL']='FALSE'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
CORRECTIONS=ROOT/'runs/paper_focus_v2/cached_corrections_05'
from implementation.corrected.dasatom_routes import repair_native,route_transition,restore_idle_qubits,RoutingUnsupported,CapacityUnsupported
from implementation.trace.model import circuit_from_pairs,load_trace
from implementation.validation.checker import check_trace


class Acceptance(unittest.TestCase):
    def test_exact_paper_target_matrix(self):
        plan=json.loads((ROOT/'configs/studies/paper_focus_v2.json').read_text())
        with (ROOT/'reports/phase_01/published_targets.csv').open() as stream:references=list(csv.DictReader(stream))
        expected={(r['family'],r['circuit'],int(r['grid']),'rft' if r['method'].startswith('rft') else r['method']) for r in references}
        actual={(j['family'],j['case'],j['grid'],j['algorithm']) for j in plan['jobs']}
        self.assertEqual(actual,expected);self.assertEqual(len(actual),132)
        self.assertEqual(sum(j['family']=='fig4_qft' for j in plan['jobs']),72)
        self.assertEqual(sum(j['family']=='tableII' for j in plan['jobs']),60)
        self.assertFalse(plan['new_rft8_sweep']);self.assertFalse(plan['new_blanket_timing_repetitions'])
        self.assertTrue(plan['retain_all_existing_timing_repetitions'])

    def test_original_attempts_are_unchanged(self):
        inventory=json.loads((ROOT/'reports/phase_01/paper_focus_v2/frozen_record_inventory.json').read_text())
        self.assertEqual(len(inventory),411)
        for item in inventory:
            self.assertEqual(hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(),item['sha256'])
        plan=json.loads((ROOT/'configs/studies/paper_focus_v2.json').read_text())
        for job in plan['jobs']:
            if not job['selected_reference']:continue
            record=ROOT/job['selected_reference']['record']
            manifest=ROOT/'reports/phase_02/live_audit_v2/attempts'/record.parent.parent.name/record.parent.name/'trace_manifest.json'
            data=json.loads(manifest.read_text())
            for source in data['metadata']['origin']['source_files']:
                path=Path(source['path']).resolve();self.assertTrue(path.is_relative_to(ROOT))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),source['sha256'])

    def test_old_726_job_controller_cannot_be_accidentally_resumed(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import baseline_campaign
        with self.assertRaisesRegex(SystemExit,'stopped by the user'):
            baseline_campaign.run(ROOT/'runs/current_baseline/study_v1',None)

    def test_all_reused_RFT_targets_have_matching_prior_independent_audits(self):
        plan=json.loads((ROOT/'configs/studies/paper_focus_v2.json').read_text())
        reused=[j for j in plan['jobs'] if j['algorithm']=='rft']
        self.assertEqual(len(reused),66)
        for job in reused:
            reference=job['selected_reference'];record=ROOT/reference['record']
            audit=ROOT/'reports/phase_02/live_audit_v2/attempts'/record.parent.parent.name/record.parent.name/'audit.json'
            result=json.loads(audit.read_text())
            self.assertEqual(result['record_sha256'],reference['sha256'])
            self.assertFalse(result['adapter_error']);self.assertTrue(result['legacy_all_match'])
            self.assertTrue(result['saved_final_mapping_matches'])
            self.assertEqual(result['evidence_violation_codes'],[])

    def test_every_cached_paper_target_is_independently_replayed(self):
        summary=json.loads((CORRECTIONS/'summary.json').read_text())
        self.assertEqual(summary['targets'],57);self.assertEqual(summary['new_partition_or_embedding_runs'],0)
        for row in summary['results']:
            with self.subTest(target=row['target_id']):
                trace=load_trace(CORRECTIONS/row['target_id']/'trace')
                result=check_trace(trace)
                self.assertTrue(result['structural_valid'],result)
                self.assertEqual(result['violations'],[])
                self.assertFalse(result['fully_validated_within_model'])
                self.assertIn('physical_minimum_separation',result['coverage']['unsupported'])
                self.assertTrue(trace['metadata']['origin']['original_register_complete'])

    def test_occupied_destination_and_cycle(self):
        batches,report=route_transition([[0,0],[0,2]],[[1,0],[0,0]],3,3,[[[1,[0,2],[0,0]]],[[0,[0,0],[1,0]]]])
        self.assertFalse(report['native_transition_reused']);self.assertEqual(batches[0][0][0],0)
        native={'embeddings':[[[0,0],[0,2]],[[0,2],[0,0]]], 'gate_groups':[[[[0,1]]],[[[0,1]]]],'movement_list':[[[[0,[0,0],[0,2]]],[[1,[0,2],[0,0]]]]],'actual_grid':3}
        trace,corrected=repair_native(native,circuit_from_pairs(2,[(0,1),(0,1)]),3)
        result=check_trace(trace);self.assertTrue(result['structural_valid'],result)
        self.assertEqual(result['final_positions'],{'a0':[0,2],'a1':[0,0]})

    def test_legal_native_route_is_retained(self):
        original=[[[0,[0,0],[0,1]]]]
        batches,report=route_transition([[0,0],[2,2]],[[0,1],[2,2]],3,3,original)
        self.assertTrue(report['native_transition_reused']);self.assertEqual(batches,original)

    def test_idle_population_capacity_empty_and_wrong_grid(self):
        embeddings=restore_idle_qubits([[[0,0],[0,1]],[[0,1],[0,0]]],4,3,3)
        self.assertEqual(len(embeddings[0]),4);self.assertEqual(embeddings[0][2:],embeddings[1][2:])
        with self.assertRaises(CapacityUnsupported):restore_idle_qubits([[[0,0]]],5,2,2)
        with self.assertRaises(RoutingUnsupported):route_transition([[0,0],[0,1]],[[0,1],[0,0]],1,2)
        empty={'embeddings':[],'gate_groups':[],'movement_list':[],'actual_grid':3}
        trace,_=repair_native(empty,circuit_from_pairs(2,[]),3)
        self.assertTrue(check_trace(trace)['structural_valid'])
        with self.assertRaises(CapacityUnsupported):repair_native({**empty,'actual_grid':4},circuit_from_pairs(2,[]),3)

    def test_fresh_upstream_tuple_sites_have_the_same_mapping_as_json_cache(self):
        native={'embeddings':[[(0,0),(0,1)]],'gate_groups':[[[[0,1]]]],'movement_list':[],'actual_grid':3}
        trace,_=repair_native(native,circuit_from_pairs(3,[(0,1)]),3)
        result=check_trace(trace)
        self.assertTrue(result['structural_valid'],result)
        self.assertEqual(trace['metadata']['expected_final_positions']['a0'],[0,0])

    def test_restored_idle_wires_preserve_full_original_unitary(self):
        from qiskit import QuantumCircuit,qasm2
        from implementation.validation.full_circuit import verify_original
        original=QuantumCircuit(4);original.h(2);original.rx(.31,3);original.h(0);original.cz(0,1)
        native={'embeddings':[[[0,0],[0,1]]],'gate_groups':[[[[0,1]]]],'movement_list':[],'actual_grid':3}
        trace,_=repair_native(native,circuit_from_pairs(4,[(0,1)]),3)
        source=self.out/'idle_unitary.qasm';source.write_text(qasm2.dumps(original),encoding='utf-8')
        result=verify_original(trace,source)
        self.assertTrue(result['comparison']['equivalent_up_to_global_phase'])

    def test_fresh_corrected_worker_agrees_with_reused_layout_repairs(self):
        for tag,target,n in [('qft10','fig4_qft__qft_10__g11__dasatom__standalone__native',10),
            ('idle16','tableII__4mod5-v1_22__g11__dasatom__standalone__native',16)]:
            fresh=ROOT/'runs/paper_focus_v2'/('fresh_smoke_'+tag+'_02')
            result=json.loads((fresh/'result.json').read_text())
            self.assertEqual(result['status'],'ok');self.assertEqual(result['hash_seed'],'0')
            self.assertEqual(result['full_declared_register'],n)
            self.assertEqual(result['purpose'],'validation_smoke')
            cached=json.loads((CORRECTIONS/target/'native_corrected.json').read_text())
            measured=json.loads((fresh/'native_corrected.json').read_text())
            for field in ['embeddings','gate_groups','movement_list']:self.assertEqual(cached[field],measured[field])

    def test_worker_handles_no_two_qubit_gate_without_crashing(self):
        import subprocess
        source=self.out/'empty_normalized.qasm'
        source.write_text('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n',encoding='utf-8')
        environment=dict(os.environ);environment['PYTHONHASHSEED']='0'
        result=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/corrected_dasatom_worker.py'),
            '--input',str(source),'--grid','3','--purpose','validation_smoke','--out',str(self.out/'empty_worker')],
            capture_output=True,text=True,env=environment,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        record=json.loads((self.out/'empty_worker/result.json').read_text())
        self.assertEqual(record['status'],'ok');self.assertEqual(record['full_declared_register'],2)
        self.assertEqual(record['CZ'],0)

    def test_bounded_runner_stops_only_its_timeout_fixture(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('focus_runner',ROOT/'tools/run_paper_focus.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        plan=json.loads((ROOT/'configs/studies/paper_focus_v2.json').read_text())
        job=next(j for j in plan['jobs'] if j['algorithm']=='dasatom' and j['case']=='qft_5' and j['grid']==11).copy()
        job['target_id']='timeout_fixture'
        result=module.bounded_job(job,.05,output_root=self.out/'bounded_control')
        self.assertEqual(result['status'],'timeout');self.assertIsNotNone(result['process_exit_code'])
        self.assertTrue(result['monitored_process_ids']);self.assertLess(result['process_wall_seconds'],10)

    def test_runner_reuses_success_and_holds_identical_failed_retries(self):
        import importlib.util
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('focus_guard',ROOT/'tools/run_paper_focus.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fake=self.out/'guard_control'
        for relative in ['tools/corrected_dasatom_worker.py','implementation/corrected/dasatom_routes.py']:
            path=fake/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture',encoding='utf-8')
        record=fake/'runs/paper_focus_v2/fresh_compilations/fixture/attempt_01/attempt_record.json'
        record.parent.mkdir(parents=True)
        digest=hashlib.sha256(b'fixture').hexdigest()
        payload={'status':'timeout','worker_sha256':digest,'router_sha256':digest,'timeout_seconds':1800}
        record.write_text(json.dumps(payload),encoding='utf-8')
        with patch.object(module,'ROOT',fake):
            self.assertIsNone(module.completed_compatible({'target_id':'fixture'}))
            self.assertEqual(module.exhausted_same_cap({'target_id':'fixture'},1800),record)
            self.assertIsNone(module.exhausted_same_cap({'target_id':'fixture'},3600))
            payload['status']='ok';record.write_text(json.dumps(payload),encoding='utf-8')
            self.assertEqual(module.completed_compatible({'target_id':'fixture'}),record)

    def test_exact_paper_tableI_worked_example(self):
        # Paper PDF p4: layers (01,23), (12), (03). Independent next-partner
        # oracle: Table I retains current partner before future occurrences.
        layers=[[(0,1),(2,3)],[(1,2)],[(0,3)]]
        expected=[[(1,0),(3,1),(3,0)],[(0,0),(2,0),None],[(3,0),(1,0),None],[(2,0),(0,1),(0,0)]]
        actual=[]
        for q in range(4):
            entries=[]
            for t in range(3):
                found=None
                for future in range(t,3):
                    pair=next((p for p in layers[future] if q in p),None)
                    if pair:found=(pair[1] if pair[0]==q else pair[0],future-t);break
                entries.append(found)
            actual.append(entries)
        self.assertEqual(actual,expected)

    def test_five_actual_routing_seeds_on_fixed_paper_worked_example(self):
        import random
        from dataclasses import replace
        from qiskit import QuantumCircuit,qasm2
        sys.path.insert(0,str(ROOT/'vendor/NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a/src'))
        import compiler_core as core
        from benchmark_runner import ladder_variants
        from implementation.adapters.upstream import rft_groups,build_trace
        from implementation.trace.model import evidence_profile
        pairs=[(0,1),(2,3),(1,2),(0,3)]
        qc=QuantumCircuit(4)
        for a,b in pairs:qc.cz(a,b)
        source=self.out/'paper_worked_example.qasm';source.write_text(qasm2.dumps(qc),encoding='utf-8')
        _,schedule,n=core.analyze_qasm_file(str(source));records=[]
        for seed in range(5):
            random.seed(seed)
            options=replace(ladder_variants()['7_dynamic_slot_01q_move'],random_seed=seed)
            text='\n'.join(core.generate_hardware_instructions(schedule,{},[],n,3,3,
                [[(0,0),(0,1)],[(2,0),(2,1)]],2,1,options=options))
            groups,diagnostics=rft_groups(text)
            trace=build_trace(groups,circuit_from_pairs(4,pairs),evidence_profile(3,1,2),diagnostics=diagnostics)
            result=check_trace(trace);self.assertTrue(result['structural_valid'],result)
            (self.out/f'routing_seed_{seed}.txt').write_text(text,encoding='utf-8')
            records.append({'routing_seed':seed,'trace_sha256':hashlib.sha256(text.encode()).hexdigest(),'known_violations':result['violations']})
        (self.out/'routing_seed_fixture_results.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a new report directory under btp_work')
    out.mkdir(parents=True);Acceptance.out=out
    with (out/'unittest.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    summary={'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
        'command':sys.argv,'router_sha256':hashlib.sha256((ROOT/'implementation/corrected/dasatom_routes.py').read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))
    if not result.wasSuccessful():print((out/'unittest.txt').read_text())
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
