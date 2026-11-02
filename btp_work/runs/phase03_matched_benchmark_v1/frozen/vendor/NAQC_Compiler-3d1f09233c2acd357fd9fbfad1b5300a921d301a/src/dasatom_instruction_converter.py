"""DasAtom Hardware Instruction Converter.

Converts DasAtom's movement_list and embeddings into a text-based instruction
format compatible with our visualization tools.

Additionally, it can compute the same "realistic" fidelity model used by
`benchmark_runner.py` by parsing the converted instruction logs (no DasAtom code
changes required).
"""

import os
import sys
import math
import csv
import re
import time
from dataclasses import dataclass
from typing import Optional, Any

# Add DasAtom to path (use relative join without a leading slash)
dasatom_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dasatom', 'DasAtom-main'))

if dasatom_path not in sys.path:
    sys.path.insert(0, dasatom_path)

from DasAtom_fun import (
    CreateCircuitFromQASM, get_2q_gates_list, gates_list_to_QC,
    get_qubits_num, generate_grid_with_Rb, partition_from_DAG,
    get_embeddings, get_parallel_gates, compute_fidelity
)
from Enola.route import QuantumRouter


@dataclass(frozen=True)
class FidelityParams:
    # Units match benchmark_runner.py
    T2: float = 1.5e6
    f_cz: float = 0.995
    f_trans: float = 1.0
    t_cz: float = 0.2
    t_trans: float = 20
    v: float = 0.55
    d_atom: float = 3.0


def _compute_fidelity_from_counts(
    *,
    num_qubits: int,
    num_cz_gates: int,
    num_gate_cycles: int,
    num_movement_ops: int,
    total_move_distance: float,
    num_moves: int,
    params_optimistic: FidelityParams,
    params_realistic: FidelityParams,
) -> dict[str, Any]:
    # Matches calculate_dasatom_metrics() in benchmark_runner.py
    t_move = (num_movement_ops * 4 * params_optimistic.t_trans) + (total_move_distance / params_optimistic.v)
    total_t = (num_gate_cycles * params_optimistic.t_cz) + t_move
    idle_time = (num_qubits * total_t) - (num_cz_gates * params_optimistic.t_cz)
    num_transfers = num_movement_ops * 4

    fidelity_dasatom_model = (
        math.exp(-idle_time / params_optimistic.T2)
        * (params_optimistic.f_cz ** num_cz_gates)
        * (params_optimistic.f_trans ** num_transfers)
    )
    fidelity_realistic = (
        math.exp(-idle_time / params_realistic.T2)
        * (params_realistic.f_cz ** num_cz_gates)
        * (params_realistic.f_trans ** num_transfers)
    )
    movement_fidelity = math.exp(-t_move / params_optimistic.T2)

    return {
        "Fidelity (DasAtom Model)": fidelity_dasatom_model,
        "Fidelity (Realistic)": fidelity_realistic,
        "Movement Fidelity": movement_fidelity,
        "Num Movement Ops": num_movement_ops,
        "Num Transferred Qubits": num_transfers,
        "Num Moves": num_moves,
        "Total Move Distance": total_move_distance,
        "Num Gate Cycles": num_gate_cycles,
        "Total_T (us)": total_t,
        "Idle Time (us)": idle_time,
    }


