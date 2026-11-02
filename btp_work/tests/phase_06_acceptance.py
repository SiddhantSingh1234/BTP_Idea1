"""Independent safety, replay, rollback and deterministic-budget checks for Phase06."""
import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from implementation.assignment.costs import load_options as assignment_options
from implementation.assignment.integration import compile_schedule
from implementation.lookahead.potential import load_options as parking_options
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.schedule import make_schedule
from implementation.movement_error.evaluator import evaluate
from implementation.trace.model import fingerprint
from implementation.repair.config import load_options, validate_options
from implementation.repair.fixtures import development_cases, no_improvement_case
from implementation.repair.search import prepare, repair, strict_improvement
from implementation.repair.replay import replay, check_targets, ReplayLimit, PrefixViolation
from implementation.repair.neighborhood import rank_boundaries, generate, complete_targets
from implementation.repair.evaluation import total_E, prefix_invariant, prefix_objective, placement_span
from implementation.lookahead.events import FutureEventIndex
from implementation.repair.artifacts import write

class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = development_cases()[0]
        cls.look = parking_options(ROOT / 'configs/variants/lookahead.next_events_h4.json')
        cls.assign = assignment_options(ROOT / 'configs/variants/assignment.sum_distance.json')
        cls.profile = load_profile(ROOT / 'configs/hardware/extended_no_cooling.json')
        cls.base = prepare(cls.case, cls.look, cls.assign, cls.profile)
        cls.options = load_options(ROOT / 'configs/variants/repair.small.json')
        cls.index = FutureEventIndex(cls.case['schedule'], cls.case['circuit']['num_qubits'], cls.case['circuit'])
        cls.outcome = repair(cls.case, cls.look, cls.assign, cls.profile, cls.options, baseline=cls.base)

    def run_repair(self, **kw):
        return repair(self.case, self.look, self.assign, self.profile,
            kw.pop('options', self.options), baseline=kw.pop('baseline', self.base), **kw)

    def test_disabled_and_zero_are_exact_phase05_instructions_and_schedule(self):
        for assignment_name in ['sum_distance', 'composite_bottleneck_expanded']:
            cfg = assignment_options(ROOT / ('configs/variants/assignment.' + assignment_name + '.json'))
            legacy = compile_schedule(self.case['schedule'], self.case['circuit']['num_qubits'], self.case['layout'],
                self.case['geometry'], self.case['baseline_options'], self.look, cfg, self.profile, circuit=self.case['circuit'])
            baseline = prepare(self.case, self.look, cfg, self.profile)
            self.assertEqual(legacy['instructions'], baseline['compilation']['instructions'])
            self.assertEqual(legacy['random_state_after_sha256'], baseline['compilation']['random_state_after_sha256'])
            for name in ['disabled', 'zero']:
                result = repair(self.case, self.look, cfg, self.profile,
                    load_options(ROOT / ('configs/variants/repair.' + name + '.json')), baseline=baseline)
                self.assertEqual(result['candidate_evaluations'], 0)
                self.assertEqual(result['original_schedule_sha256'], result['final_schedule_sha256'])
                self.assertEqual(baseline['evaluation']['schedule'], result['incumbent']['evaluation']['schedule'])
                self.assertEqual(legacy['instructions'], result['incumbent']['compilation']['instructions'])

    def test_all_commits_pass_independent_complete_schedule_replay(self):
        self.assertGreater(len(self.outcome['accepted_history']), 0)
        prior = self.base
        for commit in self.outcome['accepted_history']:
            candidate = commit['bundle']
            score = evaluate(candidate['evaluation']['schedule'])
            self.assertTrue(score['valid_for_comparison'])
            self.assertEqual(score['status'], 'ok')
            self.assertLess(total_E(score), total_E(prior['evaluation']['result']) - 1e-12)
            boundary = next(b for b in prior['compilation']['repair_boundaries'] if b['key'] == commit['boundary_key'])
            self.assertTrue(prefix_invariant(prior, candidate, boundary)['unchanged'])
            prior = candidate

    def test_trial_rollback_preserves_all_incumbent_and_caller_rng_state(self):
        baseline = deepcopy(self.base)
        original = fingerprint(baseline)
        random.seed(913)
        rng = random.getstate()
        result = self.run_repair(baseline=baseline)
        self.assertEqual(random.getstate(), rng)
        self.assertEqual(fingerprint(baseline), original)
        self.assertTrue(result['baseline_input_unchanged'])
        self.assertTrue(all(a['incumbent_unchanged_after_trial'] and a['caller_rng_restored_after_trial'] for a in result['audit']))
        self.assertTrue(any(not a['accepted'] for a in result['audit']))

    def test_invalid_candidate_is_discarded_and_costed(self):
        real = replay
        def corrupt(*args, **kwargs):
            value = real(*args, **kwargs)
            value['instructions'] = value['instructions'].replace('CZ', 'UNSUPPORTED_GATE')
            return value
        with patch('implementation.repair.search.replay', side_effect=corrupt):
            result = self.run_repair()
        self.assertEqual(result['final_schedule_sha256'], result['original_schedule_sha256'])
        self.assertGreater(result['candidate_evaluations'], 0)
        self.assertTrue(all(not a['accepted'] for a in result['audit']))
        self.assertTrue(all(a['evaluation_seconds'] > 0 for a in result['audit']))
        self.assertGreater(result['candidate_compile_seconds'], 0)

    def test_route_budget_exceptions_keep_a_complete_incumbent(self):
        options = {**self.options, 'max_replay_route_calls': 0}
        result = self.run_repair(options=options)
        self.assertEqual(result['candidate_evaluations'], options['max_evaluations'])
        self.assertTrue(all(a['error']['type'] == 'ReplayLimit' for a in result['audit']))
        self.assertEqual(result['final_schedule_sha256'], result['original_schedule_sha256'])
        self.assertTrue(result['incumbent']['evaluation']['accepted_schedule'])

    def test_prefix_digest_mismatch_is_rejected_and_rng_restored(self):
        boundary, _ = rank_boundaries(self.base['compilation'], self.options)[0]
        candidate = generate(boundary, self.case, self.index, self.look, self.profile, self.options)[0]
        plan = {boundary['key']: {'prefix_sha256': '0' * 64, 'targets': candidate['targets']}}
        rng = random.getstate()
        with self.assertRaises(PrefixViolation):
            replay(self.case, self.look, self.assign, self.profile, overrides=plan)
        self.assertEqual(random.getstate(), rng)

    def test_target_legality_duplicate_missing_outside_gate_and_blockade(self):
        geometry = {'rows': 10, 'columns': 10, 'r_int': 2, 'r_blk': 3}
        current = {0:(0,0), 1:(1,0), 2:(7,7), 3:(8,7)}
        for targets in [{0:(0,0)}, {**current,1:(0,0)}, {**current,1:(10,0)},
                        {**current,1:(5,0)}, {0:(0,0),1:(1,0),2:(0,2),3:(1,2)}]:
            with self.assertRaises(ValueError):
                check_targets(targets, current, [(0,1),(2,3)], geometry)
        self.assertEqual(check_targets(current,current,[(0,1),(2,3)],geometry),current)

    def test_evicted_idle_qubit_is_reparked_with_entire_register_preserved(self):
        boundary = deepcopy(self.base['compilation']['repair_boundaries'][0])
        boundary['active_pairs'] = [[0,1]]
        boundary['targets'] = {'0':[0,0],'1':[1,0],'2':[3,0],'3':[4,4],'4':[6,6]}
        boundary['current_positions'] = deepcopy(boundary['targets'])
        targets = complete_targets(boundary,{0:[3,0],1:[4,0]},self.case,self.index,self.look)
        self.assertIsNotNone(targets)
        self.assertEqual(set(targets),set(boundary['targets']))
        self.assertEqual(targets['0'],[3,0])
        self.assertNotIn(targets['2'], [[3,0],[4,0]])
        self.assertEqual(len({tuple(p) for p in targets.values()}),5)

    def test_budget_exhaustion_returns_last_committed_feasible_schedule(self):
        result = self.outcome
        self.assertLessEqual(result['candidate_evaluations'],self.options['max_evaluations'])
        self.assertEqual(result['status'],'budget_exhausted_with_incumbent')
        self.assertEqual(result['final_schedule_sha256'],result['accepted_history'][-1]['schedule_sha256'])
        self.assertTrue(result['incumbent']['evaluation']['accepted_schedule'])

    def test_numerical_strictness_ties_nan_and_infinite_error(self):
        self.assertFalse(strict_improvement(1.,1.,1e-12))
        self.assertFalse(strict_improvement(1.-5e-13,1.,1e-12))
        self.assertTrue(strict_improvement(1.-2e-12,1.,1e-12))
        self.assertFalse(strict_improvement(math.inf,1.,0))
        self.assertFalse(strict_improvement(math.inf,math.inf,0))
        self.assertFalse(strict_improvement(math.nan,1.,0))
        self.assertTrue(strict_improvement(1.,math.inf,0))
        self.assertEqual(total_E({'budget':{'total_E_infinite':True}}),math.inf)

    def test_deterministic_candidate_order_decisions_and_final_rng(self):
        again = self.run_repair()
        keys = ['candidate_id','kind','boundary_key','actual_full_E','decision','accepted']
        self.assertEqual([{k:a[k] for k in keys} for a in again['audit']],
                         [{k:a[k] for k in keys} for a in self.outcome['audit']])
        self.assertEqual(again['final_schedule_sha256'],self.outcome['final_schedule_sha256'])
        self.assertEqual(again['incumbent']['compilation']['random_state_after_sha256'],
                         self.outcome['incumbent']['compilation']['random_state_after_sha256'])

    def test_downstream_heating_time_and_exposure_agree_with_full_evaluator(self):
        for value in [self.base,self.outcome['incumbent']]:
            scored = evaluate(value['evaluation']['schedule'])
            compilation = value['compilation']
            self.assertAlmostEqual(compilation['physical_clock_us'],scored['makespan_us'],places=8)
            for q,n in compilation['statistics']['predicted_prefix_n_by_qubit'].items():
                self.assertAlmostEqual(n,scored['final_n_by_physical_atom'][scored['final_physical_carriers'][q]],places=12)
            for q,t in compilation['weighted_exposure_us'].items():
                self.assertAlmostEqual(t,scored['per_qubit_exposure'][q]['weighted_exposure_us'],places=7)

    def test_snapshot_physics_matches_independent_prefix_replay(self):
        from implementation.repair.evaluation import prefix_objective
        value = self.base
        for boundary in value['compilation']['repair_boundaries'][::3]:
            # Prefix scoring independently checks occupancy, gates, trap state and timing.
            self.assertGreaterEqual(prefix_objective(value,boundary,include_transition=False),0.)
            state=boundary['prefix_state']
            i,_,_=placement_span(value['evaluation']['schedule'],boundary)
            prefix=value['evaluation']['schedule']['events'][:i]
            end=max((e['start_us']+e['duration_us'] for e in prefix),default=0.)
            self.assertAlmostEqual(state['clock_us'],end,places=8)
            self.assertEqual(set(state['positions']),set(state['physical_carriers']))
            self.assertTrue(all(v=='SLM' for v in state['traps'].values()))
            self.assertEqual(state['cooling_resources'],[])

    def test_cooperative_stop_wall_cap_and_checkpoint_failure_return_incumbent(self):
        self.assertEqual(self.run_repair(stop_check=lambda:True)['status'],'stopped_with_incumbent')
        result=self.run_repair(options={**self.options,'max_repair_seconds':0.})
        self.assertEqual(result['status'],'wall_budget_exhausted')
        self.assertEqual(result['candidate_evaluations'],0)
        def fail(*args):
            raise OSError('injected checkpoint failure')
        result=self.run_repair(checkpoint=fail)
        self.assertEqual(result['status'],'checkpoint_failure_with_incumbent')
        self.assertLess(result['final_E'],result['original_E'])
        self.assertTrue(result['incumbent']['evaluation']['accepted_schedule'])

    def test_no_improvement_case_and_explicit_baseline_failure(self):
        case=no_improvement_case()
        result=repair(case,self.look,self.assign,self.profile,self.options)
        self.assertEqual(result['candidate_evaluations'],0)
        self.assertEqual(result['final_schedule_sha256'],result['original_schedule_sha256'])
        case=deepcopy(self.case);case['layout']=[]
        result=repair(case,self.look,self.assign,self.profile,self.options)
        self.assertEqual(result['status'],'baseline_failure')
        self.assertIsNone(result['incumbent'])

    def test_supplied_baseline_identity_and_cached_score_are_not_trusted(self):
        baseline=deepcopy(self.base);baseline['recipe_sha256']='incorrect'
        self.assertEqual(self.run_repair(baseline=baseline)['status'],'baseline_failure')
        baseline=deepcopy(self.base)
        baseline['evaluation']['result']['budget']['total_E']=-100.
        result=self.run_repair(baseline=baseline)
        self.assertEqual(result['original_E'],total_E(self.base['evaluation']['result']))
        baseline['compilation']['instructions']='invalid\n'
        self.assertEqual(self.run_repair(baseline=baseline)['status'],'baseline_failure')

    def test_enabled_cooling_and_unsupported_controls_fail_explicitly(self):
        cooling=deepcopy(self.profile);cooling['cooling']['enabled']=True
        with self.assertRaisesRegex(ValueError,'cooling'):
            replay(self.case,self.look,self.assign,cooling)
        case=deepcopy(self.case);case['baseline_options']['enable_rft_hungarian_bias']=True
        with self.assertRaisesRegex(ValueError,'bias'):
            replay(case,self.look,self.assign,self.profile)
        options={**self.options,'max_evaluations':-1}
        with self.assertRaises(ValueError):validate_options(options)
        for value in [math.nan,math.inf,-1,True]:
            with self.assertRaises(ValueError):validate_options({**self.options,'improvement_tolerance_E':value})

    def test_independent_cz_truth_table_equivalence_all_basis_columns(self):
        expected=[tuple(g['qubits']) for g in self.case['circuit']['gates']]
        actual=[tuple(e['logical_qubit_ids']) for e in self.outcome['incumbent']['evaluation']['trace']['events'] if e['kind']=='gate']
        self.assertEqual(len(actual),len(expected))
        for bits in range(1<<self.case['circuit']['num_qubits']):
            phase=lambda gates:sum(((bits>>a)&1)*((bits>>b)&1) for a,b in gates)%2
            self.assertEqual(phase(expected),phase(actual))

    def test_full_original_qft5_semantics_after_repair_for_both_controls(self):
        from implementation.validation.full_circuit import verify_original
        self.__class__.semantic_proofs=[]
        for name in ['sum_distance','composite_bottleneck_expanded']:
            cfg=assignment_options(ROOT/('configs/variants/assignment.'+name+'.json'))
            value=repair(self.case,self.look,cfg,self.profile,self.options)
            proof=verify_original(value['incumbent']['evaluation']['trace'],
                ROOT/'benchmarks/current_baseline_v1/raw/fig4_qft/qft_5.qasm')['comparison']
            self.assertTrue(proof['equivalent_up_to_global_phase'])
            self.assertEqual(proof['basis_states'],32)
            self.assertLess(proof['maximum_absolute_error'],1e-12)
            self.assertFalse(proof['physical_validity_implied'])
            self.__class__.semantic_proofs.append({'assignment':name,**proof})

    def test_second_round_preserves_committed_prefix_and_visited_states(self):
        options=load_options(ROOT/'configs/variants/repair.standard.json')
        options['max_evaluations']=48
        result=self.run_repair(options=options)
        self.assertEqual(result['rounds'],2)
        self.assertLessEqual(result['candidate_evaluations'],48)
        plans=[fingerprint(a['override_plan']) for a in result['audit']]
        self.assertEqual(len(plans),len(set(plans)))
        self.assertTrue(all(a['valid'] and a['prefix_unchanged'] for a in result['audit']))
        self.assertTrue(result['accepted_history'])
        self.assertTrue(result['incumbent']['evaluation']['accepted_schedule'])
        self.assertLess(result['final_E'],result['original_E'])

    def test_previous_scientific_sources_and_frozen_studies_unchanged(self):
        start=json.loads((ROOT/'reports/phase_06/start_record.json').read_text())
        for name,digest in start['frozen_artifact_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
        for study,record in start['benchmark_manifests'].items():
            directory=ROOT/'runs'/study
            self.assertEqual(hashlib.sha256((directory/'manifest.json').read_bytes()).hexdigest(),record['manifest_sha256'])
            for name,digest in record['files'].items():
                self.assertEqual(hashlib.sha256((directory/name).read_bytes()).hexdigest(),digest,study+':'+name)
        directory=ROOT/'runs/phase05_matched_benchmark_v1'
        manifest=json.loads((directory/'manifest.json').read_text())
        self.assertEqual(hashlib.sha256((directory/'manifest.json').read_bytes()).hexdigest(),(directory/'manifest.sha256').read_text().strip())
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((directory/name).read_bytes()).hexdigest(),digest,name)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Use fresh output under btp_work')
    out.mkdir(parents=True)
    with (out/'unittest.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    files=list((ROOT/'implementation/repair').glob('*.py'))+list((ROOT/'configs/variants').glob('repair.*.json'))+[Path(__file__)]
    record={'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
        'artifact_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'command':sys.argv,'full_original_semantic_proofs':getattr(Acceptance,'semantic_proofs',[])}
    write(out/'result.json',record)
    print(json.dumps(record))
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
