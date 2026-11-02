"""Real detached launcher, partial-suite resume and idempotence acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
sys.dont_write_bytecode=True
from remaining_experiments import read,write,sha


def main():
    study=ROOT/'runs/remaining_experiments_resume_01'
    out=ROOT/'reports/phase_07/bounded_resume_01'
    if study.exists() or out.exists():raise ValueError('Fresh fixed integration test paths required')
    out.mkdir(parents=True)
    commands=[]
    def launch(suite):
        cmd=['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/Start-RemainingExperiments.ps1'),
             '-Study',str(study),'-Suite',suite,'-Smoke','-MaxHours','0.1']
        result=subprocess.run(cmd,cwd=ROOT,text=True,encoding='utf-8',capture_output=True,timeout=45)
        commands.append({'command':cmd,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        if result.returncode:raise AssertionError(commands[-1])
        deadline=time.monotonic()+100
        # Verify completion by process lock, not an old progress file from the
        # preceding launch. The new launcher PID can be a venv redirector.
        stamp=time.time()
        while time.monotonic()<deadline:
            if (study/'progress.json').exists():
                progress=read(study/'progress.json')
                if progress.get('suite')==suite.lower() and progress.get('state')=='selected_measurements_finished':
                    import msvcrt
                    with (study/'controller.lock').open('r+b') as h:
                        h.seek(0)
                        try:msvcrt.locking(h.fileno(),msvcrt.LK_NBLCK,1)
                        except OSError:pass
                        else:
                            msvcrt.locking(h.fileno(),msvcrt.LK_UNLCK,1)
                            return progress
            time.sleep(.2)
        raise TimeoutError('Detached test controller did not finish')
    first=launch('Weighting')
    assert first['status_counts'].get('not_run')==7,first
    original={p.relative_to(study).as_posix():sha(p) for p in (study/'measurements').glob('*/attempt_*/attempt_record.json')}
    second=launch('All')
    assert second['all_cells_terminal'],second
    assert second['status_counts']=={'reused_quality':1,'ok':7,'unsupported':1,'timeout':1},second
    for name,digest in original.items():assert sha(study/name)==digest,'Completed cell changed on resume'
    complete={p.relative_to(study).as_posix():sha(p) for p in (study/'measurements').glob('*/attempt_*/attempt_record.json')}
    launch('All')
    after={p.relative_to(study).as_posix():sha(p) for p in (study/'measurements').glob('*/attempt_*/attempt_record.json')}
    assert complete==after,'Idempotent relaunch repeated a terminal cell'
    result={'passed':True,'partial_suite_then_all_resumes':True,'terminal_attempt_records_unchanged':True,
        'completed_cells_not_repeated':True,'forced_timeout_preserved':True,'finite_resource_failure_preserved':True,
        'no_report_or_analysis_called':not read(study/'summary.json')['research_analysis_performed'],
        'final_status_counts':second['status_counts'],'commands':commands,'test_sha256':sha(Path(__file__))}
    write(out/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='commands'}));return 0
if __name__=='__main__':raise SystemExit(main())
