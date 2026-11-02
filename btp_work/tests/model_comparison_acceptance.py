"""Verify matrix matching, bounded diagnostic equivalence and real detached runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import model_comparison as service
from model_comparison_worker import BenchmarkContext
from implementation.lookahead.integration import compile_schedule, load_core
from implementation.lookahead.potential import load_options
from run_phase04_pilot import cases

PYTHON = ROOT / '.venv/Scripts/python.exe'


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_base = ROOT / 'runs/phase01_frozen_baseline_v1'
        suffix = cls.out.name
        cls.base = ROOT / ('runs/model_comparison_smoke_baseline_' + suffix)
        cls.phase3 = ROOT / ('runs/model_comparison_smoke_phase3_' + suffix)
        cls.phase4 = ROOT / ('runs/model_comparison_smoke_phase4_' + suffix)
        cls.base.mkdir()
        # An independent smoke baseline has no active controller. Immutable
        # files are hard-linked for read-only reuse; mutable manifests and
        # test outputs are separate. The user's running study is untouched.
        for name in ['manifest.json', 'manifest.sha256']:
            shutil.copyfile(cls.original_base / name, cls.base / name)
        original_manifest = service.read(cls.original_base / 'manifest.json')
        for name in original_manifest['files']:
            target = cls.base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(cls.original_base / name, target)
        das = next(j for j in original_manifest['jobs'] if j['algorithm'] == 'dasatom')
        success = next((p for p, r in service.records(cls.original_base, das['target_id']) if r['status'] == 'ok'), None)
        if success is not None:
            for item in success.parent.rglob('*'):
                if item.is_file():
                    target = cls.base / item.relative_to(cls.original_base)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.link(item, target)
        cls.manifests = {}
        for track, path in [('phase3', cls.phase3), ('phase4', cls.phase4)]:
            if path.exists():
                raise ValueError('Acceptance studies already exist; use fresh suffixes')
            cls.manifests[track] = service.prepare(path, ROOT, cls.base, track)
        cls.baseline_manifest_sha = service.sha(cls.base / 'manifest.json')

    def launch(self, track, study, limit=1):
        env = os.environ.copy()
        env['BTP_WORK_ROOT'] = str(ROOT)
        result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(ROOT / 'tools/Start-ModelComparison.ps1'), '-Track', track,
            '-Study', str(study), '-Baseline', str(self.base), '-Limit', str(limit)], capture_output=True, text=True,
            encoding='utf-8', timeout=30, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            progress = service.read(study / 'progress.json')
            if progress['state'] in ['paused_at_limit', 'error', 'finished_with_issues_or_missing_sources']:
                return progress
            time.sleep(.25)
        self.fail('Detached smoke did not complete within 60 seconds')

    def test_01_all_paper_targets_and_frozen_inputs(self):
        three = self.manifests['phase3']
        four = self.manifests['phase4']
        self.assertEqual(len(three['jobs']), 132)
        self.assertEqual(len(four['jobs']), 66)
        self.assertEqual(len([j for j in three['jobs'] if j['algorithm'] == 'dasatom']), 66)
        self.assertEqual({j['target_id'] for j in four['jobs']},
                         {j['target_id'] for j in three['jobs'] if j['algorithm'] == 'rft'})
        self.assertEqual(four['variants'], service.VARIANTS)
        for job in four['jobs']:
            self.assertEqual(service.sha(self.phase4 / job['frozen_input']), job['expected_normalized_sha256'])
        service.verify(self.phase3, runtime=True)
        service.verify(self.phase4, runtime=True)

    def test_02_bounded_audits_preserve_production_instructions_and_rng(self):
        configs = [load_options(ROOT / 'configs/variants' / ('lookahead.' + name + '.json'))
                   for name in service.VARIANTS]
        for case in cases():
            schedule = [(name, [tuple(pair) for pair in pairs]) for name, pairs in case['schedule']]
            n = case['circuit']['num_qubits']
            geometry = case['geometry']
            slots = [[tuple(site) for site in slot] for slot in case['layout']]
            for config in configs:
                expected = compile_schedule(schedule, n, slots, geometry, case['baseline_options'],
                                            config, circuit=case['circuit'], routing_seed=42)
                context = BenchmarkContext(schedule, n, case['circuit'], config, geometry['spacing_um'])
                core = load_core(context)
                busiest = core.find_busiest_pairs(schedule)
                random.seed(42)
                instructions = core.generate_hardware_instructions(schedule,
                    core.create_initial_mapping(busiest, slots), busiest, n,
                    geometry['rows'], geometry['columns'], slots, geometry['r_blk'],
                    geometry['r_int'], options=core.CompilerOptions(**case['baseline_options']))
                self.assertEqual('\n'.join(instructions) + '\n', expected['instructions'])
                self.assertEqual(hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),
                                 expected['random_state_after_sha256'])
                self.assertLessEqual(len(context.decisions), 8)
                self.assertLessEqual(len(context.batches), 8)
                self.assertEqual(context.statistics()['completed_gate_count'], len(case['circuit']['gates']))

    def test_03_real_detached_phase3_rescore_and_resume(self):
        progress = self.launch('phase3', self.phase3)
        self.assertEqual(progress['state'], 'paused_at_limit', progress)
        summary = service.read(self.phase3 / 'summary.json')
        self.assertEqual(summary['target_status_counts']['ok'], 1)
        job = self.manifests['phase3']['jobs'][0]
        attempts = service.records(self.phase3, job['target_id'])
        row = attempts[0][1]['result']['rows'][0]
        self.assertTrue(row['accepted_schedule'])
        self.assertTrue(row['compilation_reused'])
        self.assertEqual(row['variant'], 'original_phase3')
        self.assertEqual(row['compile_seconds'], job['original_compile_seconds'])
        self.assertAlmostEqual(row['legacy_fidelity'], job['native']['shared_legacy_score']['Fidelity (DasAtom Model)'])
        self.assertNotEqual(row['extended_E'], row['legacy_E'])
        before = attempts[0][0].read_bytes()
        progress = self.launch('phase3', self.phase3)
        self.assertEqual(progress['state'], 'paused_at_limit', progress)
        self.assertEqual(service.read(self.phase3 / 'summary.json')['target_status_counts']['ok'], 2)
        self.assertEqual(len(service.records(self.phase3, job['target_id'])), 1)
        self.assertEqual(attempts[0][0].read_bytes(), before)

    def test_04_real_detached_phase4_exact_control_and_all_horizons(self):
        progress = self.launch('phase4', self.phase4)
        self.assertEqual(progress['state'], 'paused_at_limit', progress)
        job = self.manifests['phase4']['jobs'][0]
        record_path, record = service.records(self.phase4, job['target_id'])[0]
        self.assertEqual(record['status'], 'ok', record)
        rows = record['result']['rows']
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row['accepted_schedule'] for row in rows))
        self.assertEqual(len({row['profile_sha256'] for row in rows}), 1)
        self.assertEqual(len({row['geometry_sha256'] for row in rows}), 1)
        compatibility = service.read(record_path.parent / 'worker/compatibility.json')
        self.assertTrue(compatibility['instructions_exact'])
        self.assertTrue(compatibility['rng_after_exact'])
        self.assertEqual({row['h'] for row in rows if 'h' in row}, {1, 2, 4, 8})
        self.assertTrue(all(row['compile_seconds'] > 0 for row in rows))
        for name in service.VARIANTS:
            diag = service.read(record_path.parent / 'worker' / name / 'parking_diagnostics.json')
            self.assertLessEqual(len(diag['decisions_sample']), 8)
            self.assertEqual(diag['statistics']['gate_count'], diag['statistics']['completed_gate_count'])
        phase3 = service.records(self.phase3, job['target_id'])[0][1]['result']['rows'][0]
        self.assertEqual(rows[0]['extended_E'], phase3['extended_E'])

    def test_05_missing_dasatom_sources_stay_pending(self):
        manifest = self.manifests['phase3']
        missing = [j for j in manifest['jobs'] if j['algorithm'] == 'dasatom'
                   and not any(r['status'] == 'ok' for _, r in service.records(self.base, j['target_id']))]
        self.assertTrue(missing)
        self.assertIsNone(service.source_request(self.phase3, manifest, missing[0]))
        self.assertFalse(service.read(self.phase3 / 'summary.json')['matrix_complete'])

    def test_06_os_lock_and_source_tampering_detection(self):
        lock_path = self.out / 'exclusive.lock'
        handle = service.acquire(lock_path)
        try:
            self.assertIsNone(service.acquire(lock_path))
        finally:
            service.release(handle)
        fixture = self.out / 'tamper'
        fixture.mkdir()
        code = fixture / 'worker.py'
        code.write_text('original', encoding='utf-8')
        service.write(fixture / 'manifest.json', {'files': {'worker.py': service.sha(code)}})
        (fixture / 'manifest.sha256').write_text(service.sha(fixture / 'manifest.json'), encoding='ascii')
        code.write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Frozen comparison file changed'):
            service.verify(fixture)

    def test_07_saved_corrected_dasatom_can_use_same_model(self):
        manifest = self.manifests['phase3']
        job = next(j for j in manifest['jobs'] if j['algorithm'] == 'dasatom')
        source_info, seconds, timing_scope = service.source_request(self.phase3, manifest, job)
        request_path = self.out / 'dasatom_request.json'
        service.write(request_path, {'track': 'phase3', 'job': job, 'source': source_info,
            'original_compile_seconds': seconds, 'original_timing_scope': timing_scope,
            'geometry': {'rows': job['grid'], 'columns': job['grid'], 'r_int': 2, 'r_blk': 4, 'spacing_um': 3.0}})
        service.bounded.ROOT = ROOT
        record = service.bounded.bounded_job(job, 60, output_root=self.out / 'dasatom_smoke',
            worker_path=self.phase3 / 'frozen/tools/model_comparison_worker.py',
            router_path=self.phase3 / 'frozen/implementation/lookahead/integration.py',
            input_path=self.phase3 / job['frozen_input'],
            env_extra={'BTP_WORK_ROOT': str(ROOT), 'BTP_COMPARISON_REQUEST': str(request_path)})
        self.assertEqual(record['status'], 'ok', record)
        row = record['result']['rows'][0]
        self.assertEqual(row['algorithm'], 'dasatom')
        self.assertTrue(row['accepted_schedule'])
        self.assertTrue(row['compilation_reused'])
        self.assertEqual(row['compile_seconds'], seconds)

    def test_08_baseline_manifest_and_all_frozen_sources_unchanged(self):
        self.assertEqual(service.sha(self.original_base / 'manifest.json'), self.baseline_manifest_sha)
        self.assertEqual(service.sha(self.base / 'manifest.json'), self.baseline_manifest_sha)
        service.baseline_service.verify(self.base)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use a new acceptance output under btp_work')
    out.mkdir(parents=True)
    Acceptance.out = out
    with (out / 'unittest.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    summary = {'tests': result.testsRun, 'failures': len(result.failures),
               'errors': len(result.errors), 'successful': result.wasSuccessful()}
    service.write(out / 'result.json', summary)
    print(json.dumps(summary))
    if not result.wasSuccessful():
        print((out / 'unittest.txt').read_text(encoding='utf-8'))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
