"""Independent coverage, input identity, tiny semantics and replay checks."""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import sys
import unittest

WORK = Path(__file__).resolve().parents[1]
os.environ.update(MPLCONFIGDIR=str(WORK / '.compiler-tools/matplotlib'), PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode = True
sys.path.insert(0, str(WORK / 'tools'))
sys.path.insert(0, str(WORK / 'vendor/NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a/src'))
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
import numpy as np
import compiler_core as core
from benchmark_runner import ladder_variants
from phase00_smoke import replay

OUT = WORK / 'reports/phase_01/tests_01'
OUT.mkdir(parents=True, exist_ok=False)
PLAN = json.loads((WORK / 'runs/current_baseline/study_v1/plan.json').read_text())


class Acceptance(unittest.TestCase):
    def test_complete_paper_target_grid_coverage(self):
        primary = [j for j in PLAN['jobs'] if j['priority'] == 0 and j['repetition'] == 1]
        self.assertEqual(len(primary), 132)
        self.assertEqual({(j['case'],j['grid'],j['algorithm']) for j in primary if j['family']=='fig4_qft'},
            {(f'qft_{n}',g,a) for n in range(5,61,5) for g in [11,20,35] for a in ['rft','dasatom']})
        expected = {Path(e['path']).stem for e in json.loads((WORK/'configs/benchmarks/reproduction_manifest.json').read_text())['tableII']}
        self.assertEqual({(j['case'],j['grid'],j['algorithm']) for j in primary if j['family']=='tableII'},
            {(n,g,a) for n in expected for g in [11,35] for a in ['rft','dasatom']})

    def test_frozen_input_hashes_and_declared_prefix_distinction(self):
        for item in PLAN['inputs']:
            path = WORK / item['raw_path']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['raw_sha256'])
            circuits = {}
            for policy, normalized in item['normalized'].items():
                p = WORK / normalized['path']
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), normalized['sha256'])
                circuits[policy] = QuantumCircuit.from_qasm_file(str(p))
            def operands(qc):
                return [(ins.operation.name,tuple(qc.find_bit(q).index for q in ins.qubits)) for ins in qc.data]
            self.assertEqual(operands(circuits['native']), operands(circuits['active_prefix']))
            self.assertEqual(circuits['native'].num_qubits, item['declared_N'])
            self.assertEqual(circuits['active_prefix'].num_qubits, item['active_prefix_N'])

    def test_tiny_CZ_semantics_against_independent_basis_phases(self):
        pairs = [(0,1),(2,3),(0,2),(1,2)]
        qc = QuantumCircuit(4)
        for a,b in pairs:
            qc.cz(a,b)
        diagonal = [(-1)**sum(((basis >> a)&1)*((basis >> b)&1) for a,b in pairs) for basis in range(16)]
        self.assertTrue(np.array_equal(Operator(qc).data, np.diag(diagonal)))

    def test_replay_rejects_missing_gate_and_bad_move(self):
        qc = QuantumCircuit(2)
        qc.cz(0,1)
        initial = '[INITIAL PLACEMENT]\n  PLACE qubit 0 at position (0, 0)\n  PLACE qubit 1 at position (0, 1)\n'
        self.assertFalse(replay(initial,qc)['valid_within_coverage'])
        bad = initial+'[SHUTTLING]\n  SHUTTLE qubit 0 from (1, 1) to (0, 1)\n[EXECUTE]\n  CZ q[0], q[1]\n'
        self.assertFalse(replay(bad,qc)['valid_within_coverage'])

    def test_actual_full_compiler_tiny_seeded_cases(self):
        summaries = []
        for seed in range(5):
            rng = random.Random(seed)
            qc = QuantumCircuit(4)
            for a,b in [(0,1),(2,3),(0,2)]+[tuple(rng.sample(range(4),2)) for _ in range(9)]:
                qc.cz(a,b)
            path = OUT / f'tiny_{seed}.qasm'
            path.write_text(qasm2.dumps(qc)+'\n',encoding='utf-8')
            _,schedule,n = core.analyze_qasm_file(str(path))
            for variant in ['7_dynamic_slot_01q_move','8_optimized_eviction']:
                random.seed(42)
                instructions = core.generate_hardware_instructions(schedule,{},[],n,3,3,
                    [[(0,0),(0,1)],[(2,0),(2,1)]],2,1,options=ladder_variants()[variant])
                text = '\n'.join(instructions)
                (OUT/f'tiny_{seed}_{variant}.txt').write_text(text,encoding='utf-8')
                report = replay(text,qc,1,2,3)
                summaries.append({'seed':seed,'variant':variant,'replay':report})
        (OUT/'tiny_replays.json').write_text(json.dumps(summaries,indent=2)+'\n',encoding='utf-8')
        self.assertTrue(all(s['replay']['valid_within_coverage'] for s in summaries), summaries)


if __name__ == '__main__':
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    (OUT/'output.txt').write_text(stream.getvalue(),encoding='utf-8')
    (OUT/'result.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),
        'errors':len(result.errors),'passed':result.wasSuccessful(),
        'scope':'coverage/identity/tiny semantics and boundary replay only; no full original-unitary or continuous path proof'},indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue())
    raise SystemExit(0 if result.wasSuccessful() else 1)