def analyze_converted_instructions(text: str, *, d_atom: float) -> dict[str, Any]:
    """Parse a converted instruction log and extract the movement/gate-cycle stats
    needed for the fidelity model.

    - Counts gate cycles by number of "[EXECUTE" blocks.
    - Counts movement ops by number of "[SHUTTLING]" blocks that contain at least one SHUTTLE.
    - Total move distance follows the DasAtom model convention: sum of max shuttle distance
      per movement step (each step = one [SHUTTLING] block).
    """
    num_gate_cycles = 0
    num_movement_ops = 0
    num_moves = 0
    total_move_distance = 0.0
    num_cz_gates = 0

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if "[EXECUTE" in line:
            num_gate_cycles += 1
            i += 1
            continue

        if "[SHUTTLING]" in line:
            i += 1
            shuttles: list[tuple[tuple[float, float], tuple[float, float]]] = []
            while i < len(lines):
                curr = lines[i]
                if curr.startswith("--- Processing Time") or curr.startswith("--- Batch Separator") or curr.strip().startswith("["):
                    break
                m = re.search(r"SHUTTLE qubit\s+\d+\s+from\s+\(([^)]*)\)\s+to\s+\(([^)]*)\)", curr)
                if m:
                    start_str, target_str = m.group(1), m.group(2)
                    start = tuple(float(c.strip()) for c in start_str.split(","))
                    target = tuple(float(c.strip()) for c in target_str.split(","))
                    shuttles.append(((start[0], start[1]), (target[0], target[1])))
                i += 1

            if shuttles:
                num_movement_ops += 1
                max_dist = 0.0
                for (sr, sc), (tr, tc) in shuttles:
                    num_moves += 1
                    dist = math.sqrt((sr - tr) ** 2 + (sc - tc) ** 2) * d_atom
                    if dist > max_dist:
                        max_dist = dist
                total_move_distance += max_dist
            continue

        # Count CZ lines (each CZ line is one gate)
        if re.search(r"^\s*CZ\s+q\[\d+\],\s*q\[\d+\]", line):
            num_cz_gates += 1

        i += 1

    return {
        "Num Gate Cycles": num_gate_cycles,
        "Num Movement Ops": num_movement_ops,
        "Num Moves": num_moves,
        "Total Move Distance": total_move_distance,
        "Num CZ Gates (from log)": num_cz_gates,
    }


def convert_dasatom_to_instructions(qasm_path, output_file, R=15, C=15, r_int=2, grid_size_override=None):
    """
    Process a QASM file using DasAtom and convert its output to our instruction format.
    
    Args:
        qasm_path: Path to the QASM file
        output_file: Path to save the instruction text file
        R, C: Grid dimensions
        r_int: Interaction radius
        grid_size_override: Optional override for grid size (uses sqrt(num_qubits) if None)
    """
    instructions = []
    
    # Extract circuit name
    circuit_name = os.path.splitext(os.path.basename(qasm_path))[0]
    
    # 1. Load and process circuit using DasAtom
    qasm_circuit = CreateCircuitFromQASM(os.path.basename(qasm_path), os.path.dirname(qasm_path))
    two_qubit_gates_list = get_2q_gates_list(qasm_circuit)
    
    if not two_qubit_gates_list:
        print(f"  [WARN] No CZ gates found in {circuit_name}")
        return False
    
    qc_object, dag_object = gates_list_to_QC(two_qubit_gates_list)
    num_qubits = get_qubits_num(two_qubit_gates_list)
    grid_size = grid_size_override if grid_size_override else math.ceil(math.sqrt(num_qubits))
    print(f"    Using grid size: {grid_size}x{grid_size} for {num_qubits} qubits")
    
    # 2. Generate coupling graph
    print(f"\n    [Stage 2/7] Generating coupling graph (grid={grid_size}x{grid_size}, r_int={r_int})...", end='', flush=True)
    stage_start = time.time()
    coupling_graph = generate_grid_with_Rb(grid_size, grid_size, r_int)
    print(f" OK ({time.time() - stage_start:.2f}s)")
    
    # 3. Partition circuit
    print(f"    [Stage 3/7] Partitioning circuit (DAG -> gates)...", end='', flush=True)
    stage_start = time.time()
    partitioned_gates = partition_from_DAG(dag_object, coupling_graph)
    print(f" OK ({time.time() - stage_start:.2f}s)")
    
    # 4. Generate embeddings
    print(f"    [Stage 4/7] Searching for physical embeddings (NP-hard search)...", end='', flush=True)
    stage_start = time.time()
    embeddings, extended_positions = get_embeddings(
        partitioned_gates,
        coupling_graph,
        num_qubits,
        grid_size,
        r_int
    )
    print(f" OK ({time.time() - stage_start:.2f}s)")
    
    # Update grid size if extended
    if extended_positions:
        grid_size += len(extended_positions)
    
    # 5. Setup router to get movements
    print(f"    [Stage 5/7] Running Quantum Router...", end='', flush=True)
    stage_start = time.time()
    router = QuantumRouter(
        num_qubits, embeddings, partitioned_gates, [grid_size, grid_size]
    )
    router.run()
    print(f" OK ({time.time() - stage_start:.2f}s)")
    
    # 6. Generate parallel gates for each partition
    print(f"    [Stage 6/7] Grouping parallel gates per partition...", end='', flush=True)
    stage_start = time.time()
    parallel_gate_groups = []
    for i in range(len(partitioned_gates)):
        gates = get_parallel_gates(
            partitioned_gates[i],
            coupling_graph,
            embeddings[i],
            r_int * 2
        )
        parallel_gate_groups.append(gates)
    print(f" OK ({time.time() - stage_start:.2f}s)")
    
    # 7. Convert to instruction format
    timestamp_counter = 1
    
    # Process each partition
    for partition_idx in range(len(embeddings)):
        # Get current embedding (qubit positions)
        current_embedding = embeddings[partition_idx]
        
        # Initial placement for first partition
        if partition_idx == 0:
            instructions.append(f"--- Processing Time {timestamp_counter} ---")
            instructions.append("[INITIAL PLACEMENT]")
            for qubit_idx, pos in enumerate(current_embedding):
                r, c = pos
                instructions.append(f"  PLACE qubit {qubit_idx} at position ({r}, {c})")
            timestamp_counter += 1
        
        # Execute gates for this partition - EACH parallel group is a separate timestep
        for gate_group in parallel_gate_groups[partition_idx]:
            instructions.append(f"--- Processing Time {timestamp_counter} ---")
            instructions.append(f"[EXECUTE Time {timestamp_counter}]")
            for gate in gate_group:
                q1, q2 = gate
                pos1 = current_embedding[q1]
                pos2 = current_embedding[q2]
                instructions.append(f"  CZ q[{q1}], q[{q2}] (at locations {tuple(pos1)}, {tuple(pos2)})")
            timestamp_counter += 1
        
        # Movement to next partition (if not the last partition)
        if partition_idx < len(router.movement_list) and router.movement_list[partition_idx]:
            movements = router.movement_list[partition_idx]
            
            # Process each movement batch (each batch is a separate timestep)
            for move_batch in movements:
                instructions.append(f"--- Processing Time {timestamp_counter} ---")
                instructions.append("[SHUTTLING]")
                for move in move_batch:
                    qubit_id = move[0]
                    from_pos = move[1]
                    to_pos = move[2]
                    instructions.append(f"  SHUTTLE qubit {qubit_id} from {from_pos} to {to_pos}")
                timestamp_counter += 1
    
    # Save to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(instructions))
    
    return True


