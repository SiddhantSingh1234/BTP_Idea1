"""Capture actual full-planner decisions for the existing ladder6 tiny fixture.

Python tracing observes locals and return values; no compiler function is patched.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import random
import sys

WORK = Path(__file__).resolve().parents[1]
RFT = WORK / "vendor/NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a"


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if hasattr(value, "tolist"):
        return clean(value.tolist())
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = (WORK / args.out).resolve()
    if not out.is_relative_to(WORK) or out.exists():
        raise SystemExit("Use a new output directory under btp_work")
    out.mkdir(parents=True)
    sys.dont_write_bytecode = True
    for k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        os.environ[k] = "1"
    sys.path.insert(0, str(RFT / "src"))
    import compiler_core as core
    from benchmark_runner import ladder_variants
    from qiskit import QuantumCircuit
    from phase00_smoke import replay
    fixture = WORK / "benchmarks/phase_00/four_qubit_hand_trace.qasm"
    _, schedule, n = core.analyze_qasm_file(str(fixture))
    options = ladder_variants()["6_dynamic_slot_0q_move"]
    layout = [[(0, 0), (0, 1)], [(2, 0), (2, 1)]]
    decisions = []
    observed = {"timestamp_name", "sub_step_index", "movers", "candidate_slots", "cost_A", "cost_B", "cost_matrix",
        "active_qubit_targets", "current_qubit_positions", "final_target_positions", "evicted_qubits",
        "current_future_partners", "center_of_mass", "qubit", "available_positions", "is_evicted",
        "current_positions", "target_positions", "r", "c", "dist_A", "dist_B"}
    source = str((RFT / "src/compiler_core.py").resolve())
    def tracer(frame, event, arg):
        if str(Path(frame.f_code.co_filename).resolve()) != source:
            return None
        function = frame.f_code.co_name
        capture = ((function == "generate_hardware_instructions" and event == "line" and frame.f_lineno in [634, 647, 735, 741, 744])
                   or (function in ["_pick_idle_position", "generate_safe_shuttle_instructions"] and event in ["call", "return"]))
        if capture:
            row = {"function": function, "event": event, "line": frame.f_lineno,
                   "locals": {k: clean(v) for k, v in frame.f_locals.items() if k in observed}}
            if event == "return":
                row["return"] = clean(arg)
            decisions.append(row)
        return tracer
    random.seed(42)
    sys.settrace(tracer)
    try:
        instructions = core.generate_hardware_instructions(schedule, {}, [], n, 3, 3, layout, 2, 1, options=options)
    finally:
        sys.settrace(None)
    text = "\n".join(instructions) + "\n"
    (out / "instructions.txt").write_text(text, encoding="utf-8")
    import dasatom_instruction_converter as metric
    counts = metric.analyze_converted_instructions(text, d_atom=3)
    score = metric._compute_fidelity_from_counts(num_qubits=4, num_cz_gates=4,
        num_gate_cycles=counts["Num Gate Cycles"], num_movement_ops=counts["Num Movement Ops"],
        total_move_distance=counts["Total Move Distance"], num_moves=counts["Num Moves"],
        params_optimistic=metric.FidelityParams(), params_realistic=metric.FidelityParams(f_trans=0.999))
    evictions = [r for r in decisions if r["function"] == "_pick_idle_position" and r["event"] == "return" and r["locals"]["is_evicted"]]
    result = {"scope": "actual unmodified full compiler on declared existing ladder6 fixture; not the default ladder7 or a published target",
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(), "schedule": schedule,
        "options": asdict(options), "grid": [3, 3], "r_int": 1, "r_blk": 2, "physical_layout": layout,
        "right_filled_table": core.build_right_filled_table(schedule, n), "decisions": decisions,
        "forced_eviction_count": len(evictions), "evictions": evictions,
        "counts": counts, "legacy_score": score, "boundary_replay": replay(text, QuantumCircuit.from_qasm_file(str(fixture)), 1, 2),
        "trace_sha256": hashlib.sha256(text.encode()).hexdigest()}
    (out / "trace.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert len(schedule) >= 3 and evictions and result["boundary_replay"]["valid_within_coverage"]
    print(json.dumps({"forced_evictions": len(evictions), "counts": counts, "score": score, "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
