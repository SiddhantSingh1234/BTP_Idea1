"""Export Phase 00 source-backed configurations and unavailable-input inventory.

This is documentation metadata, not an executable compiler configuration loader.
Null versions/hashes explicitly denote evidence that could not be recovered.
"""
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]


def write(relative, obj):
    path = WORK / relative
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main():
    repos = json.loads((WORK / "source_review/repository_snapshot.json").read_text(encoding="utf-8-sig"))
    rft, das = repos
    rt, dt = ({e["path"]: e for e in repo["tree"] if e["type"] == "blob"} for repo in repos)
    audit = json.loads((WORK / "runs/phase_00/isolated_final_01.json").read_text())
    common = {"schema": "phase00.baseline-spec.v1", "execution_ready": False,
              "new_research_heuristics_enabled": False, "environment_lock": None}
    profile = dict(T2_us=1.5e6, f_cz=0.995, f_trans=1.0, diagnostic_f_trans=0.999,
                   t_cz_us=0.2, t_trans_us=20, speed_um_per_us=0.55, spacing_um=3.0,
                   transfers_per_nonempty_movement_batch=4,
                   source="snapshot converter FidelityParams and _compute_fidelity_from_counts; not all constants established by RFT manuscript")
    snapshot = dict(common, id="rft_snapshot", revision=rft["commit"], repository=rft["url"],
        source_state="six-file excerpt only; full source recovery blocked",
        variant_key="7_dynamic_slot_01q_move", options=audit["ladder_options"]["7_dynamic_slot_01q_move"],
        geometry={"rows": 11, "columns": 11, "r_int_grid": 2, "r_blk_grid": 4,
                  "selection": "snapshot smoke control, not proof of paper options"},
        layout={"sampler": "sample_max_parallel", "trials": 20, "hardcoded_global_seed": 42, "frozen_slots": None},
        normalization={"basis_gates": ["cz", "h", "s", "t", "rx", "ry", "rz"], "optimization_level": 0,
                       "seed_transpiler": None, "one_qubit_gates": "removed", "two_qubit_operations": "all rewritten to CZ by upstream predicate",
                       "scope": "route-only CZ skeleton; not full input unitary"},
        legacy_profile=profile, seed_policy={"private_options_rng": 42, "MIS_seed_argument": None,
            "historical_runner_warmup": "one call on first sorted QASM using first selected variant",
            "hash_seed_for_new_controlled_runs": "0", "threads_for_new_controlled_runs": 1,
            "global_random_state": "consumed by offline sampler, warmup, then MIS; capture before/after"},
        timed_region="after temp QASM write; QASM reload + DAG + busiest mapping + planner including RFT/router; before unlink and scoring",
        smoke_cases=["qft_5", "4mod5-v1_22"], smoke_status="blocked_dependency")
    write("configs/baselines/rft_snapshot.json", snapshot)
    write("configs/baselines/rft_paper.json", dict(common, id="rft_paper", revision=None, options=None,
        status="paper_revision_unresolved", manuscript_python="3.13.2", available_interpreter="3.12.10 (audit only)",
        evidenced_constants={"T2_us": 1.5e6, "f_cz": 0.995, "f_trans": 1.0, "restriction_to_interaction_ratio": 2},
        figure4_grids=[11, 20, 35], tableII_grids=[11, 35], exact_sampled_QFT_sizes=None,
        candidate_existing_variant="8_optimized_eviction aligns more closely with Eq.6 but is not identified as paper implementation",
        missing_evidence=["author-supported commit/tag", "fully resolved options", "exact normalized inputs",
                          "original layout and seeds", "package lock", "raw figure/table records and timing provenance"]))
    write("configs/baselines/rft_corrected.json", dict(common, id="rft_corrected", revision=None,
        status="not_implemented", parent_revision=rft["commit"], patches_applied=[],
        proposed_correctness_repairs=["materialize saved orientation minimizing full per-slot matrix cost",
            "reject incomplete/capacity-error schedules instead of scoring error logs as successful output"],
        heuristics="none authorized in Phase00"))
    write("configs/baselines/dasatom_snapshot.json", dict(common, id="dasatom_standalone_snapshot",
        revision=das["commit"], repository=das["url"], source_state="tree metadata only",
        options=None, import_provider="standalone upstream, distinct from RFT embedded DasAtom",
        geometry_for_matched_smoke={"grid": [11, 11], "r_int_grid": 2, "r_restr_grid": 4},
        actual_grid_and_extensions=None, normalization_verified=False, legacy_profile=profile,
        note="Matched geometry is a requested control. Standalone behavior and API compatibility remain untested."))
    env = json.loads((WORK / "runs/phase_00/environment.json").read_text())
    write("configs/baselines/dependency_status.json", {"status": "unresolved_not_a_lockfile",
        "manuscript_interpreter": "3.13.2", "installed_audit_interpreter": "3.12.10",
        "compatible_compiler_interpreter": None, "tested_dependency_lock": None,
        "observed_packages": env["packages"],
        "plan": "Recover complete sources, install a compatible interpreter under btp_work, resolve packages, run both compilers, then freeze exact versions and wheel hashes. No untested version choices are presented as a lock."})
    table_names = ["4mod5-v1_22", "adr4_197", "alu-v0_27", "bv_n16", "cm152a_212", "dc1_220",
                   "ising_model_16", "misex1_241", "qft_16", "qv_n16_d5", "rd53_251", "rd73_252",
                   "square_root_7", "sym6_145", "z4_268"]
    def identity(path, family, claim):
        d = dt[path]
        r = rt.get("dasatom/DasAtom-main/" + path)
        return {"path": path, "family": family, "published_membership": claim,
                "upstream_revision": das["commit"], "standalone_git_blob_sha1": d["sha"],
                "standalone_bytes": d.get("size"), "embedded_revision": rft["commit"],
                "embedded_git_blob_sha1": r["sha"] if r else None,
                "same_between_snapshots": bool(r and r["sha"] == d["sha"]),
                "content_recovered": False, "raw_sha256": None, "normalized_sha256": None,
                "Qiskit_version": None, "CZ_count": None, "layers": None,
                "source": "saved repository_snapshot.json tree; filenames are not paper-version evidence"}
    manifest = {"schema": "phase00.reproduction-inputs.v1", "status": "inventory_only_inputs_unavailable",
        "tableII": [identity(f"Data/Q_Tetris/{n}.qasm", "QTetris", "TableII p6; source-byte version unresolved") for n in table_names],
        "figure4_candidates": [identity(f"Data/qiskit-bench/qft/qft_{n}.qasm", "QFT", "candidate only; sampled sizes unresolved") for n in range(5, 61)],
        "figure4_sampled_sizes": None, "figure4_range": [5, 60], "figure4_grids": [11, 20, 35],
        "tableII_grids": [11, 35], "small_smokes": ["Data/qiskit-bench/qft/qft_5.qasm", "Data/Q_Tetris/4mod5-v1_22.qasm"],
        "qft_source_conventions": {"final_swaps": None, "approximation_degree": None, "synthesis_version": None},
        "synthetic_fixture": {"path": "benchmarks/phase_00/four_qubit_hand_trace.qasm",
            "sha256": hashlib.sha256((WORK / "benchmarks/phase_00/four_qubit_hand_trace.qasm").read_bytes()).hexdigest(),
            "identity": "new analytic fixture, not QFT or TableII, not a published target"}}
    write("configs/benchmarks/reproduction_manifest.json", manifest)
    print("Created 4 baseline specifications, dependency-status metadata, and a 15 + 56 candidate input inventory; no runnable lock or manuscript identity claimed.")


if __name__ == "__main__":
    main()
