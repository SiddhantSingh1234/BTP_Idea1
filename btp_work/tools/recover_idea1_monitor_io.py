"""Resume ONLY monitor I/O interruptions, with bounded atomic-write retries.

Scientific workers, inputs, caps and old attempts stay unchanged. This wrapper
waits for the existing controller to release its lock and then invokes its exact
run function with a logging-only retry shim. It does not extend the study budget.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True


def sha(path):
    with Path(path).open('rb') as h:return hashlib.file_digest(h,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def infrastructure_error(record):
    error=record.get('monitor_error') or {}
    return (record.get('status')=='error' and error.get('type')=='PermissionError'
            and '[WinError 5]' in error.get('message','')
            and 'budget.json' in error.get('message','') and record.get('result') is None)


def available(study):
    import msvcrt
    with (study/'controller.lock').open('r+b') as handle:
        try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return False
        handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
    return True


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--study',type=Path,required=True);args=parser.parse_args()
    study=args.study.resolve()
    if study.parent!=ROOT/'runs':raise ValueError('Study must stay in workspace runs')
    while not available(study):time.sleep(2)
    failed=[p for p in (study/'measurements').glob('*/attempt_*/attempt_record.json') if infrastructure_error(read(p))]
    receipt={'schema':'logging_only_recovery.v1','wrapper_sha256':sha(__file__),
        'affected_records':{str(p.relative_to(ROOT)):sha(p) for p in failed},
        'pre_recovery_csv_sha256':sha(study/'results.csv'),
        'scientific_worker_changed':False,'caps_changed':False,'budget_extended':False,
        'recovery_eligibility':'only monitor PermissionError at atomic budget-log replace, null worker result; at most two attempts per cell',
        'atomic_write_retry_seconds':3.}
    spec=importlib.util.spec_from_file_location('completion_frozen_controller',study/'frozen/tools/remaining_experiments.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    module.WORK=ROOT
    original_write,original_outcome=module.write,module.outcome
    retries=[]
    def write(path,value):
        started=time.monotonic()
        while True:
            try:return original_write(path,value)
            except PermissionError:
                if time.monotonic()-started>=3:raise
                retries.append(str(Path(path).relative_to(ROOT)));time.sleep(.05)
    def outcome(study_path,job):
        record=original_outcome(study_path,job)
        if record and infrastructure_error(record):return {**record,'status':'interrupted_monitor_io'}
        return record
    module.write,module.outcome=write,outcome
    import run_paper_focus as bounded
    bounded.write=write
    write(study/'logging_recovery_provenance.json',receipt)
    if failed:
        result=module.run(study,'all')
        print(json.dumps({'recovery_controller_state':result['state']}),flush=True)
    receipt.update(atomic_write_retry_count=len(retries),atomic_write_retry_paths=retries,
        post_recovery_csv_sha256=sha(study/'results.csv'),
        post_recovery_summary=read(study/'summary.json'))
    write(study/'logging_recovery_provenance.json',receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
