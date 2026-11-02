"""Run only missing paper targets, one at a time, with owned-family caps.

Status is read-only. Run defaults to at most one missing target and never
repeats a compatible successful corrected compilation. No optional sweeps.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from baseline_campaign import process_family,memory_handle,memory_peak,environment


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);temporary=p.with_suffix(p.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8');temporary.replace(p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def owned_job(process):
    """Windows kill-on-close job: a controller crash also stops its worker.

    Descendants inherit job membership. Assignment failure is fatal rather
    than silently leaving an unowned benchmark running after controller exit.
    """
    class BASIC(ctypes.Structure):
        _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
            ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),
            ('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),
            ('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_=[(name,ctypes.c_ulonglong) for name in ['ReadOperationCount','WriteOperationCount',
            'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
    class EXTENDED(ctypes.Structure):
        _fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),
            ('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];kernel.CreateJobObjectW.restype=wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateJobObjectW(None,None)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    info=EXTENDED();info.BasicLimitInformation.LimitFlags=0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    try:
        if not kernel.SetInformationJobObject(handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        # The initial thread is still suspended; descendants cannot exist yet.
        for pid in [process.pid]:
            child=kernel.OpenProcess(0x0501,False,pid) # QUERY_INFORMATION | SET_QUOTA | TERMINATE
            if not child:
                if process.poll() is not None:continue
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                # A venv redirector can spawn the real interpreter between
                # assignment and enumeration. Query membership before trying
                # to assign an already-inherited descendant a second time.
                kernel.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)]
                inside=wintypes.BOOL()
                if not kernel.IsProcessInJob(child,handle,ctypes.byref(inside)):
                    raise ctypes.WinError(ctypes.get_last_error())
                if not inside.value and not kernel.AssignProcessToJobObject(handle,child):
                    raise ctypes.WinError(ctypes.get_last_error(), 'AssignProcessToJobObject failed for suspended worker')
            finally:kernel.CloseHandle(child)
        return kernel,handle
    except Exception:
        kernel.CloseHandle(handle);raise


def resume_initial_thread(pid):
    """Resume the single initial thread after assigning the suspended root."""
    class THREADENTRY32(ctypes.Structure):
        _fields_ = [(name, kind) for name, kind in [
            ('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
            ('th32ThreadID', wintypes.DWORD), ('th32OwnerProcessID', wintypes.DWORD),
            ('tpBasePri', wintypes.LONG), ('tpDeltaPri', wintypes.LONG),
            ('dwFlags', wintypes.DWORD)]]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
    kernel.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
    kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenThread.restype = wintypes.HANDLE
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(4, 0)  # TH32CS_SNAPTHREAD
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    tids = []
    try:
        entry = THREADENTRY32(); entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while more:
            if entry.th32OwnerProcessID == pid: tids.append(entry.th32ThreadID)
            more = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(snapshot)
    if len(tids) != 1:
        raise OSError('Expected one initial thread in suspended worker; found ' + str(tids))
    thread = kernel.OpenThread(0x0002, False, tids[0])  # THREAD_SUSPEND_RESUME
    if not thread: raise ctypes.WinError(ctypes.get_last_error())
    try:
        previous = kernel.ResumeThread(thread)
        if previous == 0xffffffff: raise ctypes.WinError(ctypes.get_last_error())
        if previous != 1: raise OSError('Unexpected initial thread suspend count: ' + str(previous))
    finally:
        kernel.CloseHandle(thread)


def start_owned_process(command, **kwargs):
    """Contain the process before Python's venv redirector can spawn a child.

    Creating a running redirector then assigning its unordered process family
    races inherited Windows jobs. CREATE_SUSPENDED removes that window. Every
    descendant inherits the root's kill-on-close job after ResumeThread.
    """
    flags = kwargs.pop('creationflags', 0) | 0x00000004  # CREATE_SUSPENDED
    process = subprocess.Popen(command, creationflags=flags, **kwargs)
    kernel = handle = None
    try:
        kernel, handle = owned_job(process)
        resume_initial_thread(process.pid)
        return process, kernel, handle
    except BaseException:
        if handle is not None: kernel.CloseHandle(handle)
        if process.poll() is None: process.kill()
        process.wait(timeout=5)
        raise


def retryable_controller_failure(record):
    """Only recover the archived pre-repair access-denied launch failures."""
    error = record.get('monitor_error') or {}
    return (record.get('status') == 'error' and record.get('result') is None
        and record.get('launcher_protocol') != 'windows-suspended-job-v1'
        and error.get('type') == 'PermissionError'
        and '[WinError 5]' in error.get('message', '')
        and record.get('peak_working_set_bytes') == 0
        and not record.get('worker_artifact_sha256')
        and 0 <= record.get('process_wall_seconds', float('inf')) < 1)


def completed_compatible(job):
    base=ROOT/'runs/paper_focus_v2/fresh_compilations'/job['target_id']
    worker_hash=sha(ROOT/'tools/corrected_dasatom_worker.py');router_hash=sha(ROOT/'implementation/corrected/dasatom_routes.py')
    for p in sorted(base.glob('attempt_*/attempt_record.json')):
        value=read(p)
        if value['status']=='ok' and value.get('worker_sha256')==worker_hash and value.get('router_sha256')==router_hash:return p
    return None


def retry_budget(job,explicit=None):
    if explicit is not None:return explicit
    return 3600 if job['case']=='qv_n16_d5' else (6000 if job['case']=='square_root_7' else job['retry_timeout_seconds'])


def exhausted_same_cap(job,timeout):
    base=ROOT/'runs/paper_focus_v2/fresh_compilations'/job['target_id']
    worker_hash=sha(ROOT/'tools/corrected_dasatom_worker.py');router_hash=sha(ROOT/'implementation/corrected/dasatom_routes.py')
    for p in base.glob('attempt_*/attempt_record.json'):
        value=read(p)
        if value.get('worker_sha256')==worker_hash and value.get('router_sha256')==router_hash and value.get('timeout_seconds',0)>=timeout and value['status'] in ['timeout','out_of_memory','unsupported','error']:
            return p
    return None


def bounded_job(job,timeout,output_root=None,worker_path=None,router_path=None,input_path=None,env_extra=None,progress_callback=None,stop_check=None,heartbeat_gap_limit=None):
    output_root=Path(output_root or ROOT/'runs/paper_focus_v2/fresh_compilations').resolve()
    if not output_root.is_relative_to(ROOT):raise ValueError('Output must stay under btp_work')
    base=output_root/job['target_id']
    worker_path=Path(worker_path or ROOT/'tools/corrected_dasatom_worker.py')
    router_path=Path(router_path or ROOT/'implementation/corrected/dasatom_routes.py')
    worker_hash=sha(worker_path);router_hash=sha(router_path)
    for p in sorted(base.glob('attempt_*/attempt_record.json')):
        previous=read(p)
        if previous['status']=='ok' and previous.get('worker_sha256')==worker_hash and previous.get('router_sha256')==router_hash:
            return {'target_id':job['target_id'],'status':'reused_corrected_compilation','record':str(p.relative_to(ROOT))}
    number=len(list(base.glob('attempt_*')))+1;out=base/f'attempt_{number:02}'
    out.mkdir(parents=True)
    source=Path(input_path or ROOT/'benchmarks/current_baseline_v1/normalized'/job['family']/(job['case']+'_native.qasm'))
    if sha(source)!=job['expected_normalized_sha256']:raise ValueError('Frozen normalized input mismatch')
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-X','utf8',str(worker_path),
        '--input',str(source),'--grid',str(job['grid']),'--seed',str(job['seed']),'--out',str(out/'worker')]
    request={'target_id':job['target_id'],'command':command,'worker_sha256':worker_hash,'router_sha256':router_hash,
        'input_sha256':sha(source),'timeout_seconds':timeout,'memory_limit_bytes':4*1024**3,'attempt':number,
        'launcher_protocol':'windows-suspended-job-v1','launcher_sha256':sha(Path(__file__))}
    write(out/'request.json',request);started=time.monotonic();handles={};kernel=None;peak=0;forced=None;monitor_error=None
    with (out/'stdout.txt').open('w',encoding='utf-8') as stdout,(out/'stderr.txt').open('w',encoding='utf-8') as stderr:
        child_env=environment();child_env.update(env_extra or {})
        try:process,job_kernel,job_handle=start_owned_process(command,cwd=ROOT.parent,env=child_env,stdout=stdout,stderr=stderr)
        except OSError as exc:
            record={**request,'status':'error','error':{'type':type(exc).__name__,'message':str(exc),'stage':'suspended_launch','traceback':traceback.format_exc()},'process_wall_seconds':time.monotonic()-started,'record_path':str((out/'attempt_record.json').relative_to(ROOT))}
            write(out/'attempt_record.json',record);return record
        last_progress=0.0;last_poll=time.monotonic()
        try:
            while process.poll() is None:
                if heartbeat_gap_limit and time.monotonic()-last_poll>heartbeat_gap_limit:
                    forced='interrupted_by_unmonitored_gap';break
                last_poll=time.monotonic()
                if stop_check is not None and stop_check():forced='interrupted_by_user';break
                for pid in process_family(process.pid):
                    if pid not in handles:
                        try:kernel,handles[pid]=memory_handle(pid)
                        except OSError:continue
                peak=max(peak,sum(v for handle in handles.values() if (v:=memory_peak(handle)) is not None))
                if progress_callback is not None and time.monotonic()-last_progress>=2:
                    progress_callback({'worker_pid':process.pid,'wall_seconds':time.monotonic()-started,'peak_working_set_bytes':peak})
                    last_progress=time.monotonic()
                if time.monotonic()-started>timeout:forced='timeout';break
                if peak>request['memory_limit_bytes']:forced='out_of_memory';break
                time.sleep(.2)
            if heartbeat_gap_limit and time.monotonic()-last_poll>heartbeat_gap_limit:
                forced='interrupted_by_unmonitored_gap'
        except KeyboardInterrupt:forced='interrupted_by_user'
        except Exception as exc:
            forced='error';monitor_error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        finally:
            if forced:
                # Freeze only this worker's owned process family. Never target
                # the former campaign or unrelated Python processes.
                for pid in process_family(process.pid):
                    if pid not in handles:
                        try:kernel,handles[pid]=memory_handle(pid)
                        except OSError:continue
                for handle in handles.values():kernel.TerminateProcess(handle,1)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            for handle in handles.values():kernel.CloseHandle(handle)
            if job_handle is not None:job_kernel.CloseHandle(job_handle)
    result_path=out/'worker/result.json'
    try:result=read(result_path) if result_path.exists() else None
    except (OSError,json.JSONDecodeError) as exc:
        result=None;monitor_error={'type':type(exc).__name__,'message':str(exc)}
    artifact_hashes={p.relative_to(out).as_posix():sha(p) for p in (out/'worker').rglob('*') if p.is_file()}
    record={**request,'status':forced or (result or {}).get('status','error'),
        'process_exit_code':process.returncode,'process_wall_seconds':time.monotonic()-started,
        'peak_working_set_bytes':peak,'memory_definition':'observed sum of family peak working sets; not allocation-proof hard cap',
        'monitored_process_ids':sorted(handles),
        'result':result,'worker_artifact_sha256':artifact_hashes,'monitor_error':monitor_error,'record_path':str((out/'attempt_record.json').relative_to(ROOT))}
    write(out/'attempt_record.json',record);return record


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['status','run']);parser.add_argument('--target')
    parser.add_argument('--limit',type=int,default=1);parser.add_argument('--timeout',type=float)
    args=parser.parse_args();plan=read(ROOT/'configs/studies/paper_focus_v2.json')
    jobs=[j for j in plan['jobs'] if j['action']=='one_targeted_retry_required_no_complete_trace']
    if args.target:jobs=[j for j in jobs if args.target in [j['target_id'],j['case']]]
    complete=[j for j in jobs if completed_compatible(j)]
    jobs=[j for j in jobs if not completed_compatible(j)]
    held=[j for j in jobs if exhausted_same_cap(j,retry_budget(j,args.timeout))]
    jobs=[j for j in jobs if not exhausted_same_cap(j,retry_budget(j,args.timeout))]
    if args.mode=='status':
        print(json.dumps({'paper_targets':132,'existing_RFT_targets_reused':66,'cached_DasAtom_targets':57,
            'missing_trace_targets':[j['target_id'] for j in jobs],
            'new_corrected_targets_already_complete':len(complete),
            'held_after_failed_same_cap_attempt':[j['target_id'] for j in held],
            'new_blanket_repeats':False,'background_campaign_running':False},indent=2));return 0
    if args.limit<1:raise ValueError('Use a positive finite job limit')
    import msvcrt
    lock_path=ROOT/'runs/paper_focus_v2/controller.lock';lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            for job in jobs[:args.limit]:
                if completed_compatible(job):continue
                timeout=retry_budget(job,args.timeout)
                if not 0<timeout<=7200:raise ValueError('Timeout must be finite, positive and at most 7200 seconds')
                result=bounded_job(job,timeout)
                print(json.dumps({'target':job['target_id'],'status':result['status'],'record':result.get('record_path',result.get('record'))}),flush=True)
                if result['status']=='interrupted_by_user':return 130
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    return 0


if __name__=='__main__':raise SystemExit(main())
