"""Repair paper targets from saved native layouts, without rerunning VF2.

Native compile timings remain reference data. Only correction/validation times
are newly measured; changed pipelines need fresh timings for corrected T_comp.
"""
import collections
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from implementation.corrected.dasatom_routes import repair_native
from implementation.trace.model import read_cz_qasm,save_trace
from implementation.validation.checker import check_trace
from implementation.metrics.legacy import measure_trace


def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'runs/paper_focus_v2/cached_corrections');args=parser.parse_args()
    plan=json.loads((ROOT/'configs/studies/paper_focus_v2.json').read_text());out=args.out.resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output must remain under btp_work')
    if out.exists():raise FileExistsError('Cache repair output exists')
    out.mkdir(parents=True);rows=[]
    for job in plan['jobs']:
        if job['algorithm']!='dasatom' or not job['selected_reference']:continue
        directory=ROOT/job['selected_reference']['worker'];source=json.loads((directory/'result.json').read_text())
        destination=out/job['target_id'];started=time.perf_counter()
        row={'target_id':job['target_id'],'reference_worker':job['selected_reference']['worker'],
            'source_status':source['status'],'fresh_corrected_compile_seconds':None,
            'original_native_compile_seconds_reference':source['native_metrics']['adapter_pipeline_seconds']}
        try:
            native=json.loads((directory/'native_dasatom.json').read_text())
            circuit=read_cz_qasm(directory/'normalized.qasm')
            trace,corrected=repair_native(native,circuit,job['grid'],origin={'original_native_record':job['selected_reference']['record'],
                'original_native_record_sha256':job['selected_reference']['sha256'],'rft_revision':source['rft_revision'],'dasatom_revision':source['dasatom_revision']})
            row['correction_seconds']=time.perf_counter()-started
            validate_start=time.perf_counter();validation=check_trace(trace);metrics=measure_trace(trace)
            row.update(status='ok' if validation['structural_valid'] else 'invalid',physical_validation_status=validation['status'],
                discrete_schedule_valid=validation['structural_valid'],validation_seconds=time.perf_counter()-validate_start,
                restored_idle_qubits=trace['metadata']['register_repair']['restored_idle_qubits'],
                corrected_transitions=sum(not r['native_transition_reused'] for r in trace['metadata']['transition_reports']),
                native_transitions_reused=sum(r['native_transition_reused'] for r in trace['metadata']['transition_reports']),
                declared_qubits=circuit['num_qubits'],CZ=metrics['observed_CZ'],movement_batches=metrics['routing_batches'],
                fully_validated_within_model=validation['fully_validated_within_model'],physical_device_evidence_complete=False,
                legacy_fidelity=metrics['legacy']['fidelity_proxy'],legacy_runtime_us=metrics['legacy']['runtime_proxy_us'],
                derived_makespan_us=metrics['makespan_us'],violations=validation['violations'][:5])
            save_trace(destination/'trace',trace)
            write(destination/'native_corrected.json',corrected);write(destination/'validation.json',validation);write(destination/'metrics.json',metrics)
        except Exception as exc:
            row.update(status='unsupported' if type(exc).__name__ in ['RoutingUnsupported','CapacityUnsupported'] else 'error',
                error_type=type(exc).__name__,error=str(exc),correction_seconds=time.perf_counter()-started)
        write(destination/'repair_record.json',row);rows.append(row)
        print(json.dumps({'target':row['target_id'],'status':row['status'],'seconds':round(row['correction_seconds'],3)}),flush=True)
    summary={'targets':len(rows),'statuses':dict(collections.Counter(r['status'] for r in rows)),
        'restored_register_targets':sum(r.get('restored_idle_qubits',0)>0 for r in rows),
        'new_partition_or_embedding_runs':0,'original_compiler_reruns':0,
        'fresh_corrected_compile_times_measured':0,'existing_native_results_unchanged':True,
        'discrete_valid_targets':sum(r.get('discrete_schedule_valid',False) for r in rows),
        'corrected_model':'Legacy gate geometry, vacant SLM destinations and AOD line constraints; minimum physical path clearance remains unsupported',
        'implementation_sha256':hashlib.sha256((ROOT/'implementation/corrected/dasatom_routes.py').read_bytes()).hexdigest(),
        'results':rows}
    write(out/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='results'}))
    return 0 if all(r['status']=='ok' for r in rows) else 2


if __name__=='__main__':raise SystemExit(main())
