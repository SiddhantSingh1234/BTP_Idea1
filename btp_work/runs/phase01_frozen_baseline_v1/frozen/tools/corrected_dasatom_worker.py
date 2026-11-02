"""One corrected full DasAtom compilation; separate from cached repair times.

This worker does not schedule a campaign. Run it only through a bounded caller
for large inputs. Native vendor code stays immutable.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import random
import sys
import time
import traceback
sys.dont_write_bytecode=True
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS','QISKIT_NUM_PROCS']:
    os.environ[key]='1'
os.environ['QISKIT_PARALLEL']='FALSE'
CODE_ROOT=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('BTP_WORK_ROOT',CODE_ROOT)).resolve()
VENDOR_ROOT=Path(os.environ.get('BTP_VENDOR_ROOT',ROOT/'vendor')).resolve()
sys.path.insert(0,str(CODE_ROOT))
REV='73a6bdf0fd200b2733745211eaf2e0c1e17f496a'
sys.path.insert(0,str(VENDOR_ROOT/('DasAtom-'+REV)))
from implementation.corrected.dasatom_routes import repair_native,RoutingUnsupported,CapacityUnsupported
from implementation.trace.model import read_cz_qasm,save_trace
from implementation.validation.checker import check_trace
from implementation.metrics.legacy import measure_trace


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--grid',required=True,type=int);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--purpose',choices=['measurement','validation_smoke'],default='measurement');args=parser.parse_args()
    out=args.out.resolve();source=args.input.resolve()
    if not out.is_relative_to(ROOT) or not source.is_relative_to(ROOT) or out.exists():raise ValueError('Use existing input and new output under btp_work')
    out.mkdir(parents=True);result={'variant':'dasatom_corrected_v2','status':'error','source_revision':REV,
        'input':str(source.relative_to(ROOT)),'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'grid':args.grid,'seed':args.seed,'hash_seed':os.environ.get('PYTHONHASHSEED'),
        'command':sys.argv,'native_measurement':False,'purpose':args.purpose,
        'helper_sha256':hashlib.sha256((VENDOR_ROOT/('DasAtom-'+REV)/'DasAtom_fun.py').read_bytes()).hexdigest(),
        'router_sha256':hashlib.sha256((CODE_ROOT/'implementation/corrected/dasatom_routes.py').read_bytes()).hexdigest(),
        'code_root':str(CODE_ROOT)}
    def stage(name):
        (out/'stage.json').write_text(json.dumps({'stage':name,'wall_time':time.time()})+'\n',encoding='utf-8')
    log=io.StringIO()
    try:
        with contextlib.redirect_stdout(log):
            stage('imports')
            import DasAtom_fun as f
            from Enola.route import QuantumRouter
            from qiskit import QuantumCircuit
            from qiskit.converters import circuit_to_dag
            normalized_start=time.perf_counter()
            circuit=read_cz_qasm(source);n=circuit['num_qubits']
            if n>args.grid**2:raise CapacityUnsupported('Declared register exceeds requested grid')
            pairs=[g['qubits'] for g in circuit['gates']]
            active=max((max(p)+1 for p in pairs),default=0)
            qc=QuantumCircuit(active)
            for a,b in pairs:qc.cz(a,b)
            dag=circuit_to_dag(qc);random.seed(args.seed)
            started=time.perf_counter();timings={}
            def timed(name,fn):
                stage(name);before=time.perf_counter();value=fn();timings[name]=time.perf_counter()-before;return value
            if pairs:
                graph=timed('grid',lambda:f.generate_grid_with_Rb(args.grid,args.grid,2))
                partitions=timed('partition',lambda:f.partition_from_DAG(dag,graph))
                embeddings,extensions=timed('embeddings',lambda:f.get_embeddings(partitions,graph,active,args.grid,2))
                if extensions:raise CapacityUnsupported('Upstream requested a larger grid; matched hardware rejected')
                router=QuantumRouter(active,embeddings,partitions,[args.grid,args.grid])
                timed('native_route_proposals',router.run)
                movements=router.movement_list
                groups=timed('gate_groups',lambda:[f.get_parallel_gates(p,graph,e,4) for p,e in zip(partitions,embeddings)])
            else:partitions=[];embeddings=[];groups=[];movements=[]
            native={'embeddings':embeddings,'gate_groups':groups,'movement_list':movements,'partitions':partitions,'actual_grid':args.grid}
            trace,corrected=timed('corrected_routing',lambda:repair_native(native,circuit,args.grid,origin={'input_sha256':result['input_sha256'],'dasatom_revision':REV}))
            compile_seconds=time.perf_counter()-started
            normalized_compile_seconds=time.perf_counter()-normalized_start-timings.get('grid',0)
            stage('independent_validation');validation=check_trace(trace);metrics=measure_trace(trace)
            save_trace(out/'trace',trace)
            for name,value in [('native_corrected',corrected),('validation',validation),('metrics',metrics)]:
                (out/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            result.update(status='ok' if validation['structural_valid'] else 'invalid',
                full_declared_register=n,active_prefix=active,CZ=len(pairs),corrected_compile_seconds=compile_seconds,
                normalized_compile_seconds=normalized_compile_seconds,
                normalized_compile_scope='normalized CZ QASM to complete schedule; excludes hardware graph setup, imports, validation and scoring',
                timing_scope='fresh grid/partition/embedding/gate grouping/corrected routing; excludes imports, input parsing, validation and scoring',
                stage_seconds=timings,physical_validation_status=validation['status'],
                full_physical_validity_claimed=False,known_violations=validation['violations'])
    except (RoutingUnsupported,CapacityUnsupported) as exc:result.update(status='unsupported',error={'type':type(exc).__name__,'message':str(exc)})
    except Exception as exc:result.update(status='error',error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
    (out/'stdout.txt').write_text(log.getvalue(),encoding='utf-8')
    (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result));return 0 if result['status']=='ok' else 2


if __name__=='__main__':raise SystemExit(main())
