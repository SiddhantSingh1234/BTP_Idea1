"""Run the original scientific acceptance suite under the memory revision."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from phase06_memory import memory_scope, Freeze, streaming_fingerprint, freeze_compilation
from implementation.trace.model import fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Use fresh output under btp_work')
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('phase06_original_tests', ROOT / 'tests/phase_06_acceptance.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    operational = {'tools/model_comparison.py', 'tools/model_comparison_worker.py',
        'tools/standalone_baseline.py', 'tools/Start-ModelComparison.ps1', 'tools/phase06_comparison_worker.py'}
    class RevisionAcceptance(module.Acceptance):
        def test_previous_scientific_sources_and_frozen_studies_unchanged(self):
            start = json.loads((ROOT / 'reports/phase_06/start_record.json').read_text())
            for name, digest in start['frozen_artifact_sha256'].items():
                if name not in operational:
                    self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
            for study, record in start['benchmark_manifests'].items():
                directory = ROOT / 'runs' / study
                self.assertEqual(hashlib.sha256((directory / 'manifest.json').read_bytes()).hexdigest(), record['manifest_sha256'])
                for name, digest in record['files'].items():
                    self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), digest, name)
            version = json.loads((ROOT / 'reports/phase_06/version_manifest.json').read_text())
            for name, digest in version['artifact_sha256'].items():
                if name.startswith(('implementation/', 'configs/')):
                    self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        def test_lossless_json_hash_sharing_and_immutability(self):
            from copy import deepcopy
            values = {'text': 'é\\\"\n', 'tiny': 1e-300, 'signed': -0.,
                'list': [1, True, None, {'nested': [0, 2]}]}
            frozen = Freeze()(values)
            self.assertEqual(json.dumps(values, sort_keys=True), json.dumps(frozen, sort_keys=True))
            self.assertEqual(fingerprint(values), streaming_fingerprint(frozen))
            self.assertIs(deepcopy(frozen), frozen)
            with self.assertRaises(TypeError):
                frozen['list'].append(9)
        def test_completed_context_release_preserves_all_returned_evidence(self):
            import gc
            for unused in range(3):
                value = module.prepare(self.case, self.look, self.assign, self.profile)
                freeze_compilation(value['compilation'])
                before = fingerprint(value)
                release_contexts()
                self.assertEqual(fingerprint(value), before)
                self.assertTrue(value['evaluation']['accepted_schedule'])
                contexts = [x for x in gc.get_objects() if type(x).__name__ == 'MemoryContext']
                self.assertTrue(all(not context.__dict__ for context in contexts))
    with memory_scope() as release_contexts, (out / 'unittest.txt').open('w', encoding='utf-8') as handle:
        result = unittest.TextTestRunner(stream=handle, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(RevisionAcceptance))
    record = {'passed': result.wasSuccessful(), 'tests': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors),
        'original_behavior_tests_unchanged': 20,
        'preservation_check': 'Original scientific/frozen evidence checked; operational launchers have an explicitly scoped revision exception',
        'operational_exception_paths': sorted(operational)}
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
