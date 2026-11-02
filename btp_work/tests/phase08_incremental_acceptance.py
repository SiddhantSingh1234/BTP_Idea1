"""Independent aggregation-unit and saturated-factorial cross-checks."""
import argparse
import csv
import json
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools'),str(ROOT/'analysis')]
sys.dont_write_bytecode=True
from phase07_extension import read,write,sha
from phase08_incremental import paired_statistics


class Acceptance(unittest.TestCase):
    def test_grids_are_clusters_not_independent_circuits(self):
        sample=[{'family':'toy','case':'A','relative_E_percent':100.,'delta_E':1.,'control_E':1.}]
        sample += [{'family':'toy','case':'B','relative_E_percent':0.,'delta_E':0.,'control_E':1.} for _ in range(10)]
        result=paired_statistics(sample,reps=1000)
        self.assertEqual(result['independent_circuit_clusters'],2)
        self.assertEqual(result['equal_circuit_mean_relative_E_percent'],50.)
        self.assertAlmostEqual(result['target_mean_relative_E_percent'],100/11)
        self.assertEqual(result,paired_statistics(sample,reps=1000))

    def test_factorial_effects_against_independent_saturated_linear_system(self):
        source=list(csv.DictReader((ROOT/'runs/idea1_extension_v1/campaign/results.csv').open(encoding='utf-8-sig')))
        effects=list(csv.DictReader((ROOT/'reports/phase_08/integrated_analysis_02/factorial_effects.csv').open()))
        for row in effects:
            selected=[r for r in source if r['case']==row['case'] and r['seed']==row['seed'] and r['quality_sample'].lower()=='true']
            self.assertEqual(len(selected),8)
            design=[];values=[]
            for r in selected:
                L,A,R=(int(r[k]) for k in ['L','A','R'])
                design.append([1,L,A,R,L*A,L*R,A*R,L*A*R]);values.append(float(r['E']))
            b=np.linalg.solve(np.array(design,float),np.array(values))
            expected={'L_effect_E':b[1]+.5*b[4]+.5*b[5]+.25*b[7],
                      'A_effect_E':b[2]+.5*b[4]+.5*b[6]+.25*b[7],
                      'R_effect_E':b[3]+.5*b[5]+.5*b[6]+.25*b[7],
                      'LA_interaction_E':b[4]+.5*b[7],'LR_interaction_E':b[5]+.5*b[7],
                      'AR_interaction_E':b[6]+.5*b[7],'LAR_interaction_E':b[7]}
            for key,value in expected.items():self.assertAlmostEqual(float(row[key]),value,places=12)

    def test_new_primary_scores_are_paired_and_not_mixed_timers(self):
        d=read(ROOT/'reports/phase_08/new_primary_analysis_01/summary.json')
        self.assertTrue(d['all_new_primary_outputs_independently_replayed'])
        self.assertEqual(sum(g['paired'] for g in d['groups']),20)
        self.assertTrue(all(p['equivalent_up_to_global_phase'] for p in d['semantic_proofs']))
        pairs=list(csv.DictReader((ROOT/'reports/phase_08/new_primary_analysis_01/new_primary_pairs.csv').open()))
        self.assertTrue(all(r['strict_cross_algorithm_timing_comparison']=='False' for r in pairs))
        self.assertTrue(all(p['parking_calls']==p['eviction_calls']==0 for p in d['qv_parking_mechanism']))

    def test_sensitivity_and_fresh_environment_evidence(self):
        d=read(ROOT/'reports/phase_08/integrated_analysis_02/summary.json')
        self.assertTrue(d['sensitivity_formula_independently_replayed'])
        self.assertEqual(len(d['sensitivity']),9)
        r=read(ROOT/'final/reproduction_clean_01/verification.json')
        self.assertEqual(r['status'],'ok');self.assertTrue(r['all_29_exact_packages_match'])
        self.assertFalse(r['user_site_enabled'])
        self.assertIn('repro_env',r['sys_prefix'])
        self.assertTrue(all(p['equivalent_up_to_global_phase'] and p['basis_states']==32 for p in r['semantic_proofs']))

    def test_old_studies_and_numeric_rebuild_are_unchanged(self):
        for path,record in read(ROOT/'reports/phase_07/reused_studies.json').items():self.assertEqual(sha(ROOT/path),record['sha256'])
        old=ROOT/'reports/phase_08/integrated_analysis_01';new=ROOT/'reports/phase_08/integrated_analysis_02'
        for name in ['clustered_comparisons.csv','paired_effects.csv','transport_budget.csv','factorial_effects.csv','fixed_trace_sensitivity.csv']:
            self.assertEqual((old/name).read_bytes(),(new/name).read_bytes())


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Fresh output required')
    out.mkdir(parents=True)
    with (out/'tests.txt').open('w',encoding='utf-8') as h:
        result=unittest.TextTestRunner(stream=h,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    record={'tests':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
            'script_sha256':sha(Path(__file__))}
    write(out/'result.json',record);print(json.dumps(record));return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
