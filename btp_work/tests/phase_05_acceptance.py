"""Phase05 independent oriented oracle, predictor and unchanged-router acceptance."""
import argparse
from copy import deepcopy
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from implementation.assignment.matching import solve, AssignmentInfeasible, covering_matching
from implementation.assignment.costs import make_problem, assign, load_options, validate_options, candidates
from implementation.assignment.integration import compile_schedule
from implementation.assignment.oracle import enumerate_optimum
from implementation.lookahead.events import FutureEventIndex
from implementation.lookahead.potential import load_options as load_lookahead
from implementation.lookahead.integration import compile_schedule as phase04
from implementation.lookahead.evaluation import evaluate_compilation, pilot_geometry_profile
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.physics import local_batch_cost
from implementation.movement_error.schedule import make_schedule
from implementation.movement_error.evaluator import evaluate
from implementation.adapters.upstream import build_trace
from implementation.trace.model import circuit_from_pairs
from run_phase04_pilot import cases


def config(name='sum_distance'):
    return load_options(ROOT / 'configs/variants' / ('assignment.' + name + '.json'))


def lookahead():
    return load_lookahead(ROOT / 'configs/variants/lookahead.next_events_h4.json')


def profile():
    return load_profile(ROOT / 'configs/hardware/extended_no_cooling.json')


def problem(pairs, slots, current, cfg=None, committed=None, committed_slots=()):
    n = max([q for pair in pairs for q in pair] + list((committed or {}).keys()) + list(current.keys()) + [1]) + 1
    circuit = circuit_from_pairs(n, pairs)
    index = FutureEventIndex([('Time 1', pairs)], n, circuit)
    active = set(index.gate_layer)
    return make_problem(pairs, slots, current, committed or {}, committed_slots,
        {'rows': 12, 'columns': 12, 'r_int': 2, 'r_blk': 3, 'spacing_um': 3.},
        index=index, layer=0, completed=set(), active=active,
        n_by_qubit={q: 0. for q in range(n)}, profile=profile(), lookahead=lookahead(), config=cfg or config())


