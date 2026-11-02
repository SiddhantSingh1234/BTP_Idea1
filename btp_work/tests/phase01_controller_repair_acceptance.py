"""Windows regression coverage for suspended worker ownership and recovery."""
import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import run_paper_focus as runner
import standalone_baseline as service
from standalone_baseline_acceptance import Acceptance


class RepairRegression(unittest.TestCase):
    def test_60_real_venv_launches_complete_without_assignment_race(self):
        for index in range(60):
            process, kernel, handle = runner.start_owned_process(
                [sys.executable, '-B', '-c', 'print(123)'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                out, err = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, (index, err))
                self.assertEqual(out.strip(), b'123')
            finally:
                kernel.CloseHandle(handle)
                if process.poll() is None: process.kill(); process.wait()

    def test_job_contains_suspended_root_before_python_can_spawn(self):
        resume = runner.resume_initial_thread
        checked = []
        def inspect(pid):
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x0400, False, pid)
            self.assertTrue(handle)
            try:
                inside = wintypes.BOOL()
                self.assertTrue(kernel.IsProcessInJob(handle, None, ctypes.byref(inside)))
                self.assertTrue(inside.value)
                self.assertEqual(runner.process_family(pid), {pid})
                checked.append(pid)
            finally: kernel.CloseHandle(handle)
            resume(pid)
        with patch.object(runner, 'resume_initial_thread', inspect):
            process, kernel, handle = runner.start_owned_process(
                [sys.executable, '-B', '-c', 'pass'])
        try: self.assertEqual(process.wait(timeout=5), 0)
        finally: kernel.CloseHandle(handle)
        self.assertEqual(len(checked), 1)

    def test_resume_failure_kills_suspended_worker(self):
        created = []
        popen = subprocess.Popen
        def track(*args, **kwargs):
            process = popen(*args, **kwargs); created.append(process); return process
        with patch.object(runner.subprocess, 'Popen', track), patch.object(
                runner, 'resume_initial_thread', side_effect=OSError('injected resume failure')):
            with self.assertRaisesRegex(OSError, 'injected resume failure'):
                runner.start_owned_process([sys.executable, '-B', '-c', 'import time; time.sleep(30)'])
        self.assertEqual(len(created), 1)
        self.assertIsNotNone(created[0].poll())

    def test_retry_scope_excludes_compiler_failures_and_repaired_attempts(self):
        original = {'status': 'error', 'result': None, 'peak_working_set_bytes': 0,
            'worker_artifact_sha256': {}, 'process_wall_seconds': .05,
            'monitor_error': {'type': 'PermissionError', 'message': '[WinError 5] Access is denied.'}}
        self.assertTrue(runner.retryable_controller_failure(original))
        for update in [{'status': 'timeout'}, {'result': {'status': 'error'}},
                       {'peak_working_set_bytes': 10}, {'process_wall_seconds': 10},
                       {'worker_artifact_sha256': {'worker/result.json': 'abc'}},
                       {'launcher_protocol': 'windows-suspended-job-v1'},
                       {'monitor_error': {'type': 'ValueError', 'message': 'compiler bug'}}]:
            self.assertFalse(runner.retryable_controller_failure({**original, **update}), update)

    def test_repair_bundle_tampering_is_rejected(self):
        study = self.out / 'repair_fixture'; bundle = study / 'controller_repair_v1'
        bundle.mkdir(parents=True)
        service.write(study / 'manifest.json', {'fixture': True})
        code = bundle / 'runner.py'; code.write_text('original')
        service.write(bundle / 'manifest.json', {'parent_manifest_sha256': service.sha(study / 'manifest.json'),
            'files': {'runner.py': service.sha(code)}})
        (bundle / 'manifest.sha256').write_text(service.sha(bundle / 'manifest.json'))
        service.verify_controller_repair(study)
        code.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Controller repair file changed'):
            service.verify_controller_repair(study)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists(): raise ValueError('Use new output under btp_work')
    out.mkdir(parents=True)
    Acceptance.study = ROOT / 'runs/standalone_acceptance_v3'
    Acceptance.out = out
    RepairRegression.out = out
    suite = unittest.TestSuite()
    for name in unittest.defaultTestLoader.getTestCaseNames(Acceptance):
        if name != 'test_detached_launcher_completed_real_validated_compile':
            suite.addTest(Acceptance(name))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(RepairRegression))
    with (out / 'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    service.write(out / 'result.json', {'tests': result.testsRun, 'successful': result.wasSuccessful(),
        'failures': len(result.failures), 'errors': len(result.errors), 'command': sys.argv})
    print((out / 'result.json').read_text())
    if not result.wasSuccessful(): print((out / 'tests.txt').read_text())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': raise SystemExit(main())
