"""Predetermined development/evaluation circuits; no outcome-based case selection."""
from copy import deepcopy
from pathlib import Path
import random
from implementation.trace.model import circuit_from_pairs, read_cz_qasm, fingerprint
from implementation.lookahead.integration import load_core
from implementation.lookahead.fixtures import serialized_case

ROOT = Path(__file__).resolve().parents[2]


def generated_case(seed, *, n=8, depth=8, static=False):
    rng = random.Random(seed)
    layers = []
    for layer in range(depth):
        qubits = list(range(n))
        rng.shuffle(qubits)
        layers.append(sorted(tuple(sorted(qubits[i:i + 2])) for i in range(0, n, 2)))
    import json
    baseline = json.loads((ROOT / 'configs/baselines/rft_snapshot.json').read_text())
    options = deepcopy(baseline['options'])
    if static:
        options.update(enable_keep_adjacent=False, enable_one_qubit_move=False)
    circuit = circuit_from_pairs(n, [pair for pairs in layers for pair in pairs])
    return {'case_id': ('static_' if static else '') + 'random_matching_n' + str(n) + '_seed' + str(seed),
        'schedule': [('Time ' + str(i + 1), pairs) for i, pairs in enumerate(layers)],
        'circuit': circuit, 'layout': deepcopy(baseline['layout']['frozen_slots']),
        'geometry': {'rows': 11, 'columns': 11, 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.},
        'baseline_options': options, 'input_kind': 'seeded matching-layer microbenchmark; not QAOA/QV',
        'input_sha256': fingerprint(circuit), 'generator_seed': seed, 'static_adversary': static}


def development_cases():
    return [generated_case(seed) for seed in (100, 101, 102, 103)]


def evaluation_cases():
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    from run_phase04_pilot import cases
    out = deepcopy(cases())
    baseline = out[0]
    core = load_core()
    for n in (10, 15):
        path = ROOT / 'benchmarks/current_baseline_v1/normalized/fig4_qft' / ('qft_' + str(n) + '_native.qasm')
        _, schedule, declared = core.analyze_qasm_file(str(path))
        item = deepcopy(baseline)
        item.update(case_id='qft' + str(n) + '_ladder7', schedule=schedule,
                    circuit=read_cz_qasm(path), input_path=str(path.relative_to(ROOT)),
                    input_sha256=__import__('hashlib').sha256(path.read_bytes()).hexdigest())
        if declared != item['circuit']['num_qubits']:
            raise ValueError('Circuit register mismatch')
        out.append(item)
    out += [generated_case(seed) for seed in (200, 201, 202, 203)]
    out.append(generated_case(204, static=True))
    return out
