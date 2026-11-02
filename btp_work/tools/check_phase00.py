"""Check retained evidence and report every Phase 00 gate without claiming success.

Exit 0: all recorded gates pass; 1: artifact inconsistency; 2: artifacts consistent
but mandatory phase gates remain open. This does not replace compiler smokes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

WORK = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((WORK / relative).read_text(encoding="utf-8-sig"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, help="New path relative to btp_work")
    args = p.parse_args()
    target = (WORK / args.output).resolve()
    if not target.is_relative_to(WORK) or target.exists():
        raise SystemExit("Use a new output path under btp_work")
    issues = []
    required = ["reports/phase_00/environment.md", "reports/phase_00/implementation_map.md",
        "reports/phase_00/baseline_spec.md", "reports/phase_00/discrepancy_ledger.md", "handoffs/phase_00.md",
        "configs/baselines/rft_snapshot.json", "configs/baselines/rft_paper.json", "configs/baselines/rft_corrected.json",
        "configs/baselines/dasatom_snapshot.json", "configs/baselines/dependency_status.json",
        "configs/benchmarks/reproduction_manifest.json", "runs/phase_00/source_recovery_attempt_03.json",
        "runs/phase_00/compiler_retry_02/attempts.json"]
    for name in required:
        if not (WORK / name).is_file():
            issues.append(f"Missing artifact: {name}")
    inv = read("runs/phase_00/inventory.json")
    for entry in inv["local_excerpt_files"]:
        path = WORK / "source_review/upstream_excerpt/NAQC_Compiler" / entry["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entry["sha256"] or not entry["matches_pinned_blob"]:
            issues.append(f"Retained source mismatch: {entry['path']}")
    for entry in inv["original_pdf_integrity"]:
        if hashlib.sha256((WORK.parent / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
            issues.append(f"Original PDF changed: {entry['path']}")
    first, second = (WORK / f"runs/phase_00/isolated_final_0{i}.json" for i in [1, 2])
    a, b = read(first.relative_to(WORK)), read(second.relative_to(WORK))
    if first.read_bytes() != second.read_bytes() or not a["all_passed"] or len(a["checks"]) != 27:
        issues.append("Isolated repeat records do not match their documented 27-check result")
    fixture = WORK / "benchmarks/phase_00/four_qubit_hand_trace.txt"
    if hashlib.sha256(fixture.read_bytes()).hexdigest() != a["fixture_sha256"]:
        issues.append("Worked fixture differs from final tested bytes")
    manifest = read("configs/benchmarks/reproduction_manifest.json")
    if len(manifest["tableII"]) != 15 or len(manifest["figure4_candidates"]) != 56:
        issues.append("Target inventory count differs from specification")
    snapshot = read("configs/baselines/rft_snapshot.json")
    if snapshot["options"] != a["ladder_options"]["7_dynamic_slot_01q_move"]:
        issues.append("Snapshot options differ from exact retained ladder7")
    paper, corrected = read("configs/baselines/rft_paper.json"), read("configs/baselines/rft_corrected.json")
    if paper["revision"] is not None or paper["status"] != "paper_revision_unresolved" or corrected["patches_applied"]:
        issues.append("Recorded baseline distinction changed; rerun phase review")
    for script in (WORK / "tools").glob("*.py"):
        ast.parse(script.read_text(encoding="utf-8-sig"), filename=str(script))
    brief = (WORK / "plan/phases/00_IMPLEMENTATION_AUDIT.md").read_text(encoding="utf-8")
    criteria = re.findall(r"^- \[ \] (.+)$", brief, flags=re.M)
    runtime = read("runs/phase_00/runtime_summary.json") if (WORK / "runs/phase_00/runtime_summary.json").exists() else None
    runtime_pass = False
    if runtime:
        cases = runtime["smoke_cases"]
        runtime_pass = cases["rft_qft5"]["status"] == cases["dasatom_qft5"]["status"] == "ok"
        for case in cases.values():
            left, right = [read(n) for n in case["records"]]
            if not all(left[k] == right[k] for k in ["trace_sha256", "normalized_sha256", "legacy_counts", "shared_legacy_score"]):
                issues.append("Compiler repeat evidence differs")
        trees = read("runs/phase_00/verified_source_trees.json")
        for tree in trees:
            for entry in tree["files"]:
                actual = hashlib.sha256((WORK / tree["path"] / entry["path"]).read_bytes()).hexdigest()
                if actual != entry["sha256"]:
                    issues.append(f"Pinned working-tree file changed: {entry['path']}")
        if not read("runs/phase_00/compiled_fixture_01/trace.json")["forced_eviction_count"]:
            issues.append("Missing compiled eviction")
    verdicts = (["pass_tested_smokes", "pass_source_and_compiled_trace", "pass", "pass", "pass_documented_native_register_limit", "pass_tested_smoke_repeatability"]
                if runtime_pass else ["blocked_dependency", "pass_source_audit", "pass", "pass", "partial_unresolved", "unresolved_full_compiler"])
    if len(criteria) != len(verdicts):
        issues.append("Phase criteria changed; reassess all gates")
    gates = [{"criterion": c, "verdict": v} for c, v in zip(criteria, verdicts)]
    accepted = False
    scope_path = WORK / "configs/baselines/accepted_scope.json"
    if scope_path.exists():
        scope = read("configs/baselines/accepted_scope.json")
        heads = read(scope["head_evidence"])
        accepted = (scope["status"] == "adopted" and scope["scope"] == "latest_public_snapshot"
            and scope["rft_commit"] == snapshot["revision"]
            and scope["dasatom_commit"] == read("configs/baselines/dasatom_snapshot.json")["revision"]
            and {h["commit"] for h in heads if h["status"] == "ok"} == {scope["rft_commit"], scope["dasatom_commit"]}
            and (WORK / scope["decision"]).is_file())
        if not accepted:
            issues.append("Accepted latest-source scope/head evidence does not match frozen controls")
    gates.append({"criterion": "Exact manuscript implementation/version evidence",
                  "verdict": "unresolved_historical_limitation_outside_user_selected_snapshot_gate" if accepted else "paper_revision_unresolved"})
    complete = runtime_pass and accepted and not issues
    result = {"artifact_checks_ok": not issues, "issues": issues, "mandatory_gates": gates,
        "phase_status": "complete" if complete else "needs_revision" if runtime_pass else "blocked_dependency", "phase_complete": complete,
        "completion_scope": "user_selected_latest_public_snapshot" if accepted else "original_exact_paper_gate",
        "isolated_checks_per_run": len(a["checks"]), "isolated_repeat_byte_equal": first.read_bytes() == second.read_bytes(),
        "full_compiler_smoke_passed": runtime_pass, "paper_revision_resolved": False,
        "snapshot_mandatory_criteria_passed": runtime_pass and not issues,
        "scope": "Evidence/source consistency and gate accounting; smoke replay does not prove continuous physical validity"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if issues else 0 if complete else 2)


if __name__ == "__main__":
    main()
