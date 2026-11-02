"""Verify exact Phase03 output equality and scoped analysis reuse."""
import argparse
from copy import deepcopy
import builtins
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import model_comparison as service
import model_comparison_worker as worker
import implementation.movement_error.schedule as schedule_module
import implementation.movement_error.checker as checker_module


class Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = ROOT / 'runs/phase03_matched_benchmark_v1'
        cls.manifest = service.verify(cls.study, runtime=True)
        cls.baseline = Path(cls.manifest['baseline'])
        for name, expected in cls.manifest['files'].items():
            if name.startswith('frozen/implementation/'):
                current = ROOT / name[len('frozen/'):]
                assert service.sha(current) == expected, str(current)
        spec = importlib.util.spec_from_file_location('unoptimized_worker_reference', cls.study / 'frozen/tools/model_comparison_worker.py')
        cls.reference = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.reference)
        cls.reference.WORK = ROOT
        cls.timings = []
        cls.requests = []
        for algorithm, case in [('rft', 'qft_5'), ('dasatom', 'qft_5'), ('rft', 'qft_10'), ('dasatom', 'qft_10'), ('rft', 'qft_20'), ('dasatom', 'qft_20')]:
            job = next(j for j in cls.manifest['jobs'] if j['algorithm'] == algorithm and j['case'] == case and j['grid'] == 11)
            if algorithm == 'rft':
                source = {'kind': 'rft_instructions', 'instructions': str(cls.study / job['source_worker'] / 'instructions.txt')}
                seconds = job['original_compile_seconds']; scope = job['native']['timing_scope']
            else:
                p, record = next((p,r) for p,r in service.records(cls.baseline,job['target_id']) if r['status']=='ok')
                source = {'kind': 'dasatom_trace', 'worker': str(p.parent / 'worker')}
                seconds = record['result']['corrected_compile_seconds']; scope = record['result']['timing_scope']
            cls.requests.append({'track':'phase3','job':job,'source':source,'original_compile_seconds':seconds,
                'original_timing_scope':scope,'geometry':{'rows':11,'columns':11,'r_int':2,'r_blk':4,'spacing_um':3.0}})

    def test_01_scientific_outputs_equal_original_frozen_worker(self):
        for index, request in enumerate(self.requests):
            circuit = worker.read_cz_qasm(self.study / request['job']['frozen_input'])
            trace = worker.source_trace(request, circuit)
            original_out = self.out / ('reference_' + str(index)); cached_out = self.out / ('optimized_' + str(index))
            start = time.perf_counter()
            original = self.reference.score(trace, request, 'original_phase3', original_out, request['original_compile_seconds'],
                compilation_reused=True, timing_scope=request['original_timing_scope'])
            original_seconds = time.perf_counter() - start
            start = time.perf_counter()
            cached = worker.score(trace, request, 'original_phase3', cached_out, request['original_compile_seconds'],
                compilation_reused=True, timing_scope=request['original_timing_scope'])
            cached_seconds = time.perf_counter() - start
            original.pop('output'); cached.pop('output')
            self.assertEqual(original,cached)
            for filename in ['validation.json','metrics.json','schedule.json','evaluation.json', 'trace/events.jsonl', 'trace/metadata.json']:
                self.assertEqual((original_out/filename).read_bytes(),(cached_out/filename).read_bytes(),(index,filename))
            reuse = service.read(cached_out/'analysis_reuse.json')
            enabled = len(trace['events']) >= 512
            self.assertEqual(reuse['enabled'],enabled)
            self.assertEqual(reuse['validation_hits'],2 if enabled else 0)
            self.assertEqual(reuse['validation_misses'],2 if enabled else 0)
            self.assertEqual(reuse['metrics_hits'],1 if enabled else 0)
            self.assertEqual(reuse['metrics_misses'],1 if enabled else 0)
            self.timings.append({'algorithm':request['job']['algorithm'],'case':request['job']['case'],
                'events':len(trace['events']),'reference_seconds':original_seconds,'optimized_seconds':cached_seconds})

    def test_02_phase3_execute_does_not_import_or_run_compilers(self):
        original_import = builtins.__import__
        denied = {'benchmark_runner','compiler_core','DasAtom_fun','Enola','qiskit'}
        def guarded(name,*args,**kwargs):
            if name.split('.')[0] in denied: raise AssertionError('Compiler import in Phase03: '+name)
            return original_import(name,*args,**kwargs)
        request = next(r for r in self.requests if r['job']['algorithm']=='dasatom')
        with patch('builtins.__import__',guarded):
            rows = worker.execute(request,self.study/request['job']['frozen_input'],self.out/'no_compile')
        self.assertEqual(len(rows),1);self.assertTrue(rows[0]['compilation_reused'])
        self.assertTrue(rows[0]['accepted_schedule'])
        self.assertEqual(rows[0]['compile_seconds'],request['original_compile_seconds'])

    def test_03_changed_geometry_invalidates_cached_validation(self):
        request = self.requests[0];circuit=worker.read_cz_qasm(self.study/request['job']['frozen_input'])
        trace=worker.source_trace(request,circuit)
        with worker.reuse_trace_analysis() as stats:
            first=worker.check_trace(trace)
            first['violations'].append({'code':'caller_mutation'})
            second=worker.check_trace(trace)
            self.assertFalse(any(v['code']=='caller_mutation' for v in second['violations']))
            changed=deepcopy(trace);changed['metadata']['hardware']['rows']=0
            invalid=schedule_module.check_trace(changed)
            self.assertEqual(invalid['status'],'invalid')
            self.assertEqual(stats['validation_misses'],2);self.assertEqual(stats['validation_hits'],1)

    def test_04_cache_scope_restores_original_validation_after_error(self):
        original=worker.check_trace; schedule_check=schedule_module.check_trace; checker_check=checker_module.check_trace
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with worker.reuse_trace_analysis(): raise RuntimeError('injected')
        self.assertIs(worker.check_trace,original)
        self.assertIs(schedule_module.check_trace,schedule_check)
        self.assertIs(checker_module.check_trace,checker_check)

    def test_05_frozen_comparison_and_phase01_sources_stay_unchanged(self):
        service.verify(self.study,runtime=True)
        service.baseline_service.verify(self.baseline,runtime=True)
        fixed=ROOT/'runs/phase01_frozen_baseline_v1/controller_repair_v1/tools/run_paper_focus.py'
        self.assertEqual(service.sha(ROOT/'tools/run_paper_focus.py'),service.sha(fixed))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use new output under btp_work')
    out.mkdir(parents=True);Regression.out=out
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Regression))
    summary={'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)}
    service.write(out/'result.json',summary);service.write(out/'timings.json',Regression.timings)
    print(json.dumps(summary));print(json.dumps(Regression.timings))
    if not result.wasSuccessful():print((out/'tests.txt').read_text())
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