def compute_realistic_metrics_for_converted_log(
    *,
    instruction_log_path: str,
    num_qubits: int,
    num_cz_gates: int,
    circuit_depth: int,
    r_int: int,
) -> dict[str, Any]:
    with open(instruction_log_path, "r") as f:
        text = f.read()

    params_optimistic = FidelityParams(f_trans=1.0)
    params_realistic = FidelityParams(f_trans=0.999)

    parsed = analyze_converted_instructions(text, d_atom=params_optimistic.d_atom)
    # Prefer the QASM-derived CZ count when available (keeps consistent with other pipelines)
    metrics = _compute_fidelity_from_counts(
        num_qubits=num_qubits,
        num_cz_gates=num_cz_gates,
        num_gate_cycles=int(parsed["Num Gate Cycles"]),
        num_movement_ops=int(parsed["Num Movement Ops"]),
        total_move_distance=float(parsed["Total Move Distance"]),
        num_moves=int(parsed["Num Moves"]),
        params_optimistic=params_optimistic,
        params_realistic=params_realistic,
    )

    return {
        "Circuit Depth": circuit_depth,
        "Num CZ Gates": num_cz_gates,
        "Num Qubit": num_qubits,
        **metrics,
        "r_int": r_int,
    }


def process_all_circuits(
    qasm_folder: str,
    output_dir: str = 'dasatom_instruction_logs',
    *,
    dataset: Optional[str] = None,
    results_csv: Optional[str] = None,
    r_int: int = 2,
    grid_size_override: Optional[int] = None,
    limit: Optional[int] = None,
):
    """
    Process all QASM files in a folder and generate instruction files for each.
    
    Args:
        qasm_folder: Folder containing QASM files
        output_dir: Directory to save instruction files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
    
    qasm_files = sorted([f for f in os.listdir(qasm_folder) if f.endswith('.qasm')], key=natural_sort_key)
    
    if limit:
        qasm_files = qasm_files[:limit]
        print(f"[*] Limiting to first {limit} circuits...")

    if not qasm_files:
        print(f"[!] No QASM files found in {qasm_folder}")
        return
    
    print(f"[*] Found {len(qasm_files)} QASM files to process...\n")
    
    # Decide output path for results CSV
    out_csv = results_csv
    if out_csv is None and dataset:
        results_root = os.path.join("results", f"{dataset}_ladder_rint{r_int}")
        os.makedirs(results_root, exist_ok=True)
        out_csv = os.path.join(results_root, f"dasatom_{dataset}_results.csv")
    
    csv_file = None
    csv_writer = None
    if out_csv:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        csv_file = open(out_csv, "w", newline="")

    success_count = 0
    for qasm_file in qasm_files:
        circuit_name = os.path.splitext(qasm_file)[0]
        qasm_path = os.path.join(qasm_folder, qasm_file)
        output_file = os.path.join(output_dir, f"{circuit_name}_instructions.txt")
        
        print(f"Processing: {circuit_name}...", end=' ', flush=True)
        
        start_time = time.time()
        
        try:
            qasm_circuit = CreateCircuitFromQASM(os.path.basename(qasm_path), os.path.dirname(qasm_path))
            two_qubit_gates_list = get_2q_gates_list(qasm_circuit)
            if not two_qubit_gates_list:
                print("[WARN] Skipped (no CZ)")
                continue

            qc_object, _ = gates_list_to_QC(two_qubit_gates_list)
            num_qubits = get_qubits_num(two_qubit_gates_list)
            num_cz_gates = len(two_qubit_gates_list)
            circuit_depth = qc_object.depth() if hasattr(qc_object, "depth") else 0

            # Skip conversion if file already exists to save time
            if os.path.exists(output_file):
                print("(cached) OK")
                success_count += 1
            elif convert_dasatom_to_instructions(qasm_path, output_file, r_int=r_int, grid_size_override=grid_size_override):
                success_count += 1
                print("OK")
            else:
                print("[WARN] Skipped")
                continue

            metrics = compute_realistic_metrics_for_converted_log(
                instruction_log_path=output_file,
                num_qubits=num_qubits,
                num_cz_gates=num_cz_gates,
                circuit_depth=circuit_depth,
                r_int=r_int,
            )
            
            elapsed_time = time.time() - start_time
            metrics["Elapsed Time (s)"] = elapsed_time
            
            row = {"QASM File": qasm_file, **metrics}
            
            if csv_file:
                if csv_writer is None:
                    csv_writer = csv.DictWriter(csv_file, fieldnames=list(row.keys()))
                    csv_writer.writeheader()
                csv_writer.writerow(row)
                csv_file.flush()
            
            print("OK")
        except Exception as e:
            print(f"[ERROR] {e}")
    
    if csv_file:
        csv_file.close()

    print(f"\n[DONE] Successfully processed {success_count}/{len(qasm_files)} circuits")
    if out_csv:
        print(f"[OK] Metrics CSV saved to '{out_csv}'")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert DasAtom outputs to instruction format")
    parser.add_argument('--qasm-folder', type=str,
                        default='../dasatom/DasAtom-main/Data/qiskit-bench/qft/qft_small',
                        help='Path to folder containing QASM files')
    parser.add_argument('--output-dir', type=str, default='dasatom_instruction_logs',
                        help='Directory to save instruction files')
    parser.add_argument('--dataset', type=str, default=None,
                        help="Optional dataset name (e.g., 'qft' or 'tetris'). If provided, writes a CSV named "
                             "'dasatom_{dataset}_results.csv' under results/{dataset}_ladder_rint{r_int}/")
    parser.add_argument('--results-csv', type=str, default=None,
                        help="Optional explicit path to write the metrics CSV (overrides --dataset default).")
    parser.add_argument('--r-int', type=int, default=2,
                        help='Interaction radius used by DasAtom (default: 2).')
    parser.add_argument('--grid-size-override', type=int, default=None,
                        help='Optional manual grid size override (e.g., 12 for 12x12).')
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum number of circuits to process.')
    
    args = parser.parse_args()
    
    print("="*70)
    print("  DASATOM INSTRUCTION CONVERTER")
    print("="*70 + "\n")
    
    process_all_circuits(
        args.qasm_folder,
        args.output_dir,
        dataset=args.dataset,
        results_csv=args.results_csv,
        r_int=args.r_int,
        grid_size_override=args.grid_size_override,
        limit=args.limit,
    )
