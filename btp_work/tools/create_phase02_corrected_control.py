"""Generate one separately labelled conservative DasAtom routing control."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from implementation.adapters.upstream import adapt_run
from implementation.adapters.vacancy_control import corrected_trace
from implementation.trace.model import save_trace
from implementation.validation.checker import check_trace
from implementation.metrics.legacy import measure_trace


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output must stay under btp_work')
    if out.exists():raise FileExistsError('Use new output path')
    source=adapt_run(args.run,'dasatom');native=json.loads((args.run/'native_dasatom.json').read_text())
    started=time.perf_counter();trace=corrected_trace(native,source['metadata']['circuit'],source['metadata']['hardware'],source['metadata']['origin'])
    transform_seconds=time.perf_counter()-started;validation=check_trace(trace);metrics=measure_trace(trace)
    out.mkdir(parents=True);save_trace(out/'trace',trace)
    for name,value in [('validation',validation),('metrics',metrics)]:
        (out/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    summary={'control':'dasatom_corrected_vacancy_v1','source_worker':str(args.run),
        'transform_seconds':transform_seconds,'status':validation['status'],
        'fully_validated_within_model':validation['fully_validated_within_model'],
        'source_physical_evidence_complete':False,'original_native_output_unchanged':True,
        'not_native_compile_runtime':True,'decision':'D003',
        'implementation_sha256':hashlib.sha256((ROOT/'implementation/adapters/vacancy_control.py').read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))
    return 0 if validation['status']=='ok' else 2


if __name__=='__main__':raise SystemExit(main())
