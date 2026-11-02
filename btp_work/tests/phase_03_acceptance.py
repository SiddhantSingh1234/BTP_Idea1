"""NEW Phase 03 independent physics, schedule and adversarial acceptance checks."""
import argparse,copy,hashlib,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.adapters.upstream import build_trace,adapt_run
from implementation.trace.model import circuit_from_pairs,evidence_profile,load_trace,fingerprint
from implementation.metrics.legacy import measure_trace
from implementation.movement_error.profiles import load_profile,validate_profile
from implementation.movement_error.physics import (heating_increment,angular_frequency,movement_time,progress,position,
    movement_loss_cost,neglog_failure,neglog_fidelity,local_batch_cost)
from implementation.movement_error.schedule import make_schedule,UnsupportedSchedule
from implementation.movement_error.checker import validate_schedule
from implementation.movement_error.evaluator import evaluate


def profile(name='extended_no_cooling'):
    return load_profile(ROOT/'configs/hardware'/(name+'.json'))


def route_fixture(moves=2, *, with_gates=True, zero=False):
    hw=evidence_profile(grid=8);hw.update(profile_id='phase03_synthetic_geometry.v1',min_atom_separation_um=3.0,slm_aod_shared_plane=True)
    hw['source']='NEW Phase03 analytic fixture; declared single-plane clearance, not calibration'
    groups=[{'kind':'initialize','items':[{'qubit':0,'site':[0,0]},{'qubit':1,'site':[0,2]}]}]
    row=0
    for i in range(moves):
        target=row if zero else 5-row
        groups.append({'kind':'move','items':[{'qubit':q,'from':[row,2*q],'to':[target,2*q],'cause':'explicit_nonparking'} for q in range(2)]})
        row=target
        if with_gates:groups.append({'kind':'gate','items':[{'qubits':[0,1],'sites':[[row,0],[row,2]]}]})
    circuit=circuit_from_pairs(2,[[0,1]]*(moves if with_gates else 0))
    return build_trace(groups,circuit,hw,timing='two_transfer_stages')


def high_heating(cooling=False,moves=5):
    p=profile('extended_registered_cooling' if cooling else 'extended_no_cooling')
    p['movement']['acceleration_um_per_us2']=.05;p['heating']['initial_n']=3.0
    return make_schedule(route_fixture(moves),p,'retime_and_cool' if cooling else 'retime')


