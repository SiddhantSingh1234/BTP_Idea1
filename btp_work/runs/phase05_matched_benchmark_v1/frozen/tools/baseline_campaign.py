"""Plan/run/resume a serial, resource-bounded current-source benchmark campaign.

All inputs, configurations, attempts, logs, traces, failures and metrics are local
to btp_work. This orchestrates unmodified upstream compilers, not new heuristics.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parent
PYTHON = WORK / ".venv/Scripts/python.exe"
DAS = WORK / "vendor/DasAtom-73a6bdf0fd200b2733745211eaf2e0c1e17f496a"
RFT = WORK / "vendor/NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a"
DEFAULT_STUDY = WORK / "runs/current_baseline/study_v1"


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def environment():
    env = dict(os.environ)
    for k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "RAYON_NUM_THREADS", "QISKIT_NUM_PROCS"]:
        env[k] = "1"
    env.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", QISKIT_PARALLEL="FALSE",
        MPLCONFIGDIR=str(WORK / ".compiler-tools/matplotlib"),
        XDG_CACHE_HOME=str(WORK / ".compiler-tools/xdg-cache"),
        TEMP=str(WORK / ".compiler-tools/tmp"), TMP=str(WORK / ".compiler-tools/tmp"))
    return env


def plan(study):
    if (study / "plan.json").exists():
        raise SystemExit("Study already planned; use run/resume")
    sys.dont_write_bytecode = True
    os.environ.update(environment())
    sys.path.insert(0, str(RFT / "src"))
    from qiskit import QuantumCircuit, qasm2, transpile
    from benchmark_runner import preprocess_circuit
    inventory = read(WORK / "configs/benchmarks/reproduction_manifest.json")
    table_names = [Path(e["path"]).stem for e in inventory["tableII"]]
    inputs = [("fig4_qft", f"qft_{n}", f"Data/qiskit-bench/qft/qft_{n}.qasm", [11, 20, 35]) for n in range(5, 61, 5)]
    inputs += [("tableII", n, f"Data/Q_Tetris/{n}.qasm", [11, 35]) for n in table_names]
    records, jobs = [], []
    for family, name, source_rel, grids in inputs:
        source = DAS / source_rel
        raw = WORK / "benchmarks/current_baseline_v1/raw" / family / (name + ".qasm")
        raw.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            shutil.copyfile(source, raw)
        assert sha(source) == sha(raw)
        started = time.perf_counter()
        qc = QuantumCircuit.from_qasm_file(str(raw))
        synthesized = transpile(qc, basis_gates=['cz','h','s','t','rx','ry','rz'], optimization_level=0)
        declared = preprocess_circuit(synthesized)
        prefix_n = max(declared.find_bit(q).index + 1 for ins in declared.data for q in ins.qubits)
        prefix = QuantumCircuit(prefix_n)
        for ins in declared.data:
            a, b = [declared.find_bit(q).index for q in ins.qubits]
            prefix.cz(a, b)
        normalized_paths = {}
        for policy, circuit in [("native", declared), ("active_prefix", prefix)]:
            target = WORK / "benchmarks/current_baseline_v1/normalized" / family / f"{name}_{policy}.qasm"
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = qasm2.dumps(circuit) + "\n"
            if target.exists():
                assert target.read_text(encoding="utf-8") == payload
            else:
                target.write_text(payload, encoding="utf-8")
            normalized_paths[policy] = {"path": target.relative_to(WORK).as_posix(), "sha256": sha(target)}
        record = {"family": family, "name": name, "source": source_rel, "raw_path": raw.relative_to(WORK).as_posix(),
            "raw_sha256": sha(raw), "declared_N": declared.num_qubits, "active_prefix_N": prefix_n,
            "CZ": len(declared.data), "layers": declared.depth(), "normalized": normalized_paths,
            "preprocessing_seconds": time.perf_counter() - started, "grids": grids,
            "synthesized_two_qubit_non_CZ": dict(__import__('collections').Counter(ins.operation.name for ins in synthesized.data if ins.operation.num_qubits == 2 and ins.operation.name != 'cz'))}
        records.append(record)
        for grid in grids:
            # All paper targets for native/default RFT7 and standalone DasAtom.
            controls = [(0, "rft", "7_dynamic_slot_01q_move", "native"), (0, "dasatom", "standalone", "native"),
                        (1, "rft", "8_optimized_eviction", "native")]
            # Separate matched register controls, not a silent historical edit.
            if prefix_n != declared.num_qubits:
                controls += [(1, "rft", "7_dynamic_slot_01q_move", "active_prefix"),
                             (1, "rft", "8_optimized_eviction", "active_prefix")]
            for priority, algorithm, variant, policy in controls:
                for rep in range(1, 4):
                    key = f"{family}__{name}__g{grid}__{algorithm}__{variant}__{policy}__r{rep}"
                    jobs.append({"id": key, "priority": priority, "algorithm": algorithm, "variant": variant,
                        "family": family, "case": name, "grid": grid, "register_policy": policy, "repetition": rep,
                        "seed": 42, "routing_seed": None, "raw_path": record["raw_path"],
                        "raw_sha256": record["raw_sha256"], "expected_normalized_sha256": normalized_paths[policy]["sha256"]})
    # First coverage pass of every native paper target before timing repeats/extras.
    jobs.sort(key=lambda j: (j["priority"], j["repetition"], j["algorithm"] == "dasatom", j["grid"], j["family"], j["case"]))
    config = {"schema": "current-baseline.campaign.v1", "created_utc": now(), "decision": "reports/decisions/D001_CURRENT_SOURCE_BASELINE.md",
        "source_scope": "latest_verified_public_sources_frozen_not_exact_paper_reproduction", "serial_measurement": True,
        "environment": "configs/environment/environment.json", "lock_sha256": sha(WORK / "configs/environment/requirements-py313-win64.lock"),
        "rft_commit": RFT.name.removeprefix("NAQC_Compiler-"), "dasatom_commit": DAS.name.removeprefix("DasAtom-"),
        "worker_sha256": sha(WORK / "tools/phase00_smoke.py"), "r_int": 2, "r_blk": 4,
        "numeric_threads": 1, "hash_seed": 0, "timing_repetitions": 3,
        "initial_timeout_seconds": 300, "slow_retry_timeout_seconds": 1800, "memory_limit_bytes": 4 * 1024**3,
        "timeout_scope": "worker wall time including imports, normalization, warmup and validation; native compile time separately recorded",
        "memory_scope": "Windows peak process working set queried every 0.2s; terminate observed breaches, not an allocation-proof hard cap",
        "censored_repeats": "Do not repeat the same timed-out/OOM case at the same cap; preserve planned non-attempts and slow-retry queue",
        "quality_seed_policy": "Fixed-seed timing repeats are not independent quality samples. Additional routing-seed pilots are separate records.",
        "paper_input_circuits": len(records), "paper_method_grid_targets": 132, "jobs": jobs, "inputs": records}
    write(study / "plan.json", config)
    write(WORK / "configs/studies/current_baseline_v1.json", {k:v for k,v in config.items() if k not in ['jobs','inputs']})
    print(json.dumps({"circuits": len(records), "native_paper_targets": 132, "planned_attempts_with_controls_and_repetitions": len(jobs)}, indent=2))


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(k, ctypes.c_size_t) for k in
        ["PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage"]]


def memory_handle(pid):
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    handle = k.OpenProcess(0x0411, False, pid)
    if not handle:
        raise OSError(ctypes.get_last_error(), "Cannot monitor worker memory")
    return k, handle


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize",wintypes.DWORD),("cntUsage",wintypes.DWORD),("th32ProcessID",wintypes.DWORD),
        ("th32DefaultHeapID",ctypes.c_size_t),("th32ModuleID",wintypes.DWORD),("cntThreads",wintypes.DWORD),
        ("th32ParentProcessID",wintypes.DWORD),("pcPriClassBase",wintypes.LONG),("dwFlags",wintypes.DWORD),
        ("szExeFile",wintypes.WCHAR*260)]


def process_family(root_pid):
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(PROCESSENTRY32W)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot==ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(),"Cannot enumerate worker descendants")
    entries=[]
    try:
        item=PROCESSENTRY32W();item.dwSize=ctypes.sizeof(item)
        ok=kernel.Process32FirstW(snapshot,ctypes.byref(item))
        while ok:
            entries.append((item.th32ProcessID,item.th32ParentProcessID))
            ok=kernel.Process32NextW(snapshot,ctypes.byref(item))
    finally:
        kernel.CloseHandle(snapshot)
    family={root_pid}
    for _ in range(len(entries)):
        found={pid for pid,parent in entries if parent in family}
        if found<=family:
            break
        family.update(found)
    return family


def memory_peak(handle):
    api = ctypes.WinDLL("psapi", use_last_error=True)
    api.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    obj = PROCESS_MEMORY_COUNTERS()
    obj.cb = ctypes.sizeof(obj)
    if not api.GetProcessMemoryInfo(handle, ctypes.byref(obj), obj.cb):
        return None
    return obj.PeakWorkingSetSize


def execute(study, job, timeout, attempt):
    out = study / "attempts" / job["id"] / f"attempt_{attempt:02}"
    out.mkdir(parents=True, exist_ok=False)
    command = [str(PYTHON), "-X", "utf8", str(WORK / "tools/phase00_smoke.py"), "--algorithm", job["algorithm"],
        "--case", "file", "--input", str(WORK / job["raw_path"]), "--grid", str(job["grid"]),
        "--register-policy", job["register_policy"], "--seed", str(job["seed"]), "--out", out.relative_to(WORK).as_posix() + "/worker"]
    if job["algorithm"] == "rft":
        command += ["--variant", job["variant"]]
    if job.get("routing_seed") is not None:
        command += ["--routing-seed", str(job["routing_seed"])]
    request = {"job": job, "attempt": attempt, "command": command, "started_utc": now(),
        "timeout_seconds": timeout, "memory_limit_bytes": 4 * 1024**3,
        "worker_sha256": sha(WORK / "tools/phase00_smoke.py")}
    write(out / "request.json", request)
    started = time.monotonic()
    forced, peak = None, 0
    with (out / "process_stdout.txt").open("x", encoding="utf-8") as stdout, (out / "process_stderr.txt").open("x", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=environment(), stdout=stdout, stderr=stderr)
        kernel, handle = memory_handle(process.pid)
        handles={process.pid:handle}
        try:
            while process.poll() is None:
                for pid in process_family(process.pid):
                    if pid not in handles:
                        try:
                            _,handles[pid]=memory_handle(pid)
                        except OSError:
                            # A process may exit between enumeration and opening.
                            continue
                sampled=[memory_peak(h) for h in handles.values()]
                peak=max(peak,sum(v for v in sampled if v is not None))
                if time.monotonic() - started > timeout:
                    forced = "timeout"
                elif peak > request["memory_limit_bytes"]:
                    forced = "out_of_memory"
                if forced:
                    # The venv redirector may launch the real interpreter as a child.
                    # Terminate only handles belonging to this owned process family.
                    for pid,h in sorted(handles.items(),key=lambda pair:pair[0]==process.pid):
                        kernel.TerminateProcess(h,1)
                    process.wait()
                    break
                time.sleep(0.2)
            sampled=[memory_peak(h) for h in handles.values()]
            peak=max(peak,sum(v for v in sampled if v is not None))
        finally:
            for h in handles.values():
                kernel.CloseHandle(h)
    raw_path = out / "worker/result.json"
    raw = read(raw_path) if raw_path.exists() else {}
    status = forced or raw.get("status", "error")
    if status == "unsupported_declared_register":
        status = "unsupported"
    if raw and raw.get("normalized_sha256") != job["expected_normalized_sha256"]:
        status = "invalid"
        raw["campaign_contract_error"] = "Normalized input hash differs from frozen preflight"
    row = {**request, "ended_utc": now(), "status": status,
        "diagnostic_status": raw.get("status"), "process_exit_code": process.returncode,
        "process_wall_seconds": time.monotonic() - started, "peak_working_set_bytes": peak,
        "monitored_process_ids": sorted(handles),
        "memory_measurement": "maximum observed sum of individual process-family peak working sets; includes venv redirector and real interpreter",
        "result_path": raw_path.relative_to(WORK).as_posix() if raw_path.exists() else None,
        "stage_at_end": read(out / "worker/stage.json") if (out / "worker/stage.json").exists() else None,
        "worker_result": raw}
    write(out / "attempt_record.json", row)
    return row


def summarize(study):
    records = [read(p) for p in sorted((study / "attempts").glob("*/attempt_*/attempt_record.json"))]
    counts = {}
    rows = []
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        j, data = r["job"], r["worker_result"]
        parsed = data.get("legacy_counts", {})
        native = data.get("native_metrics", {})
        score = data.get("shared_legacy_score", {}) if j["algorithm"] == "rft" else data.get("native_N_shared_score", {})
        rows.append({"job_id": j["id"], "attempt": r["attempt"], "family": j["family"], "circuit": j["case"],
            "grid": j["grid"], "algorithm": j["algorithm"], "variant": j["variant"], "register_policy": j["register_policy"],
            "repetition": j["repetition"], "seed": j["seed"], "status": r["status"], "diagnostic_status": r["diagnostic_status"],
            "declared_N": data.get("input_declared_qubits"), "planner_N": native.get("native_num_qubits", data.get("num_qubits")),
            "CZ": data.get("num_cz"), "gate_cycles": parsed.get("Num Gate Cycles"), "movement_batches": parsed.get("Num Movement Ops"),
            "atom_moves": parsed.get("Num Moves"), "batch_max_distance_um": parsed.get("Total Move Distance"),
            "native_fidelity": score.get("Fidelity (DasAtom Model)"), "legacy_runtime_us": score.get("Total_T (us)"),
            "native_compile_seconds": native.get("Elapsed Time (s)", native.get("adapter_pipeline_seconds")),
            "offline_layout_seconds": data.get("offline_layout_seconds"), "preprocessing_seconds": data.get("preprocessing_seconds"),
            "process_wall_seconds": r["process_wall_seconds"], "peak_working_set_bytes": r["peak_working_set_bytes"],
            "timeout_seconds": r["timeout_seconds"], "trace_sha256": data.get("trace_sha256"),
            "planner_input_sha256": data.get("planner_input_sha256"), "raw_record": r.get("result_path")})
    if rows:
        path = study / "measurements.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = {"updated_utc": now(), "attempts": len(records), "statuses": counts,
        "planned_jobs": len(read(study / "plan.json")["jobs"]), "note": "No censored/invalid/unsupported outcome is treated as zero-time success"}
    write(study / "summary.json", summary)
    return summary


def run(study, args):
    import msvcrt
    progress_path = study / "progress.json"
    if progress_path.exists():
        progress = read(progress_path)
        if progress.get("state") == "stopped_by_user" and progress.get("replacement_plan"):
            raise SystemExit("This historical campaign was stopped by the user. Use tools/run_paper_focus.py with configs/studies/paper_focus_v2.json; do not resume the 726-job plan.")
    lock = (study / "controller.lock").open("a+b")
    lock.seek(0)
    if lock.read(1) == b"":
        lock.write(b"0")
        lock.flush()
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    config = read(study / "plan.json")
    completed, censored = set(), set()
    for p in (study / "attempts").glob("*/attempt_*/attempt_record.json"):
        r = read(p)
        completed.add(r["job"]["id"])
        if r["status"] in ["timeout", "out_of_memory"]:
            j = r["job"]
            censored.add((j["algorithm"], j["family"], j["case"], j["grid"], j["variant"], j["register_policy"]))
    launched, omitted = 0, []
    try:
        for job in config["jobs"]:
            if job["id"] in completed:
                continue
            if args.algorithm and job["algorithm"] != args.algorithm:
                continue
            if args.case and job["case"] not in args.case:
                continue
            if args.grid and job["grid"] not in args.grid:
                continue
            if args.primary_only and job["priority"] != 0:
                continue
            signature = (job["algorithm"], job["family"], job["case"], job["grid"], job["variant"], job["register_policy"])
            if signature in censored:
                omitted.append({"job_id": job["id"], "reason": "Earlier attempt censored at same cap; slow retry queue retained"})
                continue
            write(study / "progress.json", {"controller_pid": os.getpid(), "state": "running", "job": job, "launched_this_session": launched, "updated_utc": now()})
            folders = list((study / "attempts" / job["id"]).glob("attempt_*"))
            row = execute(study, job, args.timeout or config["initial_timeout_seconds"], len(folders) + 1)
            completed.add(job["id"])
            if row["status"] in ["timeout", "out_of_memory"]:
                censored.add(signature)
            launched += 1
            summary = summarize(study)
            print(json.dumps({"job": job["id"], "status": row["status"], "attempts": summary["attempts"], "seconds": round(row["process_wall_seconds"], 2)}), flush=True)
            if args.limit and launched >= args.limit:
                break
        write(study / "omitted_repetitions.json", omitted)
        write(study / "progress.json", {"controller_pid": os.getpid(), "state": "session_finished", "launched_this_session": launched, "updated_utc": now()})
    finally:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        lock.close()
    print(json.dumps(summarize(study)), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["plan", "run", "summarize"])
    p.add_argument("--study", default=str(DEFAULT_STUDY))
    p.add_argument("--timeout", type=float)
    p.add_argument("--limit", type=int)
    p.add_argument("--algorithm", choices=["rft", "dasatom"])
    p.add_argument("--case", action="append")
    p.add_argument("--grid", type=int, action="append")
    p.add_argument("--primary-only", action="store_true")
    args = p.parse_args()
    study = Path(args.study).resolve()
    if not study.is_relative_to(WORK):
        raise SystemExit("Study must be under btp_work")
    study.mkdir(parents=True, exist_ok=True)
    if args.mode == "plan":
        plan(study)
    elif args.mode == "run":
        run(study, args)
    else:
        print(json.dumps(summarize(study), indent=2))


if __name__ == "__main__":
    main()
