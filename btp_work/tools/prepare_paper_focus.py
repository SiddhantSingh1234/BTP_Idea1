"""Freeze a paper-complete, reuse-first replacement for the stopped campaign."""
import collections
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'runs/current_baseline/study_v1'
OUT=ROOT/'reports/phase_01/paper_focus_v2'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def signature(job):return (job['algorithm'],job['family'],job['case'],job['grid'],job['variant'],job['register_policy'])


def main():
    plan_path=ROOT/'configs/studies/paper_focus_v2.json'
    if plan_path.exists():raise FileExistsError('Revised plan already exists')
    old=read(STUDY/'plan.json');records=[];by_signature=collections.defaultdict(list)
    for path in sorted(STUDY.glob('attempts/*/attempt_*/attempt_record.json')):
        record=read(path);entry={'path':str(path.relative_to(ROOT)),'sha256':sha(path),'record':record}
        records.append(entry);by_signature[signature(record['job'])].append(entry)
    jobs=[]
    for job in old['jobs']:
        if job['priority']!=0 or job['repetition']!=1:continue
        candidates=sorted(by_signature[signature(job)],key=lambda e:(e['record']['job']['repetition'],e['record']['attempt']))
        complete=[]
        for entry in candidates:
            directory=(ROOT/entry['path']).parent/'worker'
            required=['result.json','normalized.qasm','instructions.txt' if job['algorithm']=='rft' else 'native_dasatom.json']
            if all((directory/p).exists() for p in required) and entry['record']['status'] not in ['timeout','out_of_memory','error']:
                if sha(directory/'normalized.qasm')!=job['expected_normalized_sha256']:raise ValueError('Frozen normalized input differs')
                complete.append(entry)
        selected=complete[0] if complete else None
        if job['algorithm']=='rft' and selected and selected['record']['status']=='ok':action='reuse_valid_native'
        elif selected:action='validate_or_repair_cached_dasatom'
        else:action='one_targeted_retry_required_no_complete_trace'
        jobs.append({'target_id':job['id'].rsplit('__r',1)[0],**{k:v for k,v in job.items() if k not in ['id','priority','repetition']},
            'paper_reference':'RFT manuscript p6 Fig4' if job['family']=='fig4_qft' else 'RFT manuscript p6 TableII',
            'paper_metrics':['compile_seconds','runtime_us','movement_batches','legacy_fidelity'] if job['family']=='fig4_qft' else ['compile_seconds','movement_batches','legacy_fidelity'],
            'action':action,'selected_reference':{'record':selected['path'],'sha256':selected['sha256'],'worker':str((ROOT/selected['path']).parent.relative_to(ROOT)/'worker')} if selected else None,
            'all_existing_attempts':[{'record':e['path'],'sha256':e['sha256'],'status':e['record']['status'],'repetition':e['record']['job']['repetition']} for e in candidates],
            'retry_timeout_seconds':1800 if selected is None else None,
            'fresh_corrected_compile_timing_required_if_route_changes':job['algorithm']=='dasatom'})
    if len(jobs)!=132 or len({j['target_id'] for j in jobs})!=132:raise ValueError('Paper coverage lost')
    revised={'schema':'paper-focus.v2','decision':'D005_STOP_REDUCE_REUSE_REPAIR','source_study':'runs/current_baseline/study_v1',
        'source_plan_sha256':sha(STUDY/'plan.json'),'paper_pdf_sha256':sha(ROOT.parent/'Papers/Priyanshu_Aditya_ISVLSI2026_AK_O.pdf'),
        'paper_page6_render':'reports/phase_01/paper_scope_evidence/page6.png',
        'paper_target_count':132,'paper_inputs':27,'fig4_qft_sizes':list(range(5,61,5)),
        'mandatory_grids':{'fig4_qft':[11,20,35],'tableII':[11,35]},
        'paper_baselines':['rft_snapshot_ladder7_configuration_unresolved_for_manuscript','dasatom_snapshot'],
        'all_four_fig4_metrics_preserved':True,'all_three_tableII_metrics_preserved':True,
        'paper_tableI_and_fig2':'Retain exact four-qubit worked-example test; no expensive benchmark jobs',
        'new_blanket_timing_repetitions':False,'retain_all_existing_timing_repetitions':True,
        'new_rft8_sweep':False,'new_active_prefix_sweep':False,
        'quality_policy':{'validate_every_available_trace':True,'reuse_all_completed_repetitions':True,
            'additional_timing':'Only if repeat variability materially affects a reported comparison; no automatic whole-matrix repeats',
            'additional_seeds':'Small representative development checks only, reported separately; no full-grid seed Cartesian product',
            'corrected_timing':'Original native time remains a reference; cached repair time is separate and never relabelled full compilation time'},
        'jobs':jobs}
    write(plan_path,revised)
    partial=[str(p.parent.relative_to(ROOT)) for p in STUDY.glob('attempts/*/attempt_*/request.json') if not (p.parent/'attempt_record.json').exists()]
    summary={'terminal_records':len(records),'source_statuses':dict(collections.Counter(e['record']['status'] for e in records)),
        'paper_unique_targets':len(jobs),'paper_attempts_already_saved':sum(len(j['all_existing_attempts']) for j in jobs),
        'actions':dict(collections.Counter(j['action'] for j in jobs)),
        'retired_extra_configured_jobs':sum(j['priority']!=0 for j in old['jobs']),
        'extra_attempts_already_saved_retained':sum(e['record']['job']['priority']!=0 for e in records),
        'interrupted_attempt_directories':partial,'record_inventory_sha256':hashlib.sha256(''.join(e['sha256'] for e in records).encode()).hexdigest(),
        'all_original_results_preserved':True,'background_resume_authorized_by_this_script':False}
    write(OUT/'reuse_inventory.json',summary)
    write(OUT/'frozen_record_inventory.json',[{'path':e['path'],'sha256':e['sha256']} for e in records])
    progress=read(STUDY/'progress.json');write(OUT/'progress_before_stop.json',progress)
    write(STUDY/'progress.json',{**progress,'state':'stopped_by_user','stop_receipt':'runs/current_baseline/stop_20261028_user_scope_change.json','replacement_plan':'configs/studies/paper_focus_v2.json'})
    print(json.dumps(summary))


if __name__=='__main__':main()
