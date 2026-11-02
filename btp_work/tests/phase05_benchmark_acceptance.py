"""Full Phase05 benchmark: matching, bounded equivalence, timing and detached resume."""
import argparse
from copy import deepcopy
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import model_comparison as service
import model_comparison_worker as worker
import phase05_comparison_worker as phase5
from implementation.assignment.integration import compile_schedule, assignment_core
from implementation.assignment.fixtures import generated_case
from implementation.assignment.costs import load_options as load_assignment
from implementation.lookahead.potential import load_options as load_lookahead
from implementation.movement_error.profiles import load_profile
PYTHON=ROOT/'.venv/Scripts/python.exe'


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=ROOT/'runs/model_comparison_smoke_baseline_benchmark_tests_03'
        cls.original=ROOT/'runs/phase01_frozen_baseline_v1'
        cls.original_sha=service.sha(cls.original/'manifest.json')
        suffix=cls.out.name
        cls.phase4=ROOT/('runs/phase04_full_phase5_control_'+suffix)
        cls.phase5=ROOT/('runs/phase05_full_benchmark_'+suffix)
        cls.manifests={}
        for track,study in [('phase4',cls.phase4),('phase5',cls.phase5)]:
            if study.exists():raise ValueError('Use new output suffix')
            cls.manifests[track]=service.prepare(study,ROOT,cls.base,track)

    def launch(self,track,study):
        env=os.environ.copy();env['BTP_WORK_ROOT']=str(ROOT)
        done=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
            str(ROOT/'tools/Start-ModelComparison.ps1'),'-Track',track,'-Study',str(study),
            '-Baseline',str(self.base),'-Limit','1'],capture_output=True,text=True,encoding='utf-8',timeout=30,env=env)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            p=service.read(study/'progress.json')
            if p['state'] in ['paused_at_limit','error','finished_with_issues_or_missing_sources']:
                return p
            time.sleep(.2)
        self.fail('Detached worker failed to finish within 60 seconds')

    def test_01_complete_matched_protocol_and_config_hashes(self):
        manifest=self.manifests['phase5']
        self.assertEqual(len(manifest['jobs']),66)
        self.assertTrue(all(j['algorithm']=='rft' for j in manifest['jobs']))
        self.assertEqual({j['target_id'] for j in manifest['jobs']},
                         {j['target_id'] for j in self.manifests['phase4']['jobs']})
        self.assertEqual(manifest['variants'],service.PHASE5_VARIANTS)
        self.assertEqual(len(manifest['variants']),10)
        summary=service.summarize(self.phase5,manifest)
        self.assertEqual(summary['rows'],792)
        for name in manifest['variants']:
            relative='frozen/configs/variants/assignment.'+name+'.json'
            self.assertEqual(service.sha(self.phase5/relative),manifest['files'][relative])
        for job in manifest['jobs']:
            self.assertEqual(service.sha(self.phase5/job['frozen_input']),job['expected_normalized_sha256'])
        service.verify(self.phase5,runtime=True)

    def test_02_bounded_context_preserves_every_production_decision_and_rng(self):
        profile=load_profile(ROOT/'configs/hardware/extended_no_cooling.json')
        parking=load_lookahead(ROOT/'configs/variants/lookahead.next_events_h4.json')
        context_type=phase5.bounded_context_type(worker.BenchmarkContext)
        exercised_limit=False
        for case in [generated_case(200),generated_case(204,depth=14,static=True)]:
            for name in service.PHASE5_VARIANTS:
                config=load_assignment(ROOT/'configs/variants'/('assignment.'+name+'.json'))
                expected=compile_schedule(case['schedule'],case['circuit']['num_qubits'],case['layout'],
                    case['geometry'],case['baseline_options'],parking,config,profile,circuit=case['circuit'],routing_seed=42)
                context=context_type(case['schedule'],case['circuit']['num_qubits'],case['circuit'],
                    parking,case['geometry'],config,profile)
                core=assignment_core(context)
                layout=[[tuple(p) for p in slot] for slot in case['layout']]
                busiest=core.find_busiest_pairs(case['schedule'])
                canonical=core.create_initial_mapping(busiest,layout)
                random.seed(42)
                instructions=core.generate_hardware_instructions(case['schedule'],canonical,busiest,
                    case['circuit']['num_qubits'],11,11,layout,4,2,
                    options=core.CompilerOptions(**case['baseline_options']))
                self.assertEqual('\n'.join(instructions)+'\n',expected['instructions'],(case['case_id'],name))
                self.assertEqual(hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),expected['random_state_after_sha256'])
                stats=context.statistics()
                self.assertEqual(stats['assignment_solves'],expected['statistics']['assignment_solves'])
                self.assertEqual(stats['physical_prefix_move_batches'],expected['statistics']['physical_prefix_move_batches'])
                self.assertEqual(stats['predicted_prefix_n_by_qubit'],expected['statistics']['predicted_prefix_n_by_qubit'])
                self.assertEqual(stats['completed_gate_count'],len(case['circuit']['gates']))
                for records in [context.decisions,context.batches,context.assignment_records,context.route_records]:
                    self.assertLessEqual(len(records),8)
                exercised_limit |= stats['assignment_solves']>8
        self.assertTrue(exercised_limit)

    def test_03_real_matched_timer_and_phase04_reference(self):
        progress=self.launch('phase4',self.phase4)
        self.assertEqual(progress['state'],'paused_at_limit',progress)
        progress=self.launch('phase5',self.phase5)
        self.assertEqual(progress['state'],'paused_at_limit',progress)
        job=self.manifests['phase5']['jobs'][0]
        p,record=service.records(self.phase5,job['target_id'])[0]
        self.assertEqual(record['status'],'ok',record)
        self.assertEqual(record['launcher_protocol'],'windows-suspended-job-v1')
        rows=record['result']['rows']
        self.assertEqual(len(rows),12)
        self.assertTrue(all(row['accepted_schedule'] for row in rows),rows)
        self.assertEqual(len({row['profile_sha256'] for row in rows}),1)
        self.assertEqual(len({row['geometry_sha256'] for row in rows}),1)
        self.assertTrue(all(row['compile_seconds']>0 for row in rows))
        self.assertTrue(all(row.get('prefix_heating_matches_full_evaluator',True) for row in rows))
        compatibility=service.read(p.parent/'worker/compatibility.json')
        self.assertTrue(compatibility['instructions_exact']);self.assertTrue(compatibility['rng_after_exact'])
        four_path,four_record=service.records(self.phase4,job['target_id'])[0]
        four=next(row for row in four_record['result']['rows'] if row['variant']=='next_events_h4')
        five=next(row for row in rows if row['variant']=='phase04_reference')
        self.assertEqual(four['extended_E'],five['extended_E'])
        self.assertEqual((four_path.parent/'worker/next_events_h4/instructions.txt').read_bytes(),
                         (p.parent/'worker/phase04_reference/instructions.txt').read_bytes())
        for name in self.manifests['phase5']['variants']:
            diagnostics=service.read(p.parent/'worker'/name/'assignment_diagnostics.json')
            for key in ['decisions_sample','batches_sample','assignment_sample','route_prefix_sample']:
                self.assertLessEqual(len(diagnostics[key]),8)

    def test_04_resume_skips_success_and_appends_next_target(self):
        job=self.manifests['phase5']['jobs'][0]
        p,_=service.records(self.phase5,job['target_id'])[0];before=p.read_bytes()
        progress=self.launch('phase5',self.phase5)
        self.assertEqual(progress['state'],'paused_at_limit',progress)
        self.assertEqual(p.read_bytes(),before)
        self.assertEqual(len(service.records(self.phase5,job['target_id'])),1)
        self.assertEqual(service.read(self.phase5/'summary.json')['target_status_counts']['ok'],2)

    def test_05_phase01_overlap_rejects_compilation_timing(self):
        study=self.out/'contamination';study.mkdir()
        manifest=deepcopy(self.manifests['phase5']);job=manifest['jobs'][0];manifest['jobs']=[job]
        def fake_bounded(job,timeout,**kwargs):
            path=study/'measurements'/job['target_id']/'attempt_01/attempt_record.json'
            record={'target_id':job['target_id'],'status':'ok','record_path':str(path.relative_to(ROOT)),
                'result':{'rows':[{'variant':'legacy_exact','accepted_schedule':True,'compile_seconds':1.0,'status':'ok'}]}}
            service.write(path,record);return record
        with patch.object(service,'CODE',study/'frozen'),patch.object(service,'EXECUTION',study/'frozen'),             patch.object(service,'verify',return_value=manifest),             patch.object(service,'baseline_running',side_effect=[False,True]),             patch.object(service,'source_request',return_value=({'kind':'rft_instructions'},1.0,'original')) ,             patch.object(service.bounded,'bounded_job',side_effect=fake_bounded):
            result=service.run(study,ROOT,0)
        self.assertEqual(result['state'],'interrupted_external_benchmark')
        record=service.records(study,job['target_id'])[0][1]
        self.assertTrue(record['timing_contaminated'])
        with (study/'results.csv').open(newline='') as handle:rows=list(csv.DictReader(handle))
        self.assertTrue(all(row.get('compile_seconds','')=='' for row in rows))

    def test_07_wrong_track_is_rejected_before_launch(self):
        env=os.environ.copy();env['BTP_WORK_ROOT']=str(ROOT)
        done=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
            str(ROOT/'tools/Start-ModelComparison.ps1'),'-Track','phase5','-Study',str(self.phase4),
            '-Baseline',str(self.base),'-Limit','1'],capture_output=True,text=True,encoding='utf-8',timeout=30,env=env)
        self.assertNotEqual(done.returncode,0)
        self.assertIn('different comparison track',done.stderr)

    def test_06_original_frozen_studies_are_unchanged(self):
        self.assertEqual(service.sha(self.original/'manifest.json'),self.original_sha)
        service.baseline_service.verify(self.original,runtime=True)
        service.verify(self.phase4,runtime=True);service.verify(self.phase5,runtime=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Use new output under btp_work')
    out.mkdir(parents=True);Acceptance.out=out
    with (out/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    summary={'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)}
    service.write(out/'result.json',summary);print(json.dumps(summary))
    if not result.wasSuccessful():print((out/'tests.txt').read_text())
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
