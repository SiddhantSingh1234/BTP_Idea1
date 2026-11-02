"""Immutable Phase 02 adapter/checker/metrics entry point. Stdlib only."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from implementation.adapters.upstream import adapt_run
from implementation.trace.model import load_trace,save_trace
from implementation.validation.checker import check_trace
from implementation.metrics.legacy import measure_trace


def beneath_work(path):
    target=Path(path).resolve()
    if not target.is_relative_to(ROOT): raise ValueError('All outputs must remain under btp_work')
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    adapt=sub.add_parser('adapt')
    adapt.add_argument('--run',required=True,type=Path)
    adapt.add_argument('--algorithm',required=True,choices=['rft','dasatom'])
    adapt.add_argument('--timing',default='evidence',choices=['evidence','two_transfer_stages'])
    adapt.add_argument('--out',required=True,type=Path)
    check=sub.add_parser('check');check.add_argument('--trace',required=True,type=Path);check.add_argument('--out',required=True,type=Path)
    metrics=sub.add_parser('metrics');metrics.add_argument('--trace',required=True,type=Path);metrics.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=beneath_work(args.out)
    if out.exists(): parser.error('Output already exists; use a new path')
    if args.command=='adapt':
        trace=adapt_run(args.run,args.algorithm,args.timing);save_trace(out,trace)
        print(json.dumps({'trace':str(out),'events':len(trace['events']),'timing_policy':args.timing}));return 0
    trace=load_trace(args.trace)
    result=check_trace(trace) if args.command=='check' else measure_trace(trace)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'output':str(out),'status':result.get('status','metrics_written')}))
    return 2 if result.get('status')=='invalid' else (3 if result.get('status')=='unsupported' else 0)


if __name__=='__main__':
    raise SystemExit(main())