class Acceptance(unittest.TestCase):
    def test_source_examples_and_frequency_convention(self):
        h=profile()['heating'];self.assertAlmostEqual(angular_frequency(h),.5026548245743669)
        for d,expected,tolerance in [(15,.0054,.0001),(75,.13,.01),(150,.54,.01)]:
            self.assertAlmostEqual(heating_increment(d,300,h),expected,delta=tolerance)
        h['cyclic_frequency_khz']=40
        self.assertAlmostEqual(heating_increment(55,200,h),6,delta=.3)
        # Independent SI computation; metres/seconds versus um/us.
        si=.5*(6*15e-6/(38e-9*(2*math.pi*80000)**2*(300e-6)**2))**2
        self.assertAlmostEqual(si,heating_increment(15,300,profile()['heating']),places=14)
        self.assertAlmostEqual(.001/1e-6,1000) # canonical acceleration -> SI

    def test_heating_scaling_and_distance_cancellation(self):
        p=profile();h=p['heating'];dn=heating_increment(15,300,h)
        self.assertAlmostEqual(heating_increment(30,300,h)/dn,4)
        self.assertAlmostEqual(heating_increment(15,600,h)/dn,1/16)
        for family in ('cubic','triangular'):
            p['movement']['family']=family
            values=[heating_increment(d,movement_time(d,p['movement']),h) for d in (3,15,60)]
            self.assertAlmostEqual(max(values),min(values),places=12)
        self.assertEqual(heating_increment(0,0,h),0)
        with self.assertRaises(ValueError):heating_increment(1,0,h)

    def test_independent_trajectory_oracles_and_caps(self):
        m=profile()['movement'];m.update(family='triangular',acceleration_um_per_us2=1)
        self.assertEqual(movement_time(0,m),0);self.assertEqual(movement_time(9,m),6)
        self.assertAlmostEqual(progress(1.5,6,'triangular'),.125)
        self.assertAlmostEqual(position([0,0],[8,4],1,4,'cubic')[0],1.25)
        self.assertAlmostEqual(progress(3,4,'cubic'),.84375)
        m['velocity_cap_um_per_us']=2
        self.assertEqual(movement_time(4,m),4);self.assertEqual(movement_time(12,m),8)
        self.assertAlmostEqual(progress(2,8,'triangular',distance_um=12,movement=m),1/6)
        self.assertAlmostEqual(progress(4,8,'triangular',distance_um=12,movement=m),.5)
        m.update(family='cubic',velocity_cap_um_per_us=1)
        self.assertEqual(movement_time(10,m),15) # cubic peak speed1.5D/T
        with self.assertRaises(ValueError):progress(5,4,'cubic')

    def test_batch_synchronization_and_sequential_sum(self):
        p=profile();t=route_fixture(2);s=make_schedule(t,p,'retime');r=evaluate(s)
        self.assertEqual(r['status'],'ok',r['validation'])
        # Each of two15um batches lasts300us; two20us transfer stages each; two .2us CZs.
        self.assertAlmostEqual(r['makespan_us'],680.4)
        self.assertEqual(r['counts']['transfer_atom_events'],8)
        hw=evidence_profile(8);hw.update(min_atom_separation_um=3,slm_aod_shared_plane=True)
        groups=[{'kind':'initialize','items':[{'qubit':0,'site':[0,0]},{'qubit':1,'site':[2,2]}]},
                {'kind':'move','items':[{'qubit':0,'from':[0,0],'to':[1,0]},{'qubit':1,'from':[2,2],'to':[4,2]}]}]
        unequal=build_trace(groups,circuit_from_pairs(2,[]),hw,timing='two_transfer_stages')
        out=evaluate(make_schedule(unequal,p,'retime'))
        self.assertEqual(out['status'],'ok',out['validation'])
        n=out['validation']['final_n_by_qubit'];self.assertAlmostEqual(n[1]/n[0],4)
        self.assertAlmostEqual(out['makespan_us'],40+math.sqrt(36000))

    def test_source_retention_values_and_stable_extreme_tail(self):
        for n,retention,tolerance in [(30,.708,.001),(20,.998,.001),(15,.999998,.000001)]:
            self.assertAlmostEqual(math.exp(-movement_loss_cost(n,33)),retention,delta=tolerance)
        from scipy.special import log_ndtr
        for n in (.01,15,20,30,33,100,10000,1e10):
            expected=-float(log_ndtr((33-n)/math.sqrt(n)))
            self.assertTrue(math.isclose(movement_loss_cost(n,33),expected,rel_tol=2e-13,abs_tol=1e-14),(n,expected))
        self.assertEqual(movement_loss_cost(0,33),0)
        self.assertTrue(math.isinf(neglog_failure(1)));self.assertTrue(math.isinf(neglog_fidelity(0)))
        for invalid in (-.01,1.01,float('nan')):
            with self.assertRaises(ValueError):neglog_failure(invalid)

    def test_repeated_risky_moves_not_only_final_state(self):
        p=profile();p['heating'].update(initial_n=30,multiplier=0);p['noise']['f_cz']=1
        r=evaluate(make_schedule(route_fixture(2),p,'retime'))
        self.assertEqual(r['status'],'ok')
        self.assertAlmostEqual(r['budget']['terms']['E_movement_loss'],-4*math.log(.5*(1+math.erf(3/math.sqrt(60)))) )
        no_moves=evaluate(make_schedule(route_fixture(0),p,'retime'))
        self.assertEqual(no_moves['budget']['total_E'],0)
        zero=evaluate(make_schedule(route_fixture(1,zero=True),p,'retime'))
        self.assertEqual(zero['budget']['terms']['E_movement_loss'],0)
        self.assertEqual(zero['counts'].get('transfer_atom_events',0),0)

    def test_gate_uses_completed_heating_and_trap_transfer_preserves_n(self):
        p=profile();s=make_schedule(route_fixture(1),p,'retime');r=evaluate(s)
        gate=next(a for a in r['event_audit'] if a['kind']=='gate' and a['boundary']=='start')
        self.assertTrue(all(v>0 for v in gate['n_before'].values()))
        dn=heating_increment(15,300,p['heating'])
        expected=-math.log1p(-p['heating']['lambda']*.005*2*dn)
        self.assertAlmostEqual(r['budget']['terms']['E_heating_gate'],expected)
        self.assertGreater(expected,0);self.assertLess(r['budget']['terms']['E_movement_loss'],expected)
        broken=copy.deepcopy(s);next(e for e in broken['events'] if e['kind']=='gate')['start_us']-=21
        self.assertEqual(validate_schedule(broken)['status'],'invalid')

    def test_per_qubit_exposure_and_gate_exclusion(self):
        p=profile('transfer_only');p['exposure'].update(T2_us=10,T2_by_qubit_us={'1':20})
        p['exposure']['rates']['gate']=0
        t=load_trace(ROOT/'tests/fixtures/trace_v1/valid_parallel');p['noise']['transfer_duration_us']=1
        r=evaluate(make_schedule(t,p));self.assertEqual(r['status'],'ok')
        self.assertAlmostEqual(r['per_qubit_exposure']['0']['weighted_exposure_us'],3)
        self.assertAlmostEqual(r['per_qubit_exposure']['1']['weighted_exposure_us'],3)
        self.assertAlmostEqual(r['budget']['terms']['E_decoherence'],.45)
        self.assertAlmostEqual(r['budget']['terms']['E_transfer'],-4*math.log(.999))
        self.assertAlmostEqual(r['makespan_us'],3.2)

    def test_cooling_state_transfer_circuit_independently(self):
        # Bit0 hot, bit1 cold, bit2 arbitrary entangled reference.
        state=[0j]*8;state[0]=.3+.4j;state[5]=math.sqrt(.75)
        def hadamard(vec,bit):
            out=vec.copy()
            for i in range(8):
                if not i&(1<<bit):
                    j=i|(1<<bit);out[i]=(vec[i]+vec[j])/math.sqrt(2);out[j]=(vec[i]-vec[j])/math.sqrt(2)
            return out
        got=state.copy()
        for kind,target in [('h',1),('cz',None),('h',1),('h',0),('cz',None),('h',0)]:
            if kind=='h':got=hadamard(got,target)
            else:got=[(-v if (i&3)==3 else v) for i,v in enumerate(got)]
        expected=[0j]*8;expected[0]=state[0];expected[6]=state[5]
        self.assertLess(max(abs(a-b) for a,b in zip(got,expected)),1e-15)

    def test_cooling_population_cost_time_and_no_double_counting(self):
        s=high_heating(True);r=evaluate(s)
        self.assertEqual(r['status'],'ok',r['validation']);c=r['counts'];episodes=c['cooling_episodes'];population=c['cooled_atom_events']
        self.assertGreater(episodes,0);self.assertEqual(population,2*episodes)
        self.assertEqual(c['native_CZ'],5);self.assertEqual(c['cooling_CZ'],2*population);self.assertEqual(c['cooling_H'],4*population)
        self.assertEqual(c['transfer_atom_events'],20+2*population)
        terms=r['budget']['terms'];self.assertAlmostEqual(terms['E_native_gate'],-5*math.log(.995))
        self.assertAlmostEqual(terms['E_cooling_gate'],-2*population*math.log(.995)-4*population*math.log(.99992))
        self.assertAlmostEqual(terms['E_transfer'],-(20+2*population)*math.log(.999))
        self.assertAlmostEqual(terms['E_decoherence'],2*r['makespan_us']/1.5e6)
        self.assertAlmostEqual(r['budget']['total_E'],sum(terms.values()))
        plain=evaluate(high_heating(False));self.assertAlmostEqual(r['makespan_us']-plain['makespan_us'],episodes*645.8)
        for q,a in r['final_physical_carriers'].items():self.assertTrue(a.startswith('cold_bank'))
        self.assertLess(r['budget']['total_E'],plain['budget']['total_E'])

    def test_cooling_adversarial_resources_carriers_and_duplicates(self):
        source=high_heating(True)
        for mutation in ('missing_resource','wrong_cold_atom','wrong_reset','missing_CZ','bad_dock','stale_carrier','duplicate_episode'):
            s=copy.deepcopy(source);idx=next(i for i,e in enumerate(s['events']) if e['kind']=='cooling');e=s['events'][idx]
            if mutation=='missing_resource':e['resources'].pop()
            elif mutation=='wrong_cold_atom':e['cold_atom_ids'][0]='unprepared'
            elif mutation=='wrong_reset':e['reset_n']=0.1
            elif mutation=='missing_CZ':e['suboperations'].pop(1)
            elif mutation=='bad_dock':e['sites'][0]=[7,7]
            elif mutation=='stale_carrier':s['events'][idx+1]['atom_ids']=e['atom_ids']
            else:s['events'].insert(idx+1,copy.deepcopy(e))
            self.assertEqual(validate_schedule(s)['status'],'invalid',mutation)
        p=profile('extended_registered_cooling');p['movement']['acceleration_um_per_us2']=.05;p['cooling'].update(bank_count=1,threshold_n=.001)
        with self.assertRaises(UnsupportedSchedule):make_schedule(route_fixture(3),p,'retime_and_cool')
        with self.assertRaises(UnsupportedSchedule):make_schedule(route_fixture(1),profile(),'retime_and_cool')

    def test_local_prediction_vs_replay_and_omitted_suffix(self):
        p=profile();p['heating']['initial_n']=3
        predicted=local_batch_cost({0:3,1:3},{0:15,1:15},p,next_cz_pairs=[(0,1)])
        actual=evaluate(make_schedule(route_fixture(1),p,'retime'))
        # Independent baseline: same CZ, no transport; duration .2us; starting n=3 each.
        base=-math.log(.995)-math.log1p(-p['heating']['lambda']*.005*6)+2*.2/1.5e6
        self.assertAlmostEqual(predicted['total_E'],actual['budget']['total_E']-base,places=13)
        dn=heating_increment(15,300,p['heating'])
        omitted=-math.log1p(-p['heating']['lambda']*.005*(6+2*dn))+math.log1p(-p['heating']['lambda']*.005*6)
        self.assertGreater(omitted,0)
        self.assertIn('only supplied next CZs; no later suffix gates',predicted['assumptions'])

    def test_historical_results_and_rescore_do_not_change_schedule(self):
        for algo,name in [('rft','smoke_rft_qft5_01'),('dasatom','smoke_dasatom_qft5_01')]:
            t=adapt_run(ROOT/'runs/phase_00'/name,algo,timing='two_transfer_stages');old=fingerprint(t);reference=measure_trace(t)['legacy']
            s=make_schedule(t,profile('legacy_rft'));r=evaluate(s)
            self.assertEqual(old,fingerprint(t));self.assertEqual(s['events'],t['events'])
            self.assertEqual(r['historical_source_score'],reference)
            self.assertAlmostEqual(r['budget']['fidelity_proxy'],reference['fidelity_proxy'],places=14)
            self.assertAlmostEqual(r['budget']['total_E'],reference['negative_log_fidelity'],places=13)
        s=make_schedule(route_fixture(1),profile());self.assertEqual(validate_schedule(s)['status'],'invalid') # cubic law on linear timing
        evidence=adapt_run(ROOT/'runs/phase_00/smoke_rft_qft5_01','rft')
        self.assertIsNone(evaluate(make_schedule(evidence,profile()))['budget'])

    def test_profile_rejection_underflow_and_probability_one(self):
        for path,value in [('probability',1.1),('T2',0),('frequency',float('nan')),('resources',0)]:
            p=profile('extended_registered_cooling')
            if path=='probability':p['noise']['f_transfer']=value
            elif path=='T2':p['exposure']['T2_us']=value
            elif path=='frequency':p['heating']['cyclic_frequency_khz']=value
            else:p['cooling']['bank_count']=value
            with self.assertRaises(ValueError):validate_profile(p)
        p=profile();p['exposure']['T2_us']=.001;r=evaluate(make_schedule(route_fixture(1),p,'retime'))
        self.assertTrue(r['budget']['fidelity_underflow']);self.assertTrue(math.isfinite(r['budget']['total_E']))
        p['noise']['f_cz']=0;r=evaluate(make_schedule(route_fixture(1),p,'retime'))
        self.assertTrue(r['budget']['total_E_infinite']);self.assertFalse(r['budget']['fidelity_underflow'])
        p=profile();p['heating']['initial_n']=100000
        r=evaluate(make_schedule(route_fixture(1),p,'retime'));self.assertEqual(r['status'],'invalid');self.assertIsNone(r['budget'])

    def test_disabled_heating_ablation_and_frozen_transfer_isolation(self):
        t=route_fixture(1);a=profile('frozen_ideal');a['heating']['initial_n']=30
        b=profile('transfer_only');b['heating']['initial_n']=30
        ra=evaluate(make_schedule(t,a));rb=evaluate(make_schedule(t,b))
        self.assertEqual(ra['budget']['terms']['E_heating_gate'],0)
        self.assertAlmostEqual(rb['budget']['total_E']-ra['budget']['total_E'],-4*math.log(.999),places=14)
        self.assertEqual(ra['makespan_us'],rb['makespan_us'])
        malformed=make_schedule(t,profile(),'retime');del malformed['events'][1]['start_us']
        self.assertEqual(validate_schedule(malformed)['status'],'invalid')
        with self.assertRaises(ValueError):local_batch_cost({0:0,1:0},{0:15,1:15},profile(),duration_us=1)

    def test_geometry_and_source_invalidity_not_erased(self):
        t=load_trace(ROOT/'tests/fixtures/trace_v1/two_atom_midpath_collision')
        s=make_schedule(t,profile(),'retime');self.assertEqual(validate_schedule(s)['status'],'invalid')
        t=route_fixture(1);t['metadata']['origin']['upstream_status']='invalid'
        self.assertEqual(evaluate(make_schedule(t,profile(),'retime'))['status'],'invalid')
        s=make_schedule(route_fixture(1),profile(),'retime');s['profile']['noise']['f_cz']=.99
        self.assertIn('profile_hash',{v['code'] for v in validate_schedule(s)['violations']})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a new output path inside btp_work')
    out.mkdir(parents=True)
    with (out/'unittest.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
    files=[p for p in (ROOT/'implementation/movement_error').rglob('*.py')]+list((ROOT/'configs/hardware').glob('*.json'))+[Path(__file__).resolve()]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    baseline=json.loads((ROOT/'reports/phase_02/tests_05/result.json').read_text())['artifact_sha256']
    changed=[name for name,digest in baseline.items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
    summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),
             'original_phase02_tested_artifacts_changed':changed,'artifact_sha256':hashes,'python':sys.version,'command':sys.argv}
    (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='artifact_sha256'}))
    if not result.wasSuccessful():print((out/'unittest.txt').read_text())
    return 0 if result.wasSuccessful() and not changed else 1


if __name__=='__main__':raise SystemExit(main())