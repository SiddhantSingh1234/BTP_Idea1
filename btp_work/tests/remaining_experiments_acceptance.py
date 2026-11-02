"""Independent weighting mathematics, scope restoration and portfolio checks."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
sys.dont_write_bytecode = True
from implementation.budgeted_study.weighting import critical_depths, WeightedPotential, parking_weight_scope
from implementation.lookahead.potential import FuturePotential, load_options as parking_options
from implementation.assignment.costs import load_options as assignment_options
from implementation.assignment.integration import compile_schedule
from implementation.lookahead.evaluation import evaluate_compilation
from implementation.movement_error.profiles import load_profile
from implementation.validation.full_circuit import verify_original
from implementation.trace.model import fingerprint
from bounded_experiment_worker import profile_options
from remaining_experiments import read, write, sha


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = read(ROOT / 'runs/idea1_extension_v1/inputs/qft_5/case.json')
        cls.profile = load_profile(ROOT / 'configs/hardware/extended_no_cooling.json')

    def test_critical_depths_against_explicit_branched_dag(self):
        circuit = {'gates': [{'gate_id':'a','dependencies':[]}, {'gate_id':'b','dependencies':['a']},
            {'gate_id':'c','dependencies':['a']}, {'gate_id':'d','dependencies':['c']},
            {'gate_id':'e','dependencies':['b','d']}]}
        self.assertEqual(critical_depths(circuit), {'e':1,'d':2,'c':3,'b':2,'a':4})
        circuit['gates'] = list(reversed(circuit['gates']))
        with self.assertRaises(ValueError): critical_depths(circuit)

    def test_weighted_choice_matches_hand_sum_and_changes_tie(self):
        events = [{'gate_id':'a','partner':0,'logical_layer_delta':0},
                  {'gate_id':'b','partner':1,'logical_layer_delta':0}]
        base = FuturePotential.from_events(events, {0:(0,0),1:(4,0)}, gamma=1., spacing_um=1.)
        available = [(1,0),(3,0)]
        self.assertEqual(base.choose(available,(0,0))[0], (1,0))
        weighted = WeightedPotential(base, {'a':1,'b':3})
        self.assertAlmostEqual(weighted.score((3,0))['scaled_distance_um'], 2.)
        self.assertAlmostEqual(weighted.score((1,0))['scaled_distance_um'], 10/3)
        self.assertEqual(weighted.choose(available,(0,0))[0], (3,0))

    def test_equal_depth_weights_recover_original_discounted_potential(self):
        events = [{'gate_id':'a','partner':0,'logical_layer_delta':10000},
                  {'gate_id':'b','partner':1,'logical_layer_delta':10002}]
        base = FuturePotential.from_events(events, {0:(0,0),1:(4,0)}, gamma=.5, spacing_um=3.)
        weighted = WeightedPotential(base, {'a':3,'b':3})
        for site in [(0,0),(1,1),(3,0)]:
            self.assertEqual(weighted.score(site)['scaled_distance_um'], base.score(site)['scaled_distance_um'])
        self.assertTrue(weighted.score((1,1))['raw_underflow'])

    def test_scoped_adapter_does_not_leak_or_change_uniform_mode(self):
        import implementation.lookahead.integration as integration
        before = integration.FuturePotential, integration.validate_options
        with parking_weight_scope(self.case['circuit'],'uniform'):
            self.assertEqual(before, (integration.FuturePotential, integration.validate_options))
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with parking_weight_scope(self.case['circuit'],'critical_remaining_depth'):
                raise RuntimeError('injected')
        self.assertEqual(before, (integration.FuturePotential, integration.validate_options))

    def test_weighted_full_circuit_is_valid_and_preserves_original_semantics(self):
        look = parking_options(ROOT/'configs/variants/lookahead.next_events_h4.json')
        look['weight_mode'] = 'critical_remaining_depth'
        assign = assignment_options(ROOT/'configs/variants/assignment.composite_bottleneck_expanded.json')
        with parking_weight_scope(self.case['circuit'],look['weight_mode']):
            value = compile_schedule(self.case['schedule'],self.case['circuit']['num_qubits'],self.case['layout'],
                self.case['geometry'],self.case['baseline_options'],look,assign,self.profile,circuit=self.case['circuit'])
        score = evaluate_compilation(value,self.case['circuit'],self.case['geometry'],self.profile)
        self.assertTrue(score['accepted_schedule'])
        proof = verify_original(score['trace'],ROOT/self.case['original_path'])['comparison']
        self.assertTrue(proof['equivalent_up_to_global_phase'])
        self.assertEqual(proof['basis_states'],32)

    def test_profile_sweeps_preserve_untargeted_parameters(self):
        baseline = profile_options('default')
        for label in ['heating_half','heating_double','acceleration_half','acceleration_double',
                      'coherence_short','coherence_long','transfer_lower','transfer_higher']:
            p = profile_options(label)
            self.assertEqual(p['noise']['cz_duration_us'],baseline['noise']['cz_duration_us'])
            self.assertEqual(p['noise']['f_cz'],baseline['noise']['f_cz'])
            self.assertFalse(p['cooling']['enabled'])

    def test_prior_completed_result_files_are_unchanged(self):
        for name,record in read(ROOT/'reports/phase_07/reused_studies.json').items():
            self.assertEqual(sha(ROOT/name),record['sha256'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh test output required')
    out.mkdir(parents=True)
    with (out/'tests.txt').open('w',encoding='utf-8') as h:
        result=unittest.TextTestRunner(stream=h,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    record={'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),
        'errors':len(result.errors),'script_sha256':sha(Path(__file__))}
    write(out/'result.json',record);print(json.dumps(record));return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
