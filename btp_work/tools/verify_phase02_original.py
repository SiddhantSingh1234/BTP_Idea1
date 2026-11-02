"""Produce an immutable full-original-circuit restoration sidecar and comparison."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','RAYON_NUM_THREADS','QISKIT_NUM_PROCS']:
    os.environ[key]='1'
os.environ['QISKIT_PARALLEL']='FALSE'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from implementation.trace.model import load_trace
from implementation.validation.full_circuit import verify_original
from implementation.validation.checker import check_trace


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--original',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output must be under btp_work')
    if out.exists():raise FileExistsError('Use a new output path')
    trace=load_trace(args.trace);validation=check_trace(trace)
    if not validation['structural_valid']:raise ValueError('Trace has known replay violations; no full-circuit success claim')
    result=verify_original(trace,args.original)
    result['comparison'].update(input_trace_status=validation['status'],
        trace_metadata_sha256=hashlib.sha256((args.trace/'metadata.json').read_bytes()).hexdigest(),
        trace_events_sha256=hashlib.sha256((args.trace/'events.jsonl').read_bytes()).hexdigest(),
        verifier_sha256=hashlib.sha256((ROOT/'implementation/validation/full_circuit.py').read_bytes()).hexdigest(),
        command=sys.argv)
    out.mkdir(parents=True)
    for name in ['comparison','operations']:
        (out/(name+'.json')).write_text(json.dumps(result[name],indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (out/'transpiled_full.qasm').write_text(result['transpiled_full_qasm']+'\n',encoding='utf-8')
    print(json.dumps(result['comparison']))
    return 0 if result['comparison']['equivalent_up_to_global_phase'] else 2


if __name__=='__main__':raise SystemExit(main())
