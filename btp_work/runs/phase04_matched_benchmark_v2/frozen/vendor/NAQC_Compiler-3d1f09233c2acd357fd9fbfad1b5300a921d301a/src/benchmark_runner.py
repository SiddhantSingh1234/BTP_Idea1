# benchmark_runner.py (Corrected to pass 'physical_layout')

import os
import time
import math
import pandas as pd
import numpy as np
import re
import argparse
from typing import Optional
from qiskit import QuantumCircuit, qasm2
from qiskit.compiler import transpile

# --- Import from compiler_core ---
from compiler_core import (
    analyze_qasm_file, find_busiest_pairs, sample_max_parallel,
    create_initial_mapping, generate_hardware_instructions,
    CompilerOptions, AssignmentMode, IdleParkingMode, CandidateSlotsMode,
    GridCapacityError
)


def preprocess_circuit(transpiled_circuit: QuantumCircuit):
    num_qubits = transpiled_circuit.num_qubits
    preprocessed_circuit = QuantumCircuit(num_qubits)
    for instruction in transpiled_circuit.data:
        if instruction.operation.num_qubits == 2:
            qubit_indices = [transpiled_circuit.find_bit(q).index for q in instruction.qubits]
            preprocessed_circuit.cz(qubit_indices[0], qubit_indices[1])
    return preprocessed_circuit

def calculate_dasatom_metrics(final_instructions, transpiled_circuit, preprocessed_circuit):
    from dasatom_instruction_converter import analyze_converted_instructions, _compute_fidelity_from_counts, FidelityParams
    
    num_qubits = transpiled_circuit.num_qubits
    num_cz_gates = transpiled_circuit.count_ops().get('cz', 0)
    
    params_optimistic = FidelityParams(T2=1.5e6, f_cz=0.995, f_trans=1.0, t_cz=0.2, t_trans=20, v=0.55, d_atom=3.0)
    params_realistic = FidelityParams(T2=1.5e6, f_cz=0.995, f_trans=0.999, t_cz=0.2, t_trans=20, v=0.55, d_atom=3.0)

    text = "\n".join(final_instructions)
    stats = analyze_converted_instructions(text, d_atom=params_optimistic.d_atom)

    dasatom_metrics = _compute_fidelity_from_counts(
        num_qubits=num_qubits,
        num_cz_gates=num_cz_gates,
        num_gate_cycles=stats["Num Gate Cycles"],
        num_movement_ops=stats["Num Movement Ops"],
        total_move_distance=stats["Total Move Distance"],
        num_moves=stats["Num Moves"],
        params_optimistic=params_optimistic,
        params_realistic=params_realistic,
    )

    return {
        "Circuit Depth": preprocessed_circuit.depth(),
        **dasatom_metrics
    }
def run_benchmark(qasm_file_path, R, C, r_int, r_blk, physical_layout, options: CompilerOptions):
    print(f"  Processing {os.path.basename(qasm_file_path)} [{options}]...")
    original_circuit = QuantumCircuit.from_qasm_file(qasm_file_path)
    
    dasatom_basis = ['cz', 'h', 's', 't', 'rx', 'ry', 'rz']
    transpiled_circuit = transpile(original_circuit, basis_gates=dasatom_basis, optimization_level=0)
    
    preprocessed_circuit_for_compiler = preprocess_circuit(transpiled_circuit)
    if not preprocessed_circuit_for_compiler.data:
        print(f"    Skipping: No two-qubit gates after preprocessing.")
        return None
    qasm_string = qasm2.dumps(preprocessed_circuit_for_compiler)
    with open("temp_preprocessed.qasm", "w") as f: f.write(qasm_string)
    start_time = time.time()
    _, time_series, num_qubits = analyze_qasm_file("temp_preprocessed.qasm")
    if not time_series:
        os.remove("temp_preprocessed.qasm"); return None

    busiest_pairs = find_busiest_pairs(time_series)
    
    canonical_mapping = create_initial_mapping(busiest_pairs, physical_layout)
    
    # Pass layout and blockade radius to compiler
    try:
        final_instructions = generate_hardware_instructions(
            time_series,
            canonical_mapping,
            busiest_pairs,
            num_qubits,
            R,
            C,
            physical_layout,
            r_blk,
            r_int,
            options=options,
        )
    except GridCapacityError as e:
        print(f"    [SKIP] {e}")
        os.remove("temp_preprocessed.qasm")
        return None
    
    end_time = time.time()
    os.remove("temp_preprocessed.qasm")
    das_metrics = calculate_dasatom_metrics(final_instructions, transpiled_circuit, preprocessed_circuit_for_compiler)
    all_stats = {
        "QASM File": os.path.basename(qasm_file_path),
        "Num Qubit": num_qubits,
        "Num CZ Gates": transpiled_circuit.count_ops().get('cz', 0),
        **das_metrics,
        "Elapsed Time (s)": end_time - start_time,
        "Variant": options.variant_name,
        "instructions": final_instructions  # Save for visualization
    }
    return all_stats

