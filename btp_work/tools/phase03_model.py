"""NEW Phase03 CLI; never overwrites outputs or edits original traces."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from implementation.trace.model import load_trace
from implementation.movement_error.profiles import load_profile
from implementation.movement_error.schedule import make_schedule,write_json_new,UnsupportedSchedule
from implementation.movement_error.checker import validate_schedule
from implementation.movement_error.evaluator import evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for command in ('rescore','transform'):
        p=sub.add_parser(command);p.add_argument('--trace',required=True,type=Path);p.add_argument('--profile',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
        if command=='transform':p.add_argument('--mode',choices=('retime','retime_and_cool'),default='retime')
    for command in ('check','evaluate'):
        p=sub.add_parser(command);p.add_argument('--schedule',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT) or out.exists():parser.error('Use a new output path under btp_work')
    if args.command in ('check','evaluate'):
        s=json.loads(args.schedule.read_text(encoding='utf-8'));r=validate_schedule(s) if args.command=='check' else evaluate(s)
        write_json_new(out,r,ROOT)
    else:
        started=time.perf_counter()
        try:
            s=make_schedule(load_trace(args.trace),load_profile(args.profile),'rescore' if args.command=='rescore' else args.mode)
            transformed=time.perf_counter();r=evaluate(s)
        except UnsupportedSchedule as exc:
            r={'status':'unsupported','reason':str(exc),'no_partial_schedule_accepted':True}
            write_json_new(out/'result.json',r,ROOT)
        else:
            write_json_new(out/'schedule.json',s,ROOT);write_json_new(out/'validation.json',r['validation'],ROOT);write_json_new(out/'result.json',r,ROOT)
            write_json_new(out/'timing.json',{'transform_seconds':transformed-started,'validation_scoring_seconds':time.perf_counter()-transformed,
                                            'not_native_compile_runtime':True,'command':sys.argv},ROOT)
    print(json.dumps({'status':r['status'],'output':str(out)}))
    return {'ok':0,'invalid':2,'unsupported':3}.get(r['status'],1)


if __name__=='__main__':raise SystemExit(main())