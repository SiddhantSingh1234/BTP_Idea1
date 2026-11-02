"""Run one small pinned upstream compiler case, preserving raw results.

This adapter changes no planner heuristics. DasAtom uses the unmodified standalone
functions with explicit matched geometry. Its text log is a lossless rendering of
native embeddings/gate groups/movement batches, not a physical-event expansion.
Boundary replay is intentionally smaller than the future Phase 02 validator.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import contextlib
import ctypes
from dataclasses import asdict, replace
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time
import traceback

WORK = Path(__file__).resolve().parents[1]
RFT_REV = "3d1f09233c2acd357fd9fbfad1b5300a921d301a"
DAS_REV = "73a6bdf0fd200b2733745211eaf2e0c1e17f496a"
RFT = WORK / "vendor" / f"NAQC_Compiler-{RFT_REV}"
DAS = WORK / "vendor" / f"DasAtom-{DAS_REV}"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(text, normalized, r_int=2, r_blk=4, grid=11):
    """Independent gate/order and batch-boundary checks; no continuous path proof."""
    expected = [tuple(sorted(normalized.find_bit(q).index for q in ins.qubits)) for ins in normalized.data]
    positions, seen, moves, gates = {}, [], [], []
    stages, batches = 0, 0
    errors = []

    def flush_moves():
        nonlocal batches
        if not moves:
            return
        batches += 1
        proposed = dict(positions)
        for q, start, end in moves:
            if positions.get(q) != start:
                errors.append(f"Move source mismatch for q{q}: {positions.get(q)} != {start}")
            proposed[q] = end
        if len(set(proposed.values())) != len(proposed):
            errors.append("Duplicate occupancy at movement batch endpoint")
        positions.clear()
        positions.update(proposed)
        moves.clear()

    def flush_gates():
        for i, (a, b) in enumerate(gates):
            if a not in positions or b not in positions:
                errors.append(f"Gate on absent qubit: {a},{b}")
                continue
            if math.dist(positions[a], positions[b]) > r_int + 1e-9:
                errors.append(f"Interaction range: {a},{b}")
            for c, d in gates[i + 1:]:
                if {a, b} & {c, d}:
                    errors.append("Concurrent gates share qubit")
                elif min(math.dist(positions[x], positions[y]) for x in [a, b] for y in [c, d]) < r_blk - 1e-9:
                    errors.append("Cross-gate restriction radius")
        gates.clear()

    for line in text.splitlines():
        if line.startswith("[") or line.startswith("---"):
            flush_moves()
            flush_gates()
        place = re.search(r"PLACE(?: active| idle)? qubit (\d+) at position (\([^)]*\))", line)
        move = re.search(r"SHUTTLE qubit (\d+) from (\([^)]*\)) to (\([^)]*\))", line)
        gate = re.search(r"CZ q\[(\d+)\], q\[(\d+)\]", line)
        if place:
            q, pos = int(place[1]), ast.literal_eval(place[2])
            if q in positions or pos in positions.values():
                errors.append("Duplicate initial placement")
            positions[q] = pos
        if move:
            moves.append((int(move[1]), ast.literal_eval(move[2]), ast.literal_eval(move[3])))
        if gate:
            pair = (int(gate[1]), int(gate[2]))
            gates.append(pair)
            seen.append(tuple(sorted(pair)))
            location = re.search(r"at locations (\([^)]*\)), (\([^)]*\))", line)
            if location and (positions.get(pair[0]), positions.get(pair[1])) != (ast.literal_eval(location[1]), ast.literal_eval(location[2])):
                errors.append("Printed gate coordinates disagree with replay")
        if line.startswith("[EXECUTE"):
            stages += 1
        if "ERROR" in line:
            errors.append(line)
    flush_moves()
    flush_gates()
    if Counter(expected) != Counter(seen):
        errors.append("Required CZ multiset differs from executed gates")
    for q in range(normalized.num_qubits):
        if [p for p in expected if q in p] != [p for p in seen if q in p]:
            errors.append(f"Dependency order differs for q{q}")
    if set(positions) != set(range(normalized.num_qubits)):
        errors.append("Not all declared qubits are represented")
    if any(not (0 <= p[0] < grid and 0 <= p[1] < grid) for p in positions.values()):
        errors.append("Final coordinate outside requested grid")
    return {"valid_within_coverage": not errors, "errors": errors, "CZ_count": len(seen),
            "gate_cycles": stages, "movement_batches": batches, "final_positions": positions,
            "coverage": ["gate multiset", "per-qubit dependency order", "initial/batch-end occupancy", "gate geometry"],
            "unsupported": ["continuous collision clearance", "trap ownership/transfers", "timed resources", "full original unitary"]}


def mark_stage(out, name):
    (out / "stage.json").write_text(json.dumps({"stage": name, "wall_time": time.time()}), encoding="utf-8")


def standalone(normalized_path, out, grid=11, r_int=2, r_blk=4):
    sys.path.insert(0, str(DAS))
    import DasAtom_fun as f
    from Enola.route import QuantumRouter
    t0 = time.perf_counter()
    circuit = f.CreateCircuitFromQASM(normalized_path.name, str(normalized_path.parent))
    pairs = f.get_2q_gates_list(circuit)
    qc, dag = f.gates_list_to_QC(pairs)
    from qiskit import qasm2
    (out / "planner_input.qasm").write_text(qasm2.dumps(qc) + "\n", encoding="utf-8")
    n = f.get_qubits_num(pairs)
    mark_stage(out, "dasatom_grid")
    graph = f.generate_grid_with_Rb(grid, grid, r_int)
    mark_stage(out, "dasatom_partition")
    partitions = f.partition_from_DAG(dag, graph)
    mark_stage(out, "dasatom_embeddings")
    embeddings, extensions = f.get_embeddings(partitions, graph, n, grid, r_int)
    actual_grid = grid + len(extensions)
    router = QuantumRouter(n, embeddings, partitions, [actual_grid, actual_grid])
    mark_stage(out, "dasatom_routing")
    router.run()
    mark_stage(out, "dasatom_gate_groups")
    groups = [f.get_parallel_gates(p, graph, e, r_blk) for p, e in zip(partitions, embeddings)]
    native_seconds = time.perf_counter() - t0
    all_groups = [g for p in groups for g in p]
    all_moves = [batch for transition in router.movement_list for batch in transition]
    native_score = f.compute_fidelity(all_groups, all_moves, n, len(pairs))
    native = {"partitions": partitions, "embeddings": embeddings, "extensions": extensions,
              "gate_groups": groups, "movement_list": router.movement_list,
              "score_tuple": native_score, "actual_grid": actual_grid}
    (out / "native_dasatom.json").write_text(json.dumps(native, indent=2) + "\n", encoding="utf-8")
    lines = ["[INITIAL PLACEMENT]"]
    for q, pos in enumerate(embeddings[0]):
        lines.append(f"  PLACE qubit {q} at position {tuple(pos)}")
    for i, (embedding, gate_groups) in enumerate(zip(embeddings, groups)):
        for j, group in enumerate(gate_groups):
            lines.append(f"[EXECUTE partition {i} group {j}]")
            for a, b in group:
                lines.append(f"  CZ q[{a}], q[{b}] (at locations {tuple(embedding[a])}, {tuple(embedding[b])})")
        if i < len(router.movement_list):
            for j, batch in enumerate(router.movement_list[i]):
                lines.append(f"[SHUTTLING] transition {i} batch {j}")
                for q, start, end in batch:
                    lines.append(f"  SHUTTLE qubit {q} from {tuple(start)} to {tuple(end)}")
    return "\n".join(lines), {"adapter_pipeline_seconds": native_seconds,
        "timing_scope": "standalone loading normalized CZ input, DAG, grid, partition, embedding, routing, grouping; excludes imports/normalization/scoring/logging",
        "native_score_tuple_fields": ["idle_us", "legacy_fidelity", "movement_fidelity", "runtime_us", "transfer_alias", "atom_moves", "batch_max_distance_um"],
        "native_score": native_score, "native_num_qubits": n, "partitions": len(partitions), "actual_grid": actual_grid,
        "helper_file": str(Path(f.__file__).relative_to(WORK)),
        "router_file": str(Path(sys.modules[QuantumRouter.__module__].__file__).relative_to(WORK))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--algorithm", choices=["rft", "dasatom"], required=True)
    p.add_argument("--case", choices=["qft5", "tableII", "file"], required=True)
    p.add_argument("--input", help="For --case file: immutable QASM path under btp_work")
    p.add_argument("--grid", type=int, default=11)
    p.add_argument("--r-int", type=float, default=2)
    p.add_argument("--r-blk", type=float, default=4)
    p.add_argument("--variant", default="7_dynamic_slot_01q_move")
    p.add_argument("--register-policy", choices=["native", "active_prefix"], default="native")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--routing-seed", type=int)
    p.add_argument("--out", required=True, help="New directory relative to btp_work")
    args = p.parse_args()
    out = (WORK / args.out).resolve()
    if not out.is_relative_to(WORK) or out.exists():
        raise SystemExit("Use a new output directory under btp_work")
    out.mkdir(parents=True)
    for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"]:
        os.environ[key] = "1"
    os.environ["MPLCONFIGDIR"] = str(WORK / ".compiler-tools/matplotlib")
    os.environ["XDG_CACHE_HOME"] = str(WORK / ".compiler-tools/xdg-cache")
    os.environ["TEMP"] = os.environ["TMP"] = str(WORK / ".compiler-tools/tmp")
    sys.dont_write_bytecode = True
    os.chdir(out)
    result = {"algorithm": args.algorithm, "case": args.case, "status": "error", "paper_reproduction": False,
              "rft_revision": RFT_REV, "dasatom_revision": DAS_REV, "python": sys.version,
              "seed": args.seed, "routing_seed": args.routing_seed, "hash_seed": os.environ.get("PYTHONHASHSEED"), "threads": 1,
              "geometry": {"rows": args.grid, "columns": args.grid, "r_int": args.r_int, "r_blk": args.r_blk},
              "normalization_policy": args.register_policy,
              "command": [sys.executable, *sys.argv], "output_directory": str(out.relative_to(WORK))}
    log = io.StringIO()
    mark_stage(out, "imports")
    try:
        with contextlib.redirect_stdout(log):
            sys.path.insert(0, str(RFT / "src"))
            import benchmark_runner as runner
            from qiskit import QuantumCircuit, qasm2, transpile
            source = (Path(args.input).resolve() if args.case == "file" else
                DAS / ("Data/qiskit-bench/qft/qft_5.qasm" if args.case == "qft5" else "Data/Q_Tetris/4mod5-v1_22.qasm"))
            if not source.is_relative_to(WORK):
                raise ValueError("Input must be under btp_work")
            mark_stage(out, "normalization")
            raw = QuantumCircuit.from_qasm_file(str(source))
            t0 = time.perf_counter()
            synthesized = transpile(raw, basis_gates=['cz','h','s','t','rx','ry','rz'], optimization_level=0)
            normalized = runner.preprocess_circuit(synthesized)
            declared_n = normalized.num_qubits
            prefix_n = max((normalized.find_bit(q).index + 1 for ins in normalized.data for q in ins.qubits), default=0)
            if not prefix_n:
                raise ValueError("No two-qubit operations after upstream normalization")
            if args.register_policy == "active_prefix":
                reduced = QuantumCircuit(prefix_n)
                for ins in normalized.data:
                    a, b = [normalized.find_bit(q).index for q in ins.qubits]
                    reduced.cz(a, b)
                normalized = reduced
            normpath = out / "normalized.qasm"
            normpath.write_text(qasm2.dumps(normalized) + "\n", encoding="utf-8")
            result.update(input_path=source.relative_to(WORK).as_posix(), input_sha256=sha(source),
                normalized_sha256=sha(normpath), preprocessing_seconds=time.perf_counter() - t0,
                input_declared_qubits=declared_n, active_prefix_qubits=prefix_n,
                num_qubits=normalized.num_qubits, num_cz=len(normalized.data), logical_layers=normalized.depth())
            random.seed(args.seed)
            result["global_random_state_before"] = hashlib.sha256(repr(random.getstate()).encode()).hexdigest()
            if args.algorithm == "rft":
                t0 = time.perf_counter()
                mark_stage(out, "rft_offline_layout")
                count, layout = runner.sample_max_parallel(args.grid, args.grid, args.r_int, args.r_blk, m=20)
                result["offline_layout_seconds"] = time.perf_counter() - t0
                result["layout"] = layout
                options = replace(runner.ladder_variants()[args.variant], random_seed=args.seed)
                result["options"] = asdict(options)
                # Preserve the runner's one warmup call and global RNG consumption.
                compiler_input = normpath if args.register_policy == "active_prefix" else source
                mark_stage(out, "rft_warmup")
                runner.run_benchmark(str(compiler_input), args.grid, args.grid, args.r_int, args.r_blk, layout, options)
                if args.routing_seed is not None:
                    random.seed(args.routing_seed)
                mark_stage(out, "rft_compile")
                stats = runner.run_benchmark(str(compiler_input), args.grid, args.grid, args.r_int, args.r_blk, layout, options)
                text = "\n".join(stats.pop("instructions"))
                result["native_metrics"] = stats
                result["timing_scope"] = "untouched RFT run_benchmark timed region; warmup/offline layout/preprocessing/scoring excluded"
            else:
                text, native = standalone(normpath, out, args.grid, args.r_int, args.r_blk)
                result["native_metrics"] = native
            result["global_random_state_after"] = hashlib.sha256(repr(random.getstate()).encode()).hexdigest()
            (out / "instructions.txt").write_text(text + "\n", encoding="utf-8")
            result["trace_sha256"] = sha(out / "instructions.txt")
            mark_stage(out, "boundary_replay")
            result["boundary_replay"] = replay(text, normalized, args.r_int, args.r_blk, args.grid)
            # Shared unmodified scalar parser/scorer; standalone native score is also retained.
            import dasatom_instruction_converter as converter
            parsed = converter.analyze_converted_instructions(text, d_atom=3.0)
            shared = converter._compute_fidelity_from_counts(num_qubits=normalized.num_qubits,
                num_cz_gates=len(normalized.data), num_gate_cycles=parsed["Num Gate Cycles"],
                num_movement_ops=parsed["Num Movement Ops"], total_move_distance=parsed["Total Move Distance"],
                num_moves=parsed["Num Moves"], params_optimistic=converter.FidelityParams(),
                params_realistic=converter.FidelityParams(f_trans=0.999))
            result["legacy_counts"], result["shared_legacy_score"] = parsed, shared
            register_mismatch = False
            if args.algorithm == "dasatom":
                n = result["native_metrics"]["native_num_qubits"]
                native_normalized = QuantumCircuit(n)
                for ins in normalized.data:
                    a, b = [normalized.find_bit(q).index for q in ins.qubits]
                    native_normalized.cz(a, b)
                result["native_register_replay"] = replay(text, native_normalized, args.r_int, args.r_blk, args.grid)
                native_score = converter._compute_fidelity_from_counts(num_qubits=n,
                    num_cz_gates=len(normalized.data), num_gate_cycles=parsed["Num Gate Cycles"],
                    num_movement_ops=parsed["Num Movement Ops"], total_move_distance=parsed["Total Move Distance"],
                    num_moves=parsed["Num Moves"], params_optimistic=converter.FidelityParams(),
                    params_realistic=converter.FidelityParams(f_trans=0.999))
                result["native_N_shared_score"] = native_score
                assert math.isclose(native_score["Fidelity (DasAtom Model)"], result["native_metrics"]["native_score"][1], rel_tol=1e-12)
                register_mismatch = n != normalized.num_qubits
                result["register_policy"] = {"input_declared_N": normalized.num_qubits, "native_N": n,
                    "behavior": "upstream infers max(two-qubit operand)+1, dropping trailing inactive qubits",
                    "matched_full_register_supported": not register_mismatch}
            result["module_providers"] = {n: str(Path(sys.modules[n].__file__).relative_to(WORK)) for n in
                ["compiler_core", "benchmark_runner", "dasatom_instruction_converter", "DasAtom_fun", "Enola.route"] if n in sys.modules}
            result["packages"] = {n: importlib.metadata.version(n) for n in ["qiskit","numpy","scipy","networkx","rustworkx","pandas"]}
            result["planner_input_sha256"] = sha(out / "planner_input.qasm") if args.algorithm == "dasatom" else result["normalized_sha256"]
            result["legacy_error_terms"] = {"E_native_CZ": -len(normalized.data) * math.log(0.995),
                "E_legacy_idle": shared["Idle Time (us)"] / 1.5e6,
                "E_ideal_transfer": 0.0, "underflow": shared["Fidelity (DasAtom Model)"] == 0}
            result["status"] = "ok" if result["boundary_replay"]["valid_within_coverage"] else "invalid"
            if register_mismatch and result["native_register_replay"]["valid_within_coverage"]:
                result["status"] = "unsupported_declared_register"
                result["compiler_status"] = "native_pipeline_completed"
    except Exception as e:
        result["error"] = {"type": type(e).__name__, "message": str(e), "traceback": traceback.format_exc()}
    (out / "stdout.txt").write_text(log.getvalue(), encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"algorithm": args.algorithm, "case": args.case, "status": result["status"],
        "output": str(out), "num_cz": result.get("num_cz"), "counts": result.get("legacy_counts"), "error": result.get("error")}, indent=2))
    raise SystemExit(0 if result["status"] == "ok" else 2 if result["status"] == "unsupported_declared_register" else 1)


if __name__ == "__main__":
    main()
