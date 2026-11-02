"""Freeze tested runtime evidence/configuration; preserve all earlier raw attempts."""
import difflib
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys

WORK = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((WORK / path).read_text(encoding="utf-8-sig"))


def write(path, obj):
    target = WORK / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = WORK / "runs/phase_00/runtime_summary.json"
    if output.exists():
        raise SystemExit("Runtime evidence already frozen; do not overwrite")
    repos = read("source_review/repository_snapshot.json")
    verified = []
    for repo in repos:
        root = WORK / "vendor" / (repo["repository"].split("/")[1] + "-" + repo["commit"])
        entries = []
        for item in repo["tree"]:
            if item["type"] != "blob":
                continue
            payload = (root / item["path"]).read_bytes()
            blob = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
            assert blob == item["sha"], item["path"]
            entries.append({"path": item["path"], "git_blob_sha1": blob,
                            "sha256": hashlib.sha256(payload).hexdigest()})
        record = {"repository": repo["repository"], "revision": repo["commit"],
                  "path": root.relative_to(WORK).as_posix(), "verified_blobs": len(entries), "files": entries}
        verified.append(record)
    write("runs/phase_00/verified_source_trees.json", verified)
    archive = WORK / "reports/phase_00/configs_before_recovery"
    archive.mkdir(parents=True)
    for path in (WORK / "configs/baselines").glob("*.json"):
        shutil.copyfile(path, archive / path.name)
    shutil.copyfile(WORK / "configs/benchmarks/reproduction_manifest.json", archive / "reproduction_manifest.json")

    lockdir = WORK / "configs/environment"
    lockdir.mkdir(parents=True, exist_ok=True)
    setup = WORK / "runs/phase_00/setup_20261027_183111_096"
    shutil.copyfile(setup / "requirements.candidate.lock", lockdir / "requirements-py313-win64.lock")
    shutil.copyfile(setup / "requirements.candidate.txt", lockdir / "requirements-py313-win64.txt")
    environment = {"python": sys.version, "executable": sys.executable,
        "distribution": "uv-managed Astral python-build-standalone CPython 3.13.2; same version as manuscript, binary build provenance not established for manuscript",
        "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "lock_path": "configs/environment/requirements-py313-win64.lock",
        "lock_sha256": sha(lockdir / "requirements-py313-win64.lock"),
        "setup_record": "runs/phase_00/setup_20261027_183111_096/setup_status.json",
        "threads": 1, "hash_seed": "0", "package_consistency": "uv pip check passed",
        "clean_lock_reinstallation_tested": False}
    write("configs/environment/environment.json", environment)
    smoke = {}
    for algorithm in ["rft", "dasatom"]:
        for case in ["qft5", "tableII"]:
            indices = ["01", "02"] if (algorithm, case) != ("dasatom", "tableII") else ["03", "04"]
            names = [f"runs/phase_00/smoke_{algorithm}_{case}_{i}/result.json" for i in indices]
            a, b = [read(n) for n in names]
            stable = all(a[k] == b[k] for k in ["trace_sha256", "normalized_sha256", "legacy_counts", "shared_legacy_score"])
            assert stable, (algorithm, case)
            smoke[f"{algorithm}_{case}"] = {"records": names, "status": a["status"],
                "repeat_trace_and_metrics_identical": stable, "trace_sha256": a["trace_sha256"],
                "input_sha256": a["input_sha256"], "normalized_sha256": a["normalized_sha256"],
                "num_qubits": a["num_qubits"], "num_cz": a["num_cz"], "counts": a["legacy_counts"],
                "score": a["shared_legacy_score"], "boundary_replay": a["boundary_replay"],
                "native_register_policy": a.get("register_policy"),
                "native_score": a.get("native_metrics", {}).get("native_score")}
    assert smoke["rft_qft5"]["status"] == smoke["dasatom_qft5"]["status"] == "ok"
    fixture = read("runs/phase_00/compiled_fixture_01/trace.json")
    assert fixture["forced_eviction_count"] == 2 and fixture["boundary_replay"]["valid_within_coverage"]
    history = read("runs/phase_00/history_01/summary.json")
    heads = read("runs/phase_00/history_01/rft_current_head.json")
    assert heads[0]["sha"] == repos[0]["commit"]
    for name in ["rft_snapshot", "dasatom_snapshot"]:
        cfg = read(f"configs/baselines/{name}.json")
        cfg.update(execution_ready=True, environment_lock=environment["lock_path"],
                   source_state="complete pinned archive working tree; all Git blobs verified",
                   smoke_evidence="runs/phase_00/runtime_summary.json")
        if name == "rft_snapshot":
            observed = read("runs/phase_00/smoke_rft_qft5_01/result.json")
            cfg["smoke_status"] = "passed_qft5_and_tableII"
            cfg["layout"]["frozen_slots"] = observed["layout"]
        else:
            cfg["normalization_verified"] = True
            cfg["options"] = {"routing_strategy": "maximalis", "global_seed": 42, "router_MIS_seed": 0,
                "geometry": [11, 11, 2, 4], "cache": False, "native_N_policy": "max(two-qubit operand)+1"}
            cfg["actual_grid_and_extensions"] = {"qft5": [11, []], "tableII": [11, []]}
            cfg["limitations"] = ["Table II 4mod5 declares 16 qubits, native DasAtom keeps 5; unmatched full-register schedule unsupported"]
        write(f"configs/baselines/{name}.json", cfg)
    write("configs/baselines/dependency_status.json", {"status": "installed_smoke_tested",
        "manuscript_interpreter": "3.13.2", "research_interpreter": "3.13.2",
        "environment": "configs/environment/environment.json", "tested_dependency_lock": environment["lock_path"]})
    paper = read("configs/baselines/rft_paper.json")
    paper["available_interpreter"] = "3.13.2 research venv; 3.12.10 retained extraction runtime"
    paper["history_audit"] = "runs/phase_00/history_01/summary.json"
    write("configs/baselines/rft_paper.json", paper)
    manifest = read("configs/benchmarks/reproduction_manifest.json")
    manifest["status"] = "raw_sources_recovered_smoke_normalization_frozen_paper_input_versions_unresolved"
    manifest["selected_common_input_source"] = repos[1]["commit"]
    manifest["snapshot_plot_filter"] = list(range(5, 61, 5))
    manifest["snapshot_plot_filter_evidence"] = "pinned src/qft_grid_comparison_plot_final.py lines 107-115; not proof of original plotted data"
    for family in ["tableII", "figure4_candidates"]:
        for entry in manifest[family]:
            path = WORK / verified[1]["path"] / entry["path"]
            entry.update(content_recovered=True, raw_sha256=sha(path), Qiskit_version="1.3.1")
            for case, match in [("qft5", "Data/qiskit-bench/qft/qft_5.qasm"), ("tableII", "Data/Q_Tetris/4mod5-v1_22.qasm")]:
                if entry["path"] == match:
                    data = read(f"runs/phase_00/smoke_rft_{case}_01/result.json")
                    entry.update(normalized_sha256=data["normalized_sha256"], CZ_count=data["num_cz"], layers=data["logical_layers"])
    write("configs/benchmarks/reproduction_manifest.json", manifest)
    root_a = WORK / verified[1]["path"]
    root_b = WORK / verified[0]["path"] / "dasatom/DasAtom-main"
    diff = "\n".join("".join(difflib.unified_diff((root_a/n).read_text(encoding="utf-8-sig").splitlines(True),
        (root_b/n).read_text(encoding="utf-8-sig").splitlines(True), fromfile="standalone/"+n, tofile="embedded/"+n))
        for n in ["DasAtom_fun.py", "Enola/route.py"])
    (WORK / "reports/phase_00/embedded_dasatom.diff").write_text(diff, encoding="utf-8")
    summary = {"date": "2026-10-28", "source_trees_verified": True, "source_blobs": [v["verified_blobs"] for v in verified],
        "research_python": "3.13.2", "dependency_lock": environment["lock_path"], "smoke_cases": smoke,
        "compiled_fixture": {"record": "runs/phase_00/compiled_fixture_01/trace.json", "forced_evictions": 2,
            "counts": fixture["counts"], "score": fixture["legacy_score"]},
        "history": {"records": "runs/phase_00/history_01/summary.json", "rft_commits": history["rft_commit_count_returned"],
            "current_main_matches_pin": True, "tags": read("runs/phase_00/history_01/rft_tags.json"),
            "embedded_helper_upstream_exact_match_found": False},
        "snapshot_audit_status": "complete_with_documented_register_and_validation_limits",
        "phase_status": "needs_revision", "phase_complete": False, "paper_revision_unresolved": True,
        "new_research_heuristics": False,
        "limitations": ["paper revision/options/raw-result provenance unavailable", "DasAtom trailing inactive-qubit omission",
            "no continuous physical validity claim", "dependency lock rebuild in a second clean environment not tested"]}
    write("runs/phase_00/runtime_summary.json", summary)
    print(json.dumps({"verified_source_blobs": summary["source_blobs"], "repeatability": "four pairs match exactly",
        "smokes": {k:v["status"] for k,v in smoke.items()}, "phase_status": summary["phase_status"],
        "paper_revision_unresolved": True}, indent=2))


if __name__ == "__main__":
    main()