class Acceptance(unittest.TestCase):
    def test_oriented_matrix_optima_against_independent_enumeration(self):
        rng = random.Random(5105)
        checked = 0
        for m in range(1, 5):
            for _ in range(100):
                s = rng.randint(m, min(6, m + 2))
                oriented = tuple(tuple(tuple(math.inf if rng.random() < .25 else rng.randint(-3, 20)
                                  for _ in range(2)) for _ in range(s)) for _ in range(m))
                costs = tuple(tuple(min(entry) for entry in row) for row in oriented)
                for objective in ('sum', 'bottleneck_sum'):
                    expected = enumerate_optimum(oriented, objective)
                    if expected is None:
                        with self.assertRaises(AssignmentInfeasible):
                            solve(costs, objective)
                    else:
                        actual = solve(costs, objective)
                        key = (actual.maximum, actual.total) if objective == 'bottleneck_sum' else (actual.total,)
                        self.assertEqual(key, expected['objective'])
                        self.assertEqual(len(set(actual.columns)), m)
                    checked += 1
        self.assertEqual(checked, 800)

    def test_six_rows_rectangular_all_orientations(self):
        rng = random.Random(6105)
        oriented = tuple(tuple(tuple(rng.randint(0, 30) for _ in range(2)) for _ in range(7)) for _ in range(6))
        for objective in ('sum', 'bottleneck_sum'):
            expected = enumerate_optimum(oriented, objective)
            result = solve([[min(x) for x in row] for row in oriented], objective)
            self.assertEqual((result.maximum, result.total) if objective == 'bottleneck_sum' else (result.total,),
                             expected['objective'])

    def test_hall_forbidden_infinite_and_insufficient_columns(self):
        for values in [[[1], [2]], [[0, math.inf], [1, math.inf]], [[math.inf, math.inf]]]:
            self.assertIsNone(covering_matching(values))
            for objective in ('sum', 'bottleneck_sum'):
                with self.assertRaises(AssignmentInfeasible):
                    solve(values, objective)
        self.assertEqual(solve([[math.inf, 2, 9], [1, math.inf, 8]]).columns, (1, 0))
        for values in [[[math.nan]], [[-math.inf]], [[0], [0, 1]]]:
            with self.assertRaises(ValueError):
                solve(values)

    def test_lower_sum_can_have_worse_bottleneck(self):
        values = [[0, 6], [6, 10]]
        summed = solve(values, 'sum')
        bottleneck = solve(values, 'bottleneck_sum')
        self.assertEqual((summed.maximum, summed.total), (10, 10))
        self.assertEqual((bottleneck.maximum, bottleneck.total), (6, 12))

    def test_ties_empty_and_repeated_deterministic_order(self):
        self.assertEqual(solve([]).columns, ())
        first = solve([[1, 1, 1], [1, 1, 1]]).columns
        for _ in range(5):
            self.assertEqual(solve([[1, 1, 1], [1, 1, 1]]).columns, first)

    def test_scored_orientation_materialized_exactly(self):
        p = problem([(0, 1)], [[(1, 1), (2, 1)]], {0: (0, 0), 1: (0, 1)})
        mapping, selected, result = assign(p, 'sum')
        self.assertEqual(selected[0]['orientation'], 1)
        self.assertEqual(mapping, {0: (2, 1), 1: (1, 1)})
        self.assertAlmostEqual(result.total, 3 * (1 + math.sqrt(5)))
        legacy_first_endpoint_orientation = 3 * (2 + math.sqrt(2))
        self.assertGreater(legacy_first_endpoint_orientation, result.total)

    def test_legality_committed_geometry_and_mutually_safe_columns(self):
        cfg = config()
        p = problem([(0, 1)], [[(0, 0), (0, 1)]], {0: (3, 0), 1: (3, 1), 2: (0, 0)},
                    cfg=cfg, committed={2: (0, 0)})
        with self.assertRaises(AssignmentInfeasible):
            assign(p, 'sum')
        for slots in [[[(0, 0), (0, 1)], [(0, 2), (0, 3)]], [[(0, 0), (0, 1)], [(0, 0), (0, 1)]]]:
            with self.assertRaises(ValueError):
                problem([(0, 1)], slots, {0: (5, 0), 1: (5, 1)})
        p = problem([(0, 1)], [[(0, 0), (9, 9)]], {0: (5, 0), 1: (5, 1)})
        with self.assertRaises(AssignmentInfeasible):
            assign(p, 'sum')

    def test_frozen_committed_conflicts_and_snapshot(self):
        cfg = config('composite_bottleneck')
        current = {0: (0, 0), 1: (0, 1), 2: (2, 0)}
        committed = {2: (1, 0)}
        p = problem([(0, 1)], [[(4, 0), (4, 1)]], current, cfg, committed)
        saved = p.oriented_costs
        self.assertGreater(p.details[0][0][0]['committed_conflicts'], 0)
        current[2] = (11, 11)
        committed[2] = (11, 10)
        self.assertEqual(p.oriented_costs, saved)
        self.assertEqual(p.committed_moves, ((2, (2, 0), (1, 0)),))

    def test_two_new_rows_conflict_not_encoded_as_exact_pairwise_objective(self):
        # Each row is a compatible horizontal translation; reversing their
        # row order between source and target makes the two rows incompatible.
        p = problem([(0, 1), (2, 3)], [[(4, 0), (4, 1)], [(0, 0), (0, 1)]],
                    {0: (0, 0), 1: (0, 1), 2: (4, 0), 3: (4, 1)}, config('composite_bottleneck'))
        self.assertEqual(p.details[0][0][0]['committed_conflicts'], 0)
        self.assertEqual(p.details[1][1][0]['committed_conflicts'], 0)
        from implementation.validation.checker import line_compatible
        self.assertFalse(line_compatible((0, 0), (4, 0), (4, 0), (0, 0)))

    def test_candidate_expansion_is_independent(self):
        slots = [[(0, 0), (0, 1)], [(4, 0), (4, 1)], [(8, 0), (8, 1)]]
        self.assertEqual(len(candidates(slots, (0, 0), 1, config('sum_distance'))), 1)
        self.assertEqual(len(candidates(slots, (0, 0), 1, config('sum_distance_expanded'))), 2)
        self.assertEqual(len(candidates(slots, (0, 0), 1, config('sum_distance_all'))), 3)
        for key, value in [('expansion_factor', 0), ('candidate_policy', 'unbounded'), ('objective', 'fake')]:
            cfg = config()
            cfg[key] = value
            with self.assertRaises(ValueError):
                validate_options(cfg)

    def test_predictor_matches_common_evaluator_for_one_legal_batch(self):
        p = profile()
        circuit = circuit_from_pairs(2, [(0, 1)])
        geo = {'rows': 6, 'columns': 6, 'r_int': 2, 'r_blk': 3, 'spacing_um': 3.}
        groups = [
            {'kind': 'initialize', 'items': [{'qubit': 0, 'site': [0, 0]}, {'qubit': 1, 'site': [0, 2]}]},
            {'kind': 'move', 'items': [{'qubit': 0, 'from': [0, 0], 'to': [0, 1], 'cause': 'explicit_nonparking'}]},
            {'kind': 'gate', 'items': [{'qubits': [0, 1], 'sites': [[0, 1], [0, 2]]}]}]
        trace = build_trace(groups, circuit, pilot_geometry_profile(geo), timing='two_transfer_stages')
        actual = evaluate(make_schedule(trace, p, 'retime'))
        pred = local_batch_cost({0: 0., 1: 0.}, {0: 3., 1: 0.}, p, next_cz_pairs=[(0, 1)])
        self.assertEqual(actual['status'], 'ok')
        terms = actual['budget']['terms']
        incremental = sum(terms[k] for k in ('E_transfer', 'E_heating_gate', 'E_movement_loss', 'E_decoherence'))
        incremental -= 2 * p['noise']['cz_duration_us'] / p['exposure']['T2_us']
        self.assertAlmostEqual(pred['total_E'], incremental, places=13)

    def test_future_term_restores_cross_qubit_scale_and_repeated_events(self):
        layers = [('Time 1', [(0, 1)]), ('Time 2', [(0, 2)]),
                  ('Time 3', [(1, 3)]), ('Time 4', [(0, 2)])]
        circuit = circuit_from_pairs(4, [(0, 1), (0, 2), (1, 3), (0, 2)])
        index = FutureEventIndex(layers, 4, circuit)
        p = make_problem([(0, 1)], [[(1, 0), (1, 1)]],
            {0: (0, 0), 1: (0, 1), 2: (3, 0), 3: (9, 0)}, {}, [],
            {'rows': 12, 'columns': 12, 'r_int': 2, 'r_blk': 3, 'spacing_um': 3.},
            index=index, layer=0, completed=set(), active={'g000000'},
            n_by_qubit=dict.fromkeys(range(4), 0.), profile=profile(),
            lookahead=lookahead(), config=config('composite_bottleneck'))
        expected_um = (.9 + .9**3) * 6 + .9**2 * math.sqrt(65) * 3
        self.assertAlmostEqual(p.details[0][0][0]['future_raw_um'], expected_um)
        self.assertAlmostEqual(p.details[0][0][0]['components']['future'], expected_um / (2 * 4 * 15))

    def test_optional_displaced_atom_prediction_counts_extra_transfers(self):
        args = ([(0, 1)], [[(5, 0), (5, 1)]], {0: (0, 0), 1: (0, 1), 2: (5, 0)})
        off = problem(*args, cfg=config('composite_bottleneck'))
        on = problem(*args, cfg=config('composite_with_displacements'))
        self.assertEqual(off.details[0][0][0]['displaced'], [])
        self.assertEqual(on.details[0][0][0]['displaced'][0]['qubit'], 2)
        self.assertEqual(off.details[0][0][0]['components']['transfer'], 1.)
        self.assertEqual(on.details[0][0][0]['components']['transfer'], 1.5)
        self.assertIn(2, on.details[0][0][0]['predicted']['n_after'])

    def test_phase04_passthrough_instructions_and_rng_exact(self):
        for case in cases():
            expected = phase04(case['schedule'], case['circuit']['num_qubits'], case['layout'],
                case['geometry'], case['baseline_options'], lookahead(), circuit=case['circuit'])
            actual = compile_schedule(case['schedule'], case['circuit']['num_qubits'], case['layout'],
                case['geometry'], case['baseline_options'], lookahead(), config('phase04_reference'),
                profile(), circuit=case['circuit'])
            self.assertEqual(actual['instructions'], expected['instructions'])
            self.assertEqual(actual['random_state_after_sha256'], expected['random_state_after_sha256'])

    def test_all_pilot_controls_validate_and_prefix_heating_matches(self):
        for case in cases():
            for name in ['sum_distance', 'bottleneck_time', 'composite_bottleneck',
                         'composite_bottleneck_expanded', 'composite_with_displacements']:
                actual = compile_schedule(case['schedule'], case['circuit']['num_qubits'], case['layout'],
                    case['geometry'], case['baseline_options'], lookahead(), config(name),
                    profile(), circuit=case['circuit'])
                scored = evaluate_compilation(actual, case['circuit'], case['geometry'], profile())
                self.assertTrue(scored['accepted_schedule'], (case['case_id'], name, scored['result']['validation']))
                carriers = scored['result']['final_physical_carriers']
                final = scored['result']['final_n_by_physical_atom']
                for q, n in actual['statistics']['predicted_prefix_n_by_qubit'].items():
                    self.assertAlmostEqual(n, final[carriers[q]], places=13)
                for record in actual['assignment_records']:
                    for entry in record.get('selected', []):
                        self.assertTrue(record['legal_mask'][entry['row']][entry['column']])
                        self.assertEqual(entry['cost'], record['cost_matrix'][entry['row']][entry['column']])

    def test_unmatched_zero_capacity_terminates_explicitly(self):
        case = cases()[0]
        with self.assertRaises((AssignmentInfeasible, ValueError)):
            compile_schedule(case['schedule'], case['circuit']['num_qubits'], [], case['geometry'],
                case['baseline_options'], lookahead(), config(), profile(), circuit=case['circuit'])

    def test_original_sources_and_frozen_benchmark_files_unchanged(self):
        start = json.loads((ROOT / 'reports/phase_05/start_record.json').read_text())
        for name, expected in start['frozen_artifact_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
        for name in ['phase01_frozen_baseline_v1', 'phase03_matched_benchmark_v1', 'phase04_matched_benchmark_v1']:
            study = ROOT / 'runs' / name
            manifest = json.loads((study / 'manifest.json').read_text())
            for path, expected in manifest['files'].items():
                self.assertEqual(hashlib.sha256((study / path).read_bytes()).hexdigest(), expected, name + ':' + path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh output under btp_work')
    out.mkdir(parents=True)
    with (out / 'unittest.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    files = list((ROOT / 'implementation/assignment').glob('*.py')) + list((ROOT / 'configs/variants').glob('assignment.*.json')) + [Path(__file__).resolve()]
    summary = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'successful': result.wasSuccessful(), 'oriented_random_objective_checks': 800,
        'artifact_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'command': sys.argv}
    (out / 'result.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'artifact_sha256'}))
    if not result.wasSuccessful():
        print((out / 'unittest.txt').read_text(encoding='utf-8'))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
