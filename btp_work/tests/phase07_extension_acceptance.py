"""Legacy replay adapter, generator semantics and factorial design acceptance."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from phase07_extension import read, write, sha, factorial_replay_scope
from implementation.assignment.integration import compile_schedule
from implementation.assignment.costs import load_options as assignment_options
from implementation.lookahead.potential import load_options as parking_options
from implementation.movement_error.profiles import load_profile
from implementation.repair.config import load_options as repair_options
import implementation.repair.search as search
from implementation.validation.full_circuit import verify_original
from implementation.trace.model import fingerprint


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=read(ROOT/'runs/idea1_extension_v1/protocol.json')
        cls.case=cls.protocol['cases'][0]
        cls.profile=load_profile(ROOT/'configs/hardware/extended_no_cooling.json')
        cls.proofs=[]

    def test_exact_legacy_and_generalized_baselines_both_assignment_controls(self):
        original=search.replay
        with factorial_replay_scope():
            for l in ['legacy_exact','next_events_h4']:
                for a in ['sum_distance_expanded','composite_bottleneck_expanded']:
                    look=parking_options(ROOT/('configs/variants/lookahead.'+l+'.json'))
                    assign=assignment_options(ROOT/('configs/variants/assignment.'+a+'.json'))
                    prepared=search.prepare(self.case,look,assign,self.profile)
                    expected=compile_schedule(self.case['schedule'],self.case['circuit']['num_qubits'],self.case['layout'],
                        self.case['geometry'],self.case['baseline_options'],look,assign,self.profile,circuit=self.case['circuit'])
                    self.assertEqual(prepared['compilation']['instructions'],expected['instructions'])
                    self.assertEqual(prepared['compilation']['random_state_after_sha256'],expected['random_state_after_sha256'])
        self.assertIs(search.replay,original)

    def test_enabled_repair_and_failure_restore_adapter_and_rng(self):
        rng=random.getstate();original=search.replay
        look=parking_options(ROOT/'configs/variants/lookahead.legacy_exact.json')
        assign=assignment_options(ROOT/'configs/variants/assignment.sum_distance_expanded.json')
        with factorial_replay_scope():
            result=search.repair(self.case,look,assign,self.profile,repair_options(ROOT/'configs/variants/repair.small.json'))
            self.assertLessEqual(result['final_E'],result['original_E'])
            self.assertTrue(result['caller_rng_restored'])
            self.assertTrue(all(e['incumbent_unchanged_after_trial'] for e in result['audit']))
        self.assertEqual(random.getstate(),rng)
        self.assertIs(search.replay,original)

    def test_genuine_qaoa_and_qv_original_unitaries_survive_skeleton_routing(self):
        with factorial_replay_scope():
            for family in ['qaoa','quantum_volume']:
                case=next(c for c in self.protocol['cases'] if c['family']==family)
                self.assertEqual(case['circuit']['num_qubits'],6)
                look=parking_options(ROOT/'configs/variants/lookahead.next_events_h4.json')
                assign=assignment_options(ROOT/'configs/variants/assignment.composite_bottleneck_expanded.json')
                result=search.repair(case,look,assign,self.profile,repair_options(ROOT/'configs/variants/repair.small.json'))
                proof=verify_original(result['incumbent']['evaluation']['trace'],ROOT/case['original_path'])['comparison']
                self.assertTrue(proof['equivalent_up_to_global_phase'])
                self.assertEqual(proof['basis_states'],64)
                self.proofs.append({'family':family,**proof})
                self.assertTrue(result['incumbent']['evaluation']['accepted_schedule'])

    def test_generators_and_input_hashes_are_predeclared(self):
        cases=self.protocol['cases']
        self.assertEqual({c['family'] for c in cases},{'qft','qtetris','qaoa','quantum_volume'})
        self.assertEqual(len(cases),8)
        for case in cases:
            self.assertEqual(sha(ROOT/case['original_path']),case['original_sha256'])
            self.assertEqual(sha(ROOT/case['normalized_path']),case['normalized_sha256'])
            self.assertEqual(fingerprint(case['circuit']),case['circuit_sha256'])
            if case['family']=='qaoa':
                degrees=dict.fromkeys(range(case['circuit']['num_qubits']),0)
                for a,b in case['generator']['edges']:degrees[a]+=1;degrees[b]+=1
                self.assertEqual(set(degrees.values()),{3})
                self.assertEqual(case['generator']['p'],2)
                self.assertGreater(len(case['circuit']['gates']),len(case['generator']['edges']))

    def test_all_frozen_scientific_versions_unchanged(self):
        for name,digest in self.protocol['artifact_sha256'].items():self.assertEqual(sha(ROOT/name),digest,name)
        for name,record in read(ROOT/'reports/phase_07/reused_studies.json').items():self.assertEqual(sha(ROOT/name),record['sha256'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output required under btp_work')
    out.mkdir(parents=True)
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    write(out/'result.json',{'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),
        'errors':len(result.errors),'semantic_proofs':Acceptance.proofs,'test_sha256':sha(Path(__file__))})
    print(json.dumps({'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)}))
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