def ladder_variants() -> dict:
    # Ordered exactly as your requested ladder output list.
    base = CompilerOptions()

    return {
        "1_all_random": CompilerOptions(
            variant_name="all_random",
            enable_keep_adjacent=False,
            enable_one_qubit_move=False,
            candidate_slots_mode=CandidateSlotsMode.ALL_COMPATIBLE,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=AssignmentMode.RANDOM,
            idle_parking_mode=IdleParkingMode.RANDOM,
            random_seed=base.random_seed,
        ),
        "2_greedy_nearest_idle_parking": CompilerOptions(
            variant_name="2_greedy_nearest_idle_parking",
            enable_keep_adjacent=False,
            enable_one_qubit_move=False,
            candidate_slots_mode=CandidateSlotsMode.ALL_COMPATIBLE,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=AssignmentMode.RANDOM,
            idle_parking_mode=IdleParkingMode.GREEDY_NEAREST,
            random_seed=base.random_seed,
        ),
        "3_hungarian": CompilerOptions(
            variant_name="3_hungarian",
            enable_keep_adjacent=False,
            enable_one_qubit_move=False,
            candidate_slots_mode=CandidateSlotsMode.ALL_COMPATIBLE,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=base.assignment_mode,
            idle_parking_mode=IdleParkingMode.GREEDY_NEAREST,
            random_seed=base.random_seed,
        ),
        "4_CoM_subset": CompilerOptions(
            variant_name="4_CoM_subset",
            enable_keep_adjacent=False,
            enable_one_qubit_move=False,
            candidate_slots_mode=base.candidate_slots_mode,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=base.assignment_mode,
            idle_parking_mode=IdleParkingMode.GREEDY_NEAREST,
            random_seed=base.random_seed,
        ),
        "5_rft_idle_parking": CompilerOptions(
            variant_name="5_rft_idle_parking",
            enable_keep_adjacent=False,
            enable_one_qubit_move=False,
            candidate_slots_mode=base.candidate_slots_mode,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=base.assignment_mode,
            idle_parking_mode=base.idle_parking_mode,
            random_seed=base.random_seed,
        ),
        "6_dynamic_slot_0q_move": CompilerOptions(
            variant_name="6_dynamic_slot_0q_move",
            enable_keep_adjacent=True,
            enable_one_qubit_move=False,
            candidate_slots_mode=base.candidate_slots_mode,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=base.assignment_mode,
            idle_parking_mode=base.idle_parking_mode,
            random_seed=base.random_seed,
        ),
        "7_dynamic_slot_01q_move": CompilerOptions(
            variant_name="7_dynamic_slot_01q_move",
            enable_keep_adjacent=base.enable_keep_adjacent,
            enable_one_qubit_move=base.enable_one_qubit_move,
            candidate_slots_mode=base.candidate_slots_mode,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=base.assignment_mode,
            idle_parking_mode=base.idle_parking_mode,
            random_seed=base.random_seed,
        ),
        # idle qubit move to future partner closest position
        "8_optimized_eviction": CompilerOptions(
            variant_name="8_optimized_eviction",
            enable_keep_adjacent=base.enable_keep_adjacent,
            enable_one_qubit_move=base.enable_one_qubit_move,
            candidate_slots_mode=base.candidate_slots_mode,
            pad_cost_matrix_to_square=base.pad_cost_matrix_to_square,
            assignment_mode=base.assignment_mode,
            idle_parking_mode=base.idle_parking_mode,
            random_seed=base.random_seed,
            evicted_park_closest_to_partner=True,
        ),
    }


