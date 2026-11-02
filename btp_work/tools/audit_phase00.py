"""Standard-library audit of retained upstream code, NOT a compiler replacement.

Executes selected original AST nodes without importing optional compiler packages.
No numpy, scipy, networkx, Qiskit, or DasAtom implementation is substituted.
The full compiler smoke gate is reported separately and cannot pass this audit.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import ctypes
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import importlib.metadata
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import shutil
import sys
import types
from typing import Any, Optional

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parent
EXCERPT = WORK / "source_review/upstream_excerpt/NAQC_Compiler"
RFT_REV = "3d1f09233c2acd357fd9fbfad1b5300a921d301a"
DAS_REV = "73a6bdf0fd200b2733745211eaf2e0c1e17f496a"


def digest(data):
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()}


def source_tree(name):
    path = EXCERPT / "src" / name
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path)), path


def load_nodes(filename, names, namespace):
    tree, path = source_tree(filename)
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, str(path), "exec"), namespace)


def inventory():
    repos = json.loads((WORK / "source_review/repository_snapshot.json").read_text(encoding="utf-8-sig"))
    rft, das = repos
    rt = {x["path"]: x for x in rft["tree"] if x["type"] == "blob"}
    dt = {x["path"]: x for x in das["tree"] if x["type"] == "blob"}
    local = []
    for path in sorted(EXCERPT.rglob("*")):
        if path.is_file():
            relative = path.relative_to(EXCERPT).as_posix()
            hashes = digest(path.read_bytes())
            local.append({"path": relative, "bytes": path.stat().st_size, **hashes,
                          "matches_pinned_blob": hashes["git_blob_sha1"] == rt[relative]["sha"]})
    prefix = "dasatom/DasAtom-main/"
    embedded = []
    for path, entry in rt.items():
        if path.startswith(prefix):
            other = dt.get(path[len(prefix):])
            embedded.append({"embedded_path": path, "embedded_git_blob_sha1": entry["sha"],
                             "standalone_git_blob_sha1": other["sha"] if other else None,
                             "same_blob": bool(other and entry["sha"] == other["sha"])})
    maps = {}
    for filename in ("compiler_core.py", "benchmark_runner.py", "dasatom_instruction_converter.py"):
        tree, _ = source_tree(filename)
        maps[filename] = {n.name: {"line": n.lineno, "end_line": n.end_lineno}
                          for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    primary = json.loads((WORK / "source_review/manifest.json").read_text(encoding="utf-8"))
    papers = [{"path": p["source"], "sha256": p["sha256"],
               "unchanged": digest((ROOT / p["source"]).read_bytes())["sha256"] == p["sha256"]}
              for p in primary]
    instructions = [str(p) for p in [ROOT, *ROOT.parents] if (p / "AGENTS.md").exists()]
    instructions += [str(p) for p in WORK.rglob("AGENTS.md")]
    return {"scope": "Retained excerpt and saved Git tree metadata only; no checkout/history recovery",
            "rft_revision": RFT_REV, "dasatom_revision": DAS_REV,
            "local_excerpt_files": local, "embedded_comparison": embedded,
            "function_anchors": maps, "original_pdf_integrity": papers,
            "applicable_agents_files": instructions,
            "git_available_on_path": shutil.which("git"),
            "source_checkouts_recovered": (WORK / "runs/phase_00/verified_source_trees.json").exists(),
            "compiler_smoke_passed": (WORK / "runs/phase_00/runtime_summary.json").exists(),
            "runtime_evidence_if_present": "runs/phase_00/runtime_summary.json"}


def environment():
    packages = {}
    for name in ["qiskit", "numpy", "scipy", "networkx", "rustworkx", "pandas", "matplotlib",
                 "plotly", "openpyxl", "pip", "venv", "pypdf", "fontTools"]:
        present = importlib.util.find_spec(name) is not None
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = None
        packages[name] = {"import_available": present, "distribution_version": version}
    machine = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
               "processor": platform.processor(), "logical_cpus": os.cpu_count(),
               "packages": packages, "thread_environment": {n: os.environ.get(n) for n in
                   ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "PYTHONHASHSEED"]}}
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (x, ctypes.c_ulonglong) for x in ["total_physical", "available_physical", "total_pagefile",
                                                "available_pagefile", "total_virtual", "available_virtual", "extended"]]
        memory = MEMORYSTATUSEX()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            machine["ram_total_bytes"] = memory.total_physical
            machine["ram_available_bytes"] = memory.available_physical
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                machine["cpu_model"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError as e:
            machine["cpu_model_probe_error"] = str(e)
    try:
        machine["disk"] = shutil.disk_usage(WORK)._asdict()
    except OSError as e:
        machine["disk_probe_error"] = str(e)
    # Demonstrate the actual missing dependency without writing __pycache__ to upstream.
    sys.dont_write_bytecode = True
    try:
        ns = {"__name__": "phase00_import_probe", "__file__": str(EXCERPT / "src/compiler_core.py")}
        exec(compile((EXCERPT / "src/compiler_core.py").read_text(encoding="utf-8"), ns["__file__"], "exec"), ns)
        machine["rft_excerpt_import"] = {"status": "imported", "compiler_smoke": False}
    except Exception as e:
        machine["rft_excerpt_import"] = {"status": "error", "type": type(e).__name__, "message": str(e)}
    machine["dasatom_smoke"] = ({"status": "recorded", "evidence": "runs/phase_00/runtime_summary.json"}
        if (WORK / "runs/phase_00/runtime_summary.json").exists() else
        {"status": "blocked_dependency", "reason": "No tested full runtime evidence recorded"})
    return machine


def isolated_checks():
    # Names come from stdlib; no optional-package substitutes are provided.
    ns = {"__name__": "phase00_isolated_upstream", "bisect": bisect, "math": math, "random": random,
          "dataclass": dataclass, "Enum": Enum, "Optional": Optional, "Any": Any, "re": re}
    module = types.ModuleType(ns["__name__"])
    module.__dict__.update(ns)
    sys.modules[module.__name__] = module
    ns = module.__dict__
    load_nodes("compiler_core.py", ["AssignmentMode", "IdleParkingMode", "CandidateSlotsMode", "CompilerOptions",
        "euclid_dist", "_pick_idle_position", "build_right_filled_table", "find_busiest_pairs",
        "create_initial_mapping", "is_slot_compatible", "get_neighbors", "generate_hardware_instructions",
        "generate_safe_shuttle_instructions"], ns)
    load_nodes("dasatom_instruction_converter.py", ["FidelityParams", "_compute_fidelity_from_counts",
                                                  "analyze_converted_instructions"], ns)
    load_nodes("benchmark_runner.py", ["ladder_variants"], ns)
    checks = []
    def add(name, actual, expected, detail=None):
        assert actual == expected, (name, actual, expected)
        checks.append({"name": name, "passed": True, "actual": actual, "expected": expected, "detail": detail})
    schedule = [("T1", [(0, 1)]), ("T2", [(0, 2)]), ("T3", [(0, 1)])]
    table = ns["build_right_filled_table"](schedule, 4)
    add("rft_stores_multiple_partners_at_current_layer", table["T1"][0], [(1, 0), (2, 1)])
    add("rft_earliest_repeat_hides_later_same_partner", len([p for p, _ in table["T1"][0] if p == 1]), 1)
    add("rft_no_future_partner", table["T3"][2], [])
    def park(**changes):
        kwargs = dict(qubit=0, available_positions=[(1, 0), (4, 1)], current_qubit_positions={0: (0, 0)},
                      final_target_positions={1: (4, 0)}, center_of_mass=(0, 0), current_future_partners={0: [(1, 1)]},
                      options=ns["CompilerOptions"](), rng=random.Random(42), max_partner_dist=2, is_evicted=True)
        kwargs.update(changes)
        return ns["_pick_idle_position"](**kwargs)
    add("legacy_parking_sum_distance", park(), (1, 0))
    add("alternative_eviction_pure_partner", park(options=ns["CompilerOptions"](evicted_park_closest_to_partner=True)), (4, 1))
    add("eviction_cutoff_ignores_partner_at_delta3", park(current_future_partners={0: [(1, 3)]},
        options=ns["CompilerOptions"](evicted_park_closest_to_partner=True)), (1, 0))
    add("missing_anchor_ignores_known_partner", park(final_target_positions={},
        options=ns["CompilerOptions"](evicted_park_closest_to_partner=True)), (1, 0))
    add("no_future_fallback_uses_supplied_centroid", park(current_future_partners={}, center_of_mass=(4, 1)), (4, 1))
    # Execute the exact orientation-materialization statements from the real function.
    tree, path = source_tree("compiler_core.py")
    planner = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "generate_hardware_instructions")
    loop = next(n for n in ast.walk(planner) if isinstance(n, ast.For) and isinstance(n.iter, ast.Call)
                and isinstance(n.iter.func, ast.Name) and n.iter.func.id == "zip"
                and ast.unparse(n.iter) == "zip(row_ind, col_ind)")
    orientation_code = compile(ast.Module(body=loop.body, type_ignores=[]), str(path), "exec")
    orientation = None
    points = list(itertools.product(range(4), repeat=2))
    for p1, p2, s1, s2 in itertools.permutations(points, 4):
        if math.dist(s1, s2) > 2 or math.dist(p1, s1) >= math.dist(p1, s2):
            continue
        a = math.dist(p1, s1) + math.dist(p2, s2)
        b = math.dist(p1, s2) + math.dist(p2, s1)
        if b + 1e-8 < a:
            local = dict(ns, movers=[(0, 1)], candidate_slots=[(s1, s2)], current_qubit_positions={0: p1, 1: p2},
                         R=4, C=4, r=0, c=0, active_qubit_targets={})
            exec(orientation_code, local)
            add("orientation_materialization_increases_matrix_entry", local["active_qubit_targets"], {0: s1, 1: s2})
            orientation = {"positions": {0: p1, 1: p2}, "slot": [s1, s2], "matrix_cost": b,
                           "materialized_cost": a, "materialization_ast_lines": [loop.lineno, loop.end_lineno]}
            break
    assert orientation
    # Historical parser and scorer: one batch, varying populations, one gate cycle.
    stats = []
    for population in [1, 3]:
        log = "[SHUTTLING] Batch 1\n" + "\n".join(
            f"  SHUTTLE qubit {q} from ({q}, 0) to ({q}, 1)" for q in range(population))
        log += "\n[EXECUTE T1]\n  CZ q[0], q[1] (at locations (0, 0), (0, 1))"
        parsed = ns["analyze_converted_instructions"](log, d_atom=3.0)
        scored = ns["_compute_fidelity_from_counts"](num_qubits=4, num_cz_gates=1,
            num_gate_cycles=parsed["Num Gate Cycles"], num_movement_ops=parsed["Num Movement Ops"],
            total_move_distance=parsed["Total Move Distance"], num_moves=parsed["Num Moves"],
            params_optimistic=ns["FidelityParams"](), params_realistic=ns["FidelityParams"](f_trans=0.999))
        add(f"batch_population_{population}_transfer_alias", scored["Num Transferred Qubits"], 4)
        assert math.isclose(scored["Total_T (us)"], 80 + 3 / 0.55 + 0.2, abs_tol=1e-12)
        assert math.isclose(scored["Fidelity (DasAtom Model)"], 0.995 * math.exp(-(4 * (80 + 3 / 0.55 + 0.2) - 0.2) / 1.5e6), abs_tol=1e-14)
        stats.append({"population": population, "parsed": parsed, "legacy_score": scored})
    add("increasing_atom_population_does_not_change_legacy_transfer_cost",
        stats[0]["legacy_score"]["Fidelity (Realistic)"], stats[1]["legacy_score"]["Fidelity (Realistic)"])
    # These exact paths never touch numpy or networkx; they do not test full planning.
    args = dict(canonical_mapping={}, busiest_pairs=[], num_qubits=4, R=2, C=2, physical_layout=[], r_blk=2, r_int=1)
    add("inactive_empty_schedule_has_no_initialization", ns["generate_hardware_instructions"](schedule=[], **args), [])
    skip = ns["generate_hardware_instructions"](schedule=[("T1", [])], **args)
    add("inactive_layer_is_skip_only", "Skipping." in skip[0], True)
    try:
        ns["generate_hardware_instructions"](schedule=[("T1", [(0, 1)])], **args)
        raise AssertionError("Expected zero-slot initialization failure")
    except UnboundLocalError as e:
        add("zero_slot_initialization_references_unbound_centroid", "center_of_mass" in str(e), True, str(e))
    cycle = ns["generate_safe_shuttle_instructions"]({0: (0, 0), 1: (0, 1)}, {0: (0, 1), 1: (0, 0)}, 1, 2)
    add("full_grid_swap_returns_error_log_not_exception", cycle, ["  ERROR: No free temporary spot to break movement cycle!"])
    # Source facts, tested as AST observations, not claims about absent upstream versions.
    names_loaded = {n.id for n in ast.walk(planner) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    add("canonical_mapping_and_busiest_pairs_unused", sorted({"canonical_mapping", "busiest_pairs"} & names_loaded), [])
    add("no_GridCapacityError_raise_in_planner", any(isinstance(n, ast.Raise) for n in ast.walk(planner)), False)
    router = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "generate_safe_shuttle_instructions")
    mis = [n for n in ast.walk(router) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "maximal_independent_set"]
    add("router_mis_omits_explicit_seed", len(mis) == 1 and not any(k.arg == "seed" for k in mis[0].keywords), True)
    add("ladder_variant_count", len(ns["ladder_variants"]()), 8)
    add("snapshot_default_is_ladder7", asdict(ns["CompilerOptions"]()) | {"variant_name": "7_dynamic_slot_01q_move"},
        asdict(ns["ladder_variants"]()["7_dynamic_slot_01q_move"]))
    # A declared hand-worked schedule, NOT output from an installed compiler.
    worked = (WORK / "benchmarks/phase_00/four_qubit_hand_trace.txt").read_text(encoding="utf-8")
    # Independent boundary replay of this declared fixture, not a general physical validator.
    positions, gate_layers, layer = {}, [], []
    for line in worked.splitlines():
        place = re.search(r"PLACE active qubit (\d+) at position (\([^)]*\))", line)
        move = re.search(r"SHUTTLE qubit (\d+) from (\([^)]*\)) to (\([^)]*\))", line)
        gate = re.search(r"CZ q\[(\d+)\], q\[(\d+)\]", line)
        if line.startswith("[EXECUTE"):
            if layer:
                gate_layers.append(layer)
            layer = []
        if place:
            q, pos = int(place[1]), ast.literal_eval(place[2])
            assert q not in positions and pos not in positions.values()
            positions[q] = pos
        if move:
            q, start, end = int(move[1]), ast.literal_eval(move[2]), ast.literal_eval(move[3])
            assert positions[q] == start and end not in positions.values()
            positions[q] = end
        if gate:
            a, b = int(gate[1]), int(gate[2])
            assert math.dist(positions[a], positions[b]) <= 1
            for c, d, pc, pd in layer:
                assert not {a, b} & {c, d}
                assert min(math.dist(x, y) for x in [positions[a], positions[b]] for y in [pc, pd]) >= 2
            layer.append((a, b, positions[a], positions[b]))
    gate_layers.append(layer)
    add("hand_trace_boundary_replay_and_gate_geometry", len(gate_layers), 3)
    expected_gates = [(0, 1), (2, 3), (0, 2), (1, 2)]
    add("hand_trace_gate_sequence", [(a, b) for gl in gate_layers for a, b, _, _ in gl], expected_gates)
    # Dependency depth from operand histories: (1,2) must follow (0,2).
    depths = [0] * 4
    for a, b in expected_gates:
        depths[a] = depths[b] = 1 + max(depths[a], depths[b])
    add("hand_trace_has_three_logical_layers", max(depths), 3)
    parsed = ns["analyze_converted_instructions"](worked, d_atom=3)
    add("hand_trace_gate_count", parsed["Num CZ Gates (from log)"], 4)
    add("hand_trace_move_batches", parsed["Num Movement Ops"], 2)
    add("hand_trace_gate_cycles", parsed["Num Gate Cycles"], 3)
    assert math.isclose(parsed["Total Move Distance"], 3 * (1 + math.sqrt(5)))
    worked_score = ns["_compute_fidelity_from_counts"](num_qubits=4, num_cz_gates=4,
        num_gate_cycles=3, num_movement_ops=2, total_move_distance=parsed["Total Move Distance"], num_moves=2,
        params_optimistic=ns["FidelityParams"](), params_realistic=ns["FidelityParams"](f_trans=0.999))
    return {"scope": "Isolated exact upstream AST routines and hand-specified instruction fixture only; NO full compiler run",
            "source_revision": RFT_REV, "checks": checks, "all_passed": all(c["passed"] for c in checks),
            "orientation_counterexample": orientation, "rft_repeat_case": table, "population_metric_cases": stats,
            "fixture_sha256": digest((WORK / "benchmarks/phase_00/four_qubit_hand_trace.txt").read_bytes())["sha256"],
            "source_hashes": {n: digest((EXCERPT / "src" / n).read_bytes()) for n in
                              ["compiler_core.py", "benchmark_runner.py", "dasatom_instruction_converter.py"]},
            "ladder_options": {k: asdict(v) for k, v in ns["ladder_variants"]().items()},
            "hand_worked_trace_counts": parsed, "hand_worked_trace_legacy_score": worked_score,
            "full_compiler_determinism_tested": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["inventory", "environment", "isolated"])
    parser.add_argument("--output", required=True, help="New JSON artifact under btp_work; existing files are refused")
    args = parser.parse_args()
    target = (ROOT / args.output).resolve()
    if not target.is_relative_to(WORK) or target.exists():
        raise SystemExit("Output must be new and inside btp_work")
    result = {"inventory": inventory, "environment": environment, "isolated": isolated_checks}[args.mode]()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": args.mode, "output": str(target.relative_to(ROOT)),
                      "isolated_check_count": len(result.get("checks", [])),
                      "all_isolated_checks_passed": result.get("all_passed"),
                      "full_compiler_smoke_passed": False}, indent=2))


if __name__ == "__main__":
    main()
