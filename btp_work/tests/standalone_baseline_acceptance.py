"""Real Windows process, freeze and resume checks for the detached baseline."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
import standalone_baseline as service
import run_paper_focus as runner
PYTHON = ROOT / '.venv/Scripts/python.exe'


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = service.verify(cls.study, runtime=True)
        cls.job = next(j for j in cls.manifest['jobs'] if j['algorithm'] == 'dasatom')
        cls.input = cls.study / cls.job['frozen_input']
        cls.fake = cls.out / 'slow_worker.py'
        cls.fake.write_text("import time\ntime.sleep(30)\n", encoding='utf-8')

    def test_detached_launcher_completed_real_validated_compile(self):
        value = service.status(self.study)
        self.assertFalse(value['controller_lock_held'])
        self.assertEqual(value['progress']['state'], 'paused_at_limit')
        self.assertEqual(value['summary']['new_corrected_dasatom_successes'], 1)
        paths = list((self.study / 'measurements').glob('*/attempt_*/attempt_record.json'))
        self.assertEqual(len(paths), 1)
        record = service.read(paths[0])
        self.assertEqual(record['status'], 'ok')
        self.assertEqual(record['worker_sha256'], service.sha(self.study / 'frozen/tools/corrected_dasatom_worker.py'))
        self.assertEqual(record['result']['code_root'], str(self.study / 'frozen'))
        self.assertEqual(record['result']['hash_seed'], '0')
        self.assertGreater(record['result']['corrected_compile_seconds'], 0)
        for relative, expected in record['worker_artifact_sha256'].items():
            self.assertEqual(service.sha(paths[0].parent / relative), expected)
        validation = service.read(paths[0].parent / 'worker/validation.json')
        self.assertTrue(validation['structural_valid'])
        self.assertFalse(validation['fully_validated_within_model'])

    def test_duplicate_success_is_reused_without_new_attempt(self):
        before = list((self.study / 'measurements' / self.job['target_id']).glob('attempt_*'))
        result = runner.bounded_job(self.job, 30, output_root=self.study / 'measurements',
            worker_path=self.study / 'frozen/tools/corrected_dasatom_worker.py',
            router_path=self.study / 'frozen/implementation/corrected/dasatom_routes.py', input_path=self.input)
        self.assertEqual(result['status'], 'reused_corrected_compilation')
        self.assertEqual(before, list((self.study / 'measurements' / self.job['target_id']).glob('attempt_*')))

    def test_os_lock_rejects_second_controller(self):
        handle = service.lock(self.study)
        self.assertIsNotNone(handle)
        try:
            result = subprocess.run([str(PYTHON), '-B', str(self.study / 'frozen/tools/standalone_baseline.py'),
                'run', '--study', str(self.study), '--limit', '1'], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['state'], 'already_running')
        finally: service.unlock(handle)

    def test_132_targets_and_198_native_RFT_samples_preserved(self):
        self.assertEqual(len(self.manifest['jobs']), 132)
        reused = [j for j in self.manifest['jobs'] if j['algorithm'] == 'rft']
        self.assertEqual(len(reused), 66)
        self.assertEqual(sum(len(j['frozen_native_records']) for j in reused), 198)
        for job in reused:
            reference = Path(job['selected_reference']['record'])
            audit = self.study / 'references/reports/phase_02/live_audit_v2/attempts' / reference.parent.parent.name / reference.parent.name / 'audit.json'
            self.assertEqual(service.read(audit)['record_sha256'], job['selected_reference']['sha256'])

    def test_environment_and_frozen_code_tampering_are_detected(self):
        # Use a tiny independent fixture; do not mutate the actual baseline.
        folder = self.out / 'tamper'; folder.mkdir()
        item = folder / 'worker.py'; item.write_text('original')
        manifest = {'files': {'worker.py': service.sha(item)}, 'packages': {}, 'python_version': '0'}
        service.write(folder / 'manifest.json', manifest)
        (folder / 'manifest.sha256').write_text(service.sha(folder / 'manifest.json'))
        with self.assertRaisesRegex(ValueError, 'environment changed'): service.verify(folder, runtime=True)
        item.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Frozen file changed'): service.verify(folder)

    def test_bounded_timeout_and_stop_are_terminal_not_success(self):
        for label, timeout, stop, expected in [('timeout', .5, None, 'timeout'),
                                              ('stop', 10, lambda: True, 'interrupted_by_user')]:
            record = runner.bounded_job(self.job, timeout, output_root=self.out / label,
                worker_path=self.fake, input_path=self.input, stop_check=stop)
            self.assertEqual(record['status'], expected)
            self.assertNotEqual(record['process_exit_code'], 0)
            self.assertIsNone(record['result'])

    def test_monitor_gap_does_not_accept_timing(self):
        def slow_heartbeat(_): time.sleep(.12)
        record = runner.bounded_job(self.job, 10, output_root=self.out / 'gap',
            worker_path=self.fake, input_path=self.input, progress_callback=slow_heartbeat, heartbeat_gap_limit=.05)
        self.assertEqual(record['status'], 'interrupted_by_unmonitored_gap')

    def test_controller_crash_closes_worker_job(self):
        # An actual child controller is killed while its worker is alive.
        owner_file = self.out / 'crash_owner.py'; heartbeat = self.out / 'crash_heartbeat.json'
        owner_file.write_text(
            'import sys,os,json\nfrom pathlib import Path\n'
            + 'sys.path.insert(0,' + repr(str(ROOT / 'tools')) + ')\nimport run_paper_focus as runner\n'
            + 'job=' + repr(self.job) + '\n'
            + 'def pulse(value):\n value["owner_pid"]=os.getpid()\n Path(' + repr(str(heartbeat)) + ').write_text(json.dumps(value))\n'
            + 'runner.bounded_job(job,10,output_root=Path(' + repr(str(self.out / 'crash')) + '),'
            + 'worker_path=Path(' + repr(str(self.fake)) + '),input_path=Path(' + repr(str(self.input)) + '),progress_callback=pulse)\n', encoding='utf-8')
        owner = subprocess.Popen([str(PYTHON), '-B', str(owner_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic()+8
        try:
            while not heartbeat.exists() and time.monotonic()<deadline: time.sleep(.05)
            self.assertTrue(heartbeat.exists())
            data = service.read(heartbeat)
            kernel, handle = runner.memory_handle(data['owner_pid'])
            try: self.assertTrue(kernel.TerminateProcess(handle, 1))
            finally: kernel.CloseHandle(handle)
            owner.wait(timeout=5)
            # A dead process can remain a kernel object briefly; memory queries
            # cease once the job closes and all owned worker processes exit.
            import ctypes
            from ctypes import wintypes
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            alive = True; deadline = time.monotonic()+5
            while alive and time.monotonic()<deadline:
                try: kernel, handle = runner.memory_handle(data['worker_pid'])
                except OSError: alive = False; break
                try:
                    code = wintypes.DWORD(); k.GetExitCodeProcess(handle, ctypes.byref(code)); alive = code.value == 259
                finally: kernel.CloseHandle(handle)
                if alive: time.sleep(.05)
            self.assertFalse(alive, 'Worker survived controller crash')
        finally:
            if owner.poll() is None: owner.kill(); owner.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--study', required=True, type=Path); args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists(): raise ValueError('Use new output under btp_work')
    out.mkdir(parents=True); Acceptance.out = out; Acceptance.study = args.study.resolve()
    with (out / 'tests.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    service.write(out / 'result.json', {'tests': result.testsRun, 'successful': result.wasSuccessful(),
                  'failures': len(result.failures), 'errors': len(result.errors), 'command': sys.argv})
    print((out / 'result.json').read_text())
    if not result.wasSuccessful(): print((out / 'tests.txt').read_text())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': raise SystemExit(main())