def main_experiment(
    circuit_folder_path: str,
    dataset: str,
    limit: Optional[int] = None,
    *,
    r_int_values: Optional[list[int]] = None,
    selected_variants: Optional[list[str]] = None,
    r_blk: int = 4,
    grid_size_override: Optional[int] = None,
    dynamic_grid: bool = False,
):
    if not os.path.isdir(circuit_folder_path):
        print(f"Error: Directory '{circuit_folder_path}' not found."); return
    
    # Base grid size (may be overwritten if dynamic_grid is False)
    if grid_size_override:
        init_R, init_C = grid_size_override, grid_size_override
    else:
        init_R, init_C = 11, 11

    if r_int_values is None:
        r_int_values = [2]
    
    for r_int in r_int_values:
        print(f"\n\n##################################################")
        print(f"### RUNNING EXPERIMENT WITH r_int = {r_int} ###")
        print(f"##################################################\n")

        variants = ladder_variants()
        if selected_variants:
            variants = {k: v for k, v in variants.items() if k in set(selected_variants)}
        
        instructions_root = os.path.join("instruction_logs", f"{dataset}_ladder_rint{r_int}")
        os.makedirs(instructions_root, exist_ok=True)
    
        qasm_files = [
            os.path.join(circuit_folder_path, fn)
            for fn in sorted(os.listdir(circuit_folder_path))
            if fn.endswith(".qasm")
        ]
        if limit is not None:
            qasm_files = qasm_files[: max(0, int(limit))]
    
        if not qasm_files:
            print("No valid .qasm files found.")
            return

        # Prepare a shared physical layout if grid is NOT dynamic
        shared_layout = None
        if not dynamic_grid:
            _, shared_layout = sample_max_parallel(init_R, init_C, r_int, r_blk, m=20)

        # --- Warm-up run ---
        print(f"\n[WARM-UP] Processing {os.path.basename(qasm_files[0])}...")
        warmup_options = list(variants.values())[0]
        
        # We need num_qubits for warm-up too if dynamic
        if dynamic_grid:
            qc_warm = QuantumCircuit.from_qasm_file(qasm_files[0])
            n_warm = qc_warm.num_qubits
            R_w = math.ceil(math.sqrt(n_warm))
            _, w_layout = sample_max_parallel(R_w, R_w, r_int, r_blk, m=20)
            run_benchmark(qasm_files[0], R_w, R_w, r_int, r_blk, w_layout, warmup_options)
        else:
            run_benchmark(qasm_files[0], init_R, init_C, r_int, r_blk, shared_layout, warmup_options)
        print("[WARM-UP] Complete.\n")

        for variant_name, options in variants.items():
            print(f"\n=== Running variant: {variant_name} (r_int={r_int}) ===")
            results = []
            instructions_dir = os.path.join(instructions_root, variant_name)
            os.makedirs(instructions_dir, exist_ok=True)
        
            for qasm_path in qasm_files:
                filename = os.path.basename(qasm_path)
                
                if dynamic_grid:
                    # Get qubit count to determine grid
                    qc_tmp = QuantumCircuit.from_qasm_file(qasm_path)
                    n_q = qc_tmp.num_qubits
                    cur_R = math.ceil(math.sqrt(n_q))
                    cur_C = cur_R
                    print(f"    [Dynamic Grid] Using {cur_R}x{cur_C} for {n_q} qubits")
                    _, cur_layout = sample_max_parallel(cur_R, cur_C, r_int, r_blk, m=20)
                    stats = run_benchmark(qasm_path, cur_R, cur_C, r_int, r_blk, cur_layout, options)
                else:
                    stats = run_benchmark(qasm_path, init_R, init_C, r_int, r_blk, shared_layout, options)
                
                if not stats: continue
    
                if "instructions" in stats and stats["instructions"]:
                    circuit_name = os.path.splitext(filename)[0]
                    instruction_file = os.path.join(instructions_dir, f"{circuit_name}_instructions.txt")
                    with open(instruction_file, "w") as f:
                        f.write("\n".join(stats["instructions"]))
    
                results.append(stats)
    
            if not results: continue
    
            df = pd.DataFrame(results)
            df["Num Partitions"] = df["Num Gate Cycles"]
            report_columns = [
                "Variant", "QASM File", "Num Qubit", "Num CZ Gates", "Circuit Depth",
                "Fidelity (DasAtom Model)", "Fidelity (Realistic)", "Movement Fidelity",
                "Num Movement Ops", "Num Transferred Qubits", "Num Moves", "Total Move Distance",
                "Num Gate Cycles", "Num Partitions", "Elapsed Time (s)", "Total_T (us)", "Idle Time (us)",
            ]
    
            df = df[report_columns]
            results_root = os.path.join("results", f"{dataset}_ladder_rint{r_int}")
            os.makedirs(results_root, exist_ok=True)
            out_csv = os.path.join(results_root, f"{dataset}_ladder_{variant_name}.csv")
            df.to_csv(out_csv, index=False)
            print(f"[OK] Results saved to {out_csv}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="dasatom/DasAtom-main/Data/qiskit-bench/qft/qft_small")
    parser.add_argument("--dataset", type=str, default="qft")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--r-ints", type=str, default=None)
    parser.add_argument("--variants", type=str, default=None)
    parser.add_argument("--r-blk", type=int, default=4)
    parser.add_argument("--grid-size", type=int, default=None)
    parser.add_argument("--dynamic-grid", action="store_true", help="Use sqrt(n)xsqrt(n) grid per circuit.")
    args = parser.parse_args()

    r_int_values = None
    if args.r_ints:
        r_int_values = [int(x.strip()) for x in args.r_ints.split(",") if x.strip()]

    selected_variants = None
    if args.variants:
        selected_variants = [x.strip() for x in args.variants.split(",") if x.strip()]

    main_experiment(
        args.folder,
        dataset=args.dataset,
        limit=args.limit,
        r_int_values=r_int_values,
        selected_variants=selected_variants,
        r_blk=args.r_blk,
        grid_size_override=args.grid_size,
        dynamic_grid=args.dynamic_grid,
    )
