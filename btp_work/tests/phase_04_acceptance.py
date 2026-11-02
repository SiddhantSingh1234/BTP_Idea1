"""NEW Phase04 independent oracle, legacy and full-model acceptance checks."""
import argparse,copy,hashlib,itertools,json,math,random,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.trace.model import read_cz_qasm,circuit_from_pairs
from implementation.lookahead.events import FutureEventIndex
from implementation.lookahead.potential import FuturePotential,load_options,validate_options
from implementation.lookahead.integration import LookaheadContext,compile_schedule,direct_source_control,reachable_bytes
from implementation.lookahead.fixtures import serialized_case,worse_horizon_example
from implementation.lookahead.evaluation import evaluate_compilation
from implementation.movement_error.profiles import load_profile


def config(name='next_events_h1'):
 return load_options(ROOT/'configs/variants'/('lookahead.'+name+'.json'))


def physics():return load_profile(ROOT/'configs/hardware/extended_no_cooling.json')


def baseline():return json.loads((ROOT/'configs/baselines/rft_snapshot.json').read_text())['options']


def enumerated_oracle(schedule):
 # Deliberately scan every scheduled occurrence. No index, bisect or production query.
 out=[];count=0
 for layer,(_,pairs) in enumerate(schedule):
  for a,b in pairs:
   out.append({'gate_id':f'g{count:06}','qubits':[a,b],'layer':layer});count+=1
 return out


def oracle_query(gates,q,layer,h,done,active):
 out=[]
 for gate in gates:
  if q not in gate['qubits'] or gate['layer']<layer or gate['gate_id'] in done or gate['gate_id'] in active:continue
  out.append({'gate_id':gate['gate_id'],'partner':next(x for x in gate['qubits'] if x!=q),
              'logical_layer':gate['layer'],'logical_layer_delta':gate['layer']-layer})
 return out[:h]


def manual_case():
 data=json.loads((ROOT/'runs/phase_00/compiled_fixture_01/trace.json').read_text())
 return {'schedule':data['schedule'],'circuit':read_cz_qasm(ROOT/'benchmarks/phase_00/four_qubit_hand_trace.qasm'),
         'layout':data['physical_layout'],'geometry':{'rows':3,'columns':3,'r_int':1,'r_blk':2,'spacing_um':3},'options':data['options']}


