"""Fixed development and evaluation instances, distinct generator seeds."""
from copy import deepcopy
from implementation.assignment.fixtures import generated_case, evaluation_cases as phase05_cases


def no_improvement_case():
    case = generated_case(699, n=2, depth=1)
    case['case_id'] = 'two_qubit_no_routed_transition'
    case['input_kind'] = 'analytic no-improvement fixture; initialization/CZ only'
    return case


def development_cases():
    smoke = deepcopy(phase05_cases()[0])
    smoke['input_kind'] = 'known QFT5 regression/development smoke, not held-out'
    return [smoke] + [generated_case(seed, depth=6) for seed in (300, 301, 302, 303)]


def evaluation_cases():
    # Named prior benchmarks are regression cases; random seeds are unseen by
    # the development study. This is a pilot, not the final Phase07 evaluation.
    cases = [deepcopy(case) for case in phase05_cases()
             if case['case_id'] in {'tableII_ladder7', 'forced_eviction_ladder6',
                'serialized_ladder7', 'qft10_ladder7', 'qft15_ladder7'}]
    return cases + [generated_case(seed, depth=6) for seed in (400, 401, 402, 403)] + [no_improvement_case()]
