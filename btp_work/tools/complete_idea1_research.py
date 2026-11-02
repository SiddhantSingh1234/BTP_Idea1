"""Finish the existing run, recover logging interruptions, audit, analyse, freeze.

No new scientific settings are introduced. This is a finite postprocessing chain
for the authorized Idea1 study, so it does not require an agent to monitor jobs.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from audit_idea1_completion import read,write,sha
from recover_idea1_monitor_io import available


def main():
    out=ROOT/'reports/phase_09/completion_pipeline_01'
    if out.exists():raise FileExistsError('Preserve prior pipeline receipt')
    out.mkdir(parents=True)
    python=ROOT/'.venv/Scripts/python.exe'
    study=ROOT/'runs/idea1_completion_followup_v1'
    started=time.monotonic()
    def pulse(stage,**extra):
        record={'stage':stage,'updated_utc':datetime.now(timezone.utc).isoformat(),
                'elapsed_seconds':time.monotonic()-started,**extra}
        write(out/'progress.json',record);print(json.dumps(record),flush=True)
    pulse('waiting_for_existing_frozen_experiments')
    last=0
    while not available(study):
        if time.monotonic()-last>=55:
            pulse('waiting_for_existing_frozen_experiments',outcomes=read(study/'summary.json')['status_counts'])
            last=time.monotonic()
        time.sleep(2)
    # A previously queued recovery helper may acquire the released lock. Allow
    # that helper to enter/exit before invoking the current logging-only wrapper.
    time.sleep(5)
    commands=[
        ('recover_monitor_io',['tools/recover_idea1_monitor_io.py','--study','runs/idea1_completion_followup_v1']),
        ('independent_followup_replay',['tools/audit_idea1_completion.py','--study','runs/idea1_completion_followup_v1','--out','reports/phase_07/completion_followup_audit_01']),
        ('final_aggregate_analysis',['analysis/idea1_final_analysis.py','--out','reports/phase_08/completion_final_01']),
        ('clean_environment_rebuild',['tools/verify_idea1_clean_rebuild.py']),
        ('freeze_markdown_research',['tools/finalize_idea1_research.py','--finalize'])]
    receipts=[]
    for name,args in commands:
        pulse(name)
        with (out/(name+'_stdout.txt')).open('w',encoding='utf-8') as stdout,(out/(name+'_stderr.txt')).open('w',encoding='utf-8') as stderr:
            process=subprocess.Popen([str(python),'-B','-X','utf8',*args],cwd=ROOT,stdout=stdout,stderr=stderr)
            last=time.monotonic()
            while process.poll() is None:
                if time.monotonic()-last>=55:pulse(name,state='running');last=time.monotonic()
                time.sleep(1)
            code=process.returncode
        receipts.append({'stage':name,'exit_code':code,'stdout_sha256':sha(out/(name+'_stdout.txt')),'stderr_sha256':sha(out/(name+'_stderr.txt'))})
        write(out/'commands.json',receipts)
        if code:
            pulse('requires_investigation',failed_stage=name,exit_code=code)
            raise RuntimeError(name+' failed; inspect its preserved stderr log')
    release=ROOT/'final/idea1_research_release_v1'
    gate=read(release/'completion_gate.json')
    assert gate['status']=='complete' and gate['passed']==gate['total']
    index=read(release/'artifact_index.json')
    for path,record in index['files'].items():assert sha(ROOT/path)==record['sha256'],path
    write(out/'verification.json',{'status':'ok','release':'final/idea1_research_release_v1',
        'completion_gate_sha256':sha(release/'completion_gate.json'),'artifact_index_sha256':sha(release/'artifact_index.json'),
        'all_indexed_hashes_match':True,'script_sha256':sha(__file__),'commands':receipts,'elapsed_seconds':time.monotonic()-started})
    pulse('complete',release='final/idea1_research_release_v1')


if __name__=='__main__':main()