class Acceptance(unittest.TestCase):
 def test_exhaustive_event_queries_against_independent_oracle(self):
  pairs=list(itertools.combinations(range(4),2));matchings=[[]]+[[p] for p in pairs]
  matchings += [[a,b] for i,a in enumerate(pairs) for b in pairs[i+1:] if not set(a)&set(b)]
  self.assertEqual(len(matchings),10);queries=0
  for layers in itertools.product(matchings,repeat=3):
   schedule=[(f'L{i}',layer) for i,layer in enumerate(layers)];index=FutureEventIndex(schedule,4);gates=enumerated_oracle(schedule)
   for layer in range(4):
    past={g['gate_id'] for g in gates if g['layer']<layer};current=[g['gate_id'] for g in gates if g['layer']==layer]
    for consumed in range(len(current)+1):
     done=past|set(current[:consumed]);active=set(current[consumed:consumed+1])
     for q in range(4):
      for h in (1,2,4,8):
       self.assertEqual(index.query(q,layer,h,completed=done,active=active),oracle_query(gates,q,layer,h,done,active));queries+=1
  self.assertGreater(queries,100000)

 def test_repeated_partners_gaps_and_stable_gate_ids(self):
  schedule=[('A',[(0,1)]),('empty',[]),('C',[(0,2)]),('D',[(0,1)]),('E',[(0,1)])]
  index=FutureEventIndex(schedule,3);items=index.query(0,0,8)
  self.assertEqual([e['partner'] for e in items],[1,2,1,1]);self.assertEqual([e['logical_layer_delta'] for e in items],[0,2,3,4])
  self.assertEqual(index.query(0,5,8),[])
  circuit=circuit_from_pairs(3,[(0,1),(0,2),(0,1),(0,1)])
  circuit['gates'][0]['gate_id']='stable_first';self.assertEqual(FutureEventIndex(schedule,3,circuit).query(0,0,1)[0]['gate_id'],'stable_first')

 def test_option_and_input_rejection(self):
  for key,value in [('h',0),('h',-1),('gamma',0),('gamma',1.01),('gamma',float('nan')),('weight_mode','critical_path'),('assignment_future_bias',True),('current_distance_weight',1)]:
   p=config();p[key]=value
   with self.assertRaises(ValueError):validate_options(p)
  for schedule in [[('a',[(0,1),(0,2)])],[('a',[(0,0)])],[('a',[(0,3)])],[('a',[]),('a',[])]]:
   with self.assertRaises(ValueError):FutureEventIndex(schedule,3)
  index=FutureEventIndex([('a',[])],2)
  with self.assertRaises(ValueError):index.query(0,0,0)
  with self.assertRaises(ValueError):index.query(2,0,1)
  with self.assertRaises(ValueError):index.query(0,-1,1)

 def test_current_layer_pending_active_and_consumed(self):
  index=FutureEventIndex([('a',[(0,1),(2,3)]),('b',[(0,2)])],4)
  active={'g000000'}
  self.assertEqual(index.query(2,0,1,active=active)[0]['logical_layer_delta'],0)
  self.assertEqual(index.query(0,0,1,active=active)[0]['gate_id'],'g000002')
  self.assertEqual(index.query(0,0,1,completed=active)[0]['gate_id'],'g000002')
  self.assertEqual(index.query(1,0,8,completed=active),[])

 def test_hand_calculated_two_partner_compromise(self):
  events=[{'gate_id':'a','partner':1,'logical_layer_delta':1},{'gate_id':'b','partner':2,'logical_layer_delta':2}]
  anchors={1:(0,1),2:(4,1)};sites=[(0,0),(2,1)]
  one=FuturePotential.from_events(events[:1],anchors,gamma=1,spacing_um=1);two=FuturePotential.from_events(events,anchors,gamma=1,spacing_um=1)
  self.assertEqual(one.choose(sites,(0,0))[0],(0,0));self.assertEqual(two.choose(sites,(0,0))[0],(2,1))
  self.assertAlmostEqual(two.score((0,0))['raw_distance_um'],1+math.sqrt(17));self.assertEqual(two.score((2,1))['raw_distance_um'],4)
  self.assertEqual(FuturePotential.from_events(events,anchors,gamma=.9,spacing_um=1).choose(sites,(0,0))[0],(2,1))

 def test_missing_anchors_no_refill_and_center_fallback(self):
  index=FutureEventIndex([('a',[(0,1)]),('b',[(0,2)])],3);events=index.query(0,0,1)
  potential=FuturePotential.from_events(events,{2:(9,9)},gamma=.9,spacing_um=3)
  self.assertFalse(potential.resolved);self.assertEqual(potential.missing_gate_ids,('g000000',))
  self.assertEqual(potential.choose([(1,0),(0,1)],(0,0))[0],(0,1))
  self.assertIsNone(potential.choose([],(0,0))[0])

 def test_numerical_discount_scaling_and_snapshot_copy(self):
  events=[{'gate_id':'far','partner':1,'logical_layer_delta':100000}];positions={1:[0,3]}
  potential=FuturePotential.from_events(events,positions,gamma=.9,spacing_um=3);positions[1][1]=100
  self.assertEqual(potential.choose([(0,0),(0,2)],(0,0))[0],(0,2))
  self.assertTrue(potential.score((0,2))['raw_underflow']);self.assertEqual(potential.score((0,2))['scaled_distance_um'],3)

 def test_generalized_h1_pure_distance_not_source_legacy(self):
  case=manual_case();ctx=LookaheadContext([('a',[]),('b',[(0,1)])],2,None,config(),1)
  ctx.begin_layer('a');ctx.begin_batch([],[],{0:(0,0),1:(0,6)},{1:(0,6)})
  from implementation.lookahead.integration import load_core
  source=load_core();options=source.CompilerOptions(**baseline())
  kwargs={'qubit':0,'available_positions':[(0,1),(0,5)],'current_qubit_positions':{0:(0,0)},'final_target_positions':{1:(0,6)},
          'center_of_mass':(0,0),'current_future_partners':{0:[(1,1)]},'options':options,'rng':random.Random(42),'max_partner_dist':2,'is_evicted':True}
  legacy=source._pick_idle_position(**kwargs);new=ctx.pick(**kwargs)
  self.assertEqual(legacy,(0,1));self.assertEqual(new,(0,5)) # positive gamma scales pure distance; source sums current distance

 def test_no_access_to_future_chosen_positions(self):
  class Forbidden:
   def get(self,*args):raise AssertionError('Future placement accessed')
   def __contains__(self,*args):raise AssertionError('Future placement accessed')
  ctx=LookaheadContext([('a',[]),('b',[(0,1)])],2,None,config(),1);ctx.begin_layer('a')
  now={0:[0,0],1:[0,4]};committed={1:[0,3]};ctx.begin_batch([],[],now,committed)
  now[1][1]=99;committed[1][1]=99
  chosen=ctx.pick(qubit=0,available_positions=[(0,1),(0,2)],is_evicted=True,center_of_mass=(0,0),
                  final_target_positions=Forbidden(),current_future_partners=Forbidden())
  self.assertEqual(chosen,(0,2));self.assertEqual(ctx.decisions[-1]['resolved_anchors'][0]['site'],[0,3])

 def test_cursor_rejects_unexecuted_predecessors(self):
  ctx=LookaheadContext([('a',[(0,1)]),('b',[(0,1)])],2,None,config())
  with self.assertRaises(ValueError):ctx.begin_layer('b')
  ctx.begin_layer('a');ctx.begin_batch([(0,1)],[0],{}, {0:(0,0),1:(0,1)})
  with self.assertRaises(ValueError):ctx.begin_layer('b')
  ctx.complete_batch([(0,1)]);ctx.begin_layer('b')

 def test_legacy_exact_full_schedules_and_frozen_fixture(self):
  case=manual_case();cfg=config('legacy_exact')
  for seed in (42,43):
   direct=direct_source_control(case['schedule'],4,case['layout'],case['geometry'],case['options'],routing_seed=seed)
   hooked=compile_schedule(case['schedule'],4,case['layout'],case['geometry'],case['options'],cfg,circuit=case['circuit'],routing_seed=seed)
   self.assertEqual(direct['instructions'],hooked['instructions']);self.assertEqual(direct['random_state_after_sha256'],hooked['random_state_after_sha256'])
   if seed==42:self.assertEqual(hooked['instructions'],(ROOT/'runs/phase_00/compiled_fixture_01/instructions.txt').read_text())
   self.assertGreater(hooked['statistics']['eviction_calls'],0)

 def test_serialized_compiler_consumption_and_compatibility(self):
  case=serialized_case();opts=baseline();direct=direct_source_control(case['schedule'],4,case['layout'],case['geometry'],opts)
  legacy=compile_schedule(case['schedule'],4,case['layout'],case['geometry'],opts,config('legacy_exact'),circuit=case['circuit'])
  self.assertEqual(direct['instructions'],legacy['instructions'])
  for name in ['next_events_h1','next_events_h2','next_events_h4','next_events_h8']:
   c=compile_schedule(case['schedule'],4,case['layout'],case['geometry'],opts,config(name),circuit=case['circuit'])
   self.assertGreater(len(c['batches']),len(case['schedule']))
   for d in c['decisions']:
    for e in d.get('events',[]):self.assertNotIn(e['gate_id'],set(d['completed_gate_ids'])|set(d['active_gate_ids']))
   self.assertEqual(c['statistics']['completed_gate_count'],8)

 def test_every_produced_fixture_validates_with_common_model(self):
  for case in [manual_case(),serialized_case()]:
   opts=case.get('options',baseline())
   for name in ['legacy_exact','next_events_h1','next_events_h2','next_events_h4','next_events_h8']:
    c=compile_schedule(case['schedule'],4,case['layout'],case['geometry'],opts,config(name),circuit=case['circuit'])
    result=evaluate_compilation(c,case['circuit'],case['geometry'],physics())
    self.assertTrue(result['accepted_schedule'],(name,result['source_validation'],result['result']['validation']))
    self.assertFalse(result['native_physical_validity_claimed'])

 def test_actual_parking_after_consumed_same_layer_gate(self):
  # Force the original planner's static-slot path so a later serialized batch
  # really evicts qubits whose gate already ran in this logical layer.
  case=serialized_case();opts=baseline();opts.update(variant_name='phase04_static_serialization_adversary',enable_keep_adjacent=False,enable_one_qubit_move=False)
  c=compile_schedule(case['schedule'],4,case['layout'],case['geometry'],opts,config('next_events_h4'),circuit=case['circuit'])
  gates=enumerated_oracle(case['schedule']);gate_layer={g['gate_id']:g['layer'] for g in gates};checked=0
  for d in c['decisions']:
   if d['is_evicted'] and any(gate_layer[gid]==d['logical_layer'] for gid in d['completed_gate_ids']):
    self.assertEqual(d['events'],oracle_query(gates,d['qubit'],d['logical_layer'],4,set(d['completed_gate_ids']),set(d['active_gate_ids'])))
    self.assertTrue(all(e['logical_layer_delta']>0 for e in d['events']));checked+=1
  self.assertGreater(checked,0)
  evaluated=evaluate_compilation(c,case['circuit'],case['geometry'],physics());self.assertTrue(evaluated['accepted_schedule'],evaluated['result']['validation'])

 def test_larger_h_can_worsen_full_error(self):
  example=worse_horizon_example(physics())
  for item in example.values():self.assertEqual(item['result']['status'],'ok',item['result']['validation'])
  self.assertEqual(example['1']['chosen_site'],[0,2]);self.assertEqual(example['2']['chosen_site'],[2,1])
  occupied={(0,0),(0,3),(4,1)}
  self.assertTrue(all(tuple(item['chosen_site']) not in occupied for item in example.values()))
  self.assertGreater(example['2']['result']['budget']['total_E'],example['1']['result']['budget']['total_E'])
  self.assertGreater(example['2']['result']['makespan_us'],example['1']['result']['makespan_us'])

 def test_deterministic_queries_ties_and_sparse_storage(self):
  p=FuturePotential.from_events([{'gate_id':'g','partner':1,'logical_layer_delta':1}],{1:(0,0)},gamma=.9,spacing_um=1)
  a=[(0,1),(1,0),(0,-1)]
  for perm in itertools.permutations(a):self.assertEqual(p.choose(list(perm),(0,0))[0],(0,-1))
  index=FutureEventIndex([('a',[(0,1)]),('b',[(0,1)])],1000)
  self.assertLess(reachable_bytes(index),1000000);self.assertEqual(len(index.events_by_qubit[999]),0)
  for _ in range(3):self.assertEqual(index.query(0,0,8),index.query(0,0,8))

 def test_original_artifacts_unchanged(self):
  frozen=json.loads((ROOT/'reports/phase_04/start_record.json').read_text())['frozen_artifact_sha256']
  receipt=json.loads((ROOT/'reports/phase_04/concurrent_controller_change.json').read_text())
  self.assertEqual(receipt['starting_sha256'],frozen[receipt['path']])
  self.assertEqual(hashlib.sha256((ROOT/receipt['path']).read_bytes()).hexdigest(),receipt['current_sha256'])
  self.assertFalse(receipt['phase04_modified_this_file'])
  changed=[p for p,h in frozen.items() if p!=receipt['path'] and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
  self.assertEqual(changed,[])


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise ValueError('Use a new output path under btp_work')
 out.mkdir(parents=True)
 with (out/'unittest.txt').open('w',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Acceptance))
 files=list((ROOT/'implementation/lookahead').glob('*.py'))+list((ROOT/'configs/variants').glob('lookahead.*.json'))+[Path(__file__).resolve()]
 summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),
          'artifact_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'python':sys.version,'command':sys.argv}
 (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='artifact_sha256'}))
 if not result.wasSuccessful():print((out/'unittest.txt').read_text())
 return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())