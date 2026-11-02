# compiler_core.py (UPGRADED: Intelligent Planner Version)

import bisect
import math
import os
import random
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Optional

import networkx as nx
import numpy as np
from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from scipy.optimize import linear_sum_assignment


class AssignmentMode(str, Enum):
    HUNGARIAN = "hungarian"
    RANDOM = "random"


class IdleParkingMode(str, Enum):
    RFT_GREEDY = "rft_greedy"           # current behavior
    GREEDY_NEAREST = "greedy_nearest"   # ignore RFT, park nearest empty
    RANDOM = "random"                  # random empty spot


class CandidateSlotsMode(str, Enum):
    COM_SUBSET = "com_subset"           # current behavior: take len(movers) nearest to CoM
    ALL_COMPATIBLE = "all_compatible"   # use all compatible static slots


@dataclass(frozen=True)
class CompilerOptions:
    variant_name: str = "unnamed"

    # Dynamic layout features
    enable_keep_adjacent: bool = True
    enable_one_qubit_move: bool = True

    # Movers assignment features
    candidate_slots_mode: CandidateSlotsMode = CandidateSlotsMode.COM_SUBSET
    pad_cost_matrix_to_square: bool = False  # legacy toggle; scipy supports rectangular
    assignment_mode: AssignmentMode = AssignmentMode.HUNGARIAN

    # Idle parking features
    idle_parking_mode: IdleParkingMode = IdleParkingMode.RFT_GREEDY

    # RFT idle parking heuristic toggle (evicted qubits only)
    # False: legacy: minimize dist(current->spot) + dist(spot->partner_pos)
    # True : new: park closest to partner_pos (static qubit)
    evicted_park_closest_to_partner: bool = False

    # RFT future-biased Hungarian assignment (movers)
    # When enabled, the Hungarian cost includes an extra term that pulls each qubit
    # toward the position of its nearest (in time) future partner from the RFT.
    enable_rft_hungarian_bias: bool = False
    rft_hungarian_bias_weight: float = 0.3
    rft_hungarian_bias_max_time_dist: int = 3

    # Randomness control (used when assignment_mode or idle_parking_mode is RANDOM)
    random_seed: int = 42


def _pick_idle_position(
    *,
    qubit: int,
    available_positions: list,
    current_qubit_positions: dict,
    final_target_positions: dict,
    center_of_mass,
    current_future_partners: dict,
    options: CompilerOptions,
    rng: random.Random,
    max_partner_dist: int,
    is_evicted: bool,
):
    if not available_positions:
        return None

    if options.idle_parking_mode == IdleParkingMode.RANDOM:
        return rng.choice(available_positions)

    if options.idle_parking_mode == IdleParkingMode.GREEDY_NEAREST:
        cur = current_qubit_positions.get(qubit, center_of_mass)
        return min(available_positions, key=lambda p: euclid_dist(p, cur))

    # Default: RFT_GREEDY (current behavior)
    future_partners = current_future_partners.get(qubit, [])
    if future_partners:
        partner, dist = sorted(future_partners, key=lambda x: x[1])[0]
        if partner in final_target_positions and dist <= max_partner_dist:
            partner_pos = final_target_positions[partner]

            if is_evicted and options.evicted_park_closest_to_partner:
                return min(available_positions, key=lambda spot: euclid_dist(spot, partner_pos))

            cur = current_qubit_positions.get(qubit, center_of_mass)
            return min(
                available_positions,
                key=lambda spot: euclid_dist(cur, spot) + euclid_dist(spot, partner_pos),
            )

    return min(available_positions, key=lambda p: euclid_dist(p, center_of_mass))

# Sparse schedule type: list of (timestamp_name, list_of_(q1,q2)_edges).
# Replaces the previous all-pairs Pandas DataFrame; only the edges that actually
# fire are stored, which makes the data structure tractable for thousands of qubits.
def analyze_qasm_file(qasm_file_path: str):
    """Returns (None, schedule, num_qubits).

    schedule is a list of (timestamp_name, edges) where edges is the list of
    (q_min, q_max) two-qubit-gate pairs firing at that DAG layer. The legacy
    3-tuple shape is preserved so callers unpacking `(_, ts, n)` keep working;
    the middle element is the schedule list instead of a Pandas DataFrame.
    """
    try:
        circuit = QuantumCircuit.from_qasm_file(qasm_file_path)
    except Exception:
        return None, None, 0
    num_qubits = circuit.num_qubits
    if num_qubits < 2:
        return None, [], num_qubits

    schedule = []
    dag = circuit_to_dag(circuit)
    for time_step, layer in enumerate(dag.layers()):
        op_nodes = layer['graph'].op_nodes()
        if not op_nodes:
            continue
        edges = []
        for op_node in op_nodes:
            try:
                gate_qubits = [circuit.find_bit(q).index for q in op_node.qargs]
            except Exception:
                gate_qubits = [q.index for q in op_node.qargs]
            if len(gate_qubits) > 1:
                for q1, q2 in combinations(gate_qubits, 2):
                    edges.append((min(q1, q2), max(q1, q2)))
        # Sort lexicographically so downstream sees pairs in the same order the
        # legacy Pandas DataFrame did (its index was sorted (q_min, q_max)).
        edges.sort()
        schedule.append((f"Time {time_step + 1}", edges))
    return None, schedule, num_qubits

def euclid_dist(p1, p2): return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def sample_max_parallel(R, C, r_int, r_blk, m=1000):
    """
    Generates a single optimized layout using random sampling. Returns the
    best (largest slot count) configuration found across m samples.

    The blockade check is vectorized with NumPy: occupied positions are kept
    in a pre-allocated array and each new candidate slot is rejected/accepted
    based on a single broadcasted squared-distance compare against all
    currently-occupied positions. Squared distances avoid the O(N) Python
    `math.sqrt` calls that dominated the pre-vectorization profile.
    """
    random.seed(42)  # Ensure determinism

    r_blk_sq = r_blk * r_blk
    grid_capacity = R * C
    best_num, best_slots = 0, []

    for _ in range(m):
        occupied_set = set()
        # Pre-allocated arrays for vectorized distance checks
        occupied_arr = np.empty((grid_capacity, 2), dtype=np.float64)
        n_occupied = 0
        current_slots = []

        all_starts = [(r, c) for r in range(R) for c in range(C)]
        random.shuffle(all_starts)

        for p1 in all_starts:
            if p1 in occupied_set:
                continue
            candidates_p2 = [p for p in get_neighbors(p1, R, C, r_int) if p not in occupied_set]
            if not candidates_p2:
                continue
            p2 = random.choice(candidates_p2)

            if n_occupied > 0:
                occ_view = occupied_arr[:n_occupied]
                # Squared distance from p1 to every occupied position
                dx = occ_view[:, 0] - p1[0]
                dy = occ_view[:, 1] - p1[1]
                if np.any(dx * dx + dy * dy < r_blk_sq):
                    continue
                # Same check for p2
                dx = occ_view[:, 0] - p2[0]
                dy = occ_view[:, 1] - p2[1]
                if np.any(dx * dx + dy * dy < r_blk_sq):
                    continue

            current_slots.append([p1, p2])
            occupied_set.add(p1); occupied_set.add(p2)
            occupied_arr[n_occupied] = p1; n_occupied += 1
            occupied_arr[n_occupied] = p2; n_occupied += 1

        if len(current_slots) > best_num:
            best_num, best_slots = len(current_slots), current_slots.copy()

    return best_num, best_slots

def find_busiest_pairs(schedule):
    """Return the edge list of the timestep that has the most two-qubit gates.

    Replaces the legacy find_busiest_timestamp which also returned a timestamp
    name that no caller used.
    """
    if not schedule:
        return []
    return max((edges for _, edges in schedule), key=len, default=[])

def create_initial_mapping(busiest_timestamp_pairs, physical_layout):
    return {pair: physical_layout[i] for i, pair in enumerate(busiest_timestamp_pairs) if i < len(physical_layout)}

def is_slot_compatible(slot_A, slot_B, r_blk):
    """
    Checks if two slots (edges) can be active simultaneously without violating r_blk.
    slot_A = (p1, p2), slot_B = (p3, p4)
    """
    p1, p2 = slot_A
    p3, p4 = slot_B
    
    # Check all 4 cross-distances
    if euclid_dist(p1, p3) < r_blk: return False
    if euclid_dist(p1, p4) < r_blk: return False
    if euclid_dist(p2, p3) < r_blk: return False
    if euclid_dist(p2, p4) < r_blk: return False
    return True

def get_neighbors(pos, R, C, r_int=1):
    """
    Returns all valid neighboring grid positions within Euclidean radius r_int.
    Default r_int=1 preserves previous orthogonal-one-step behavior when r_int==1.
    """
    r, c = pos
    neighbors = []
    r_bound = int(math.floor(r_int))
    for dr in range(-r_bound, r_bound + 1):
        for dc in range(-r_bound, r_bound + 1):
            nr, nc = r + dr, c + dc
            if (nr, nc) == pos:
                continue
            if 0 <= nr < R and 0 <= nc < C:
                if euclid_dist(pos, (nr, nc)) <= r_int + 1e-9:
                    neighbors.append((nr, nc))
    return neighbors

def build_right_filled_table(schedule, num_qubits):
    """Per-qubit future-partners view: {timestamp_name: {qubit: [(partner, distance)]}}.

    `distance` is the number of timesteps from the current timestep to the
    *next* timestep at which qubit and partner share a CZ gate (0 means "right
    now"). Built directly from the sparse schedule -- iterates only the edges
    that fire, never materializing the all-pairs cross product. For a
    3-regular graph this is O(|E|*T) work instead of the previous O(n^2*T).
    """
    timestamp_names = [name for name, _ in schedule]

    # For each pair that ever fires, collect the (chronologically sorted)
    # timestep indices at which it fires.
    pair_gate_times = {}
    for ts_idx, (_, edges) in enumerate(schedule):
        for q1, q2 in edges:
            pair_gate_times.setdefault((q1, q2), []).append(ts_idx)

    qubit_view = {name: {q: [] for q in range(num_qubits)} for name in timestamp_names}

    for (q1, q2), gate_times in pair_gate_times.items():
        for ts_idx, name in enumerate(timestamp_names):
            i = bisect.bisect_left(gate_times, ts_idx)
            if i < len(gate_times):
                distance = gate_times[i] - ts_idx
                qubit_view[name][q1].append((q2, distance))
                qubit_view[name][q2].append((q1, distance))

    return qubit_view

def generate_safe_shuttle_instructions(current_positions, target_positions, R, C):
    """
    Refactored version using networkx Independent Sets for parallel batching.
    Moves qubits in parallel batches where 2D dependencies don't conflict.
    """
    
    def compatible_2D(move_a, move_b):
        a = list(move_a); b = list(move_b)
        if a[0] == b[0] and a[2] != b[2]: return False
        if a[2] == b[2] and a[0] != b[0]: return False
        if a[0] < b[0] and a[2] >= b[2]: return False
        if a[0] > b[0] and a[2] <= b[2]: return False
        if a[1] == b[1] and a[3] != b[3]: return False
        if a[3] == b[3] and a[1] != b[1]: return False
        if a[1] < b[1] and a[3] >= b[3]: return False
        if a[1] > b[1] and a[3] <= b[3]: return False
        return True

    instructions = []
    sim_positions = current_positions.copy()
    pos_to_qubit = {v: k for k, v in sim_positions.items()}
    moves_todo = {q: t for q, t in target_positions.items() if sim_positions.get(q) != t}
    all_grid_pos = set((r, c) for r in range(R) for c in range(C))
    
    batch_count = 0
    while moves_todo:
        # Phase 1: Clear moves (target is an empty spot)
        clear_moves = {q: t for q, t in moves_todo.items() if t not in pos_to_qubit}
        
        if clear_moves:
            qubit_list = list(clear_moves.keys())
            move_dict = {q: (sim_positions[q][0], sim_positions[q][1], clear_moves[q][0], clear_moves[q][1]) for q in qubit_list}
            
            conflict_graph = nx.Graph()
            conflict_graph.add_nodes_from(qubit_list)
            for i, q1 in enumerate(qubit_list):
                for q2 in qubit_list[i+1:]:
                    if not compatible_2D(move_dict[q1], move_dict[q2]):
                        conflict_graph.add_edge(q1, q2)
            
            independent_set = nx.maximal_independent_set(conflict_graph) if conflict_graph else []
            
            if independent_set:
                batch_count += 1
                if batch_count > 1:
                    instructions.append("--- Batch Separator ---")
                instructions.append(f"[SHUTTLING] Batch {batch_count}")
                for qubit in independent_set:
                    start_pos = sim_positions[qubit]
                    target_pos = clear_moves[qubit]
                    instructions.append(f"  SHUTTLE qubit {qubit} from {start_pos} to {target_pos}")
                    # Update state
                    sim_positions[qubit] = target_pos
                    pos_to_qubit.pop(start_pos, None)
                    pos_to_qubit[target_pos] = qubit
                    moves_todo.pop(qubit)
                continue
                
        # Phase 2: Break cycles using temporary empty spots
        if moves_todo:
            available_temp_spots = all_grid_pos - set(pos_to_qubit.keys())
            if not available_temp_spots:
                instructions.append("  ERROR: No free temporary spot to break movement cycle!")
                break
            
            q_to_break = next(iter(moves_todo.keys()))
            start_pos = sim_positions[q_to_break]
            
            # Smart temporary parking: Pick the absolute CLOSEST available spot to minimize detour distance!
            temp_pos = min(available_temp_spots, key=lambda p: (start_pos[0] - p[0])**2 + (start_pos[1] - p[1])**2)
            
            batch_count += 1
            if batch_count > 1:
                instructions.append("--- Batch Separator ---")
            instructions.append(f"[SHUTTLING] Batch {batch_count}")
            instructions.append(f"  SHUTTLE qubit {q_to_break} from {start_pos} to {temp_pos} (to break cycle)")
            sim_positions[q_to_break] = temp_pos
            pos_to_qubit.pop(start_pos, None)
            pos_to_qubit[temp_pos] = q_to_break
            
    return instructions



class GridCapacityError(Exception):
    """Raised when the grid physical layout cannot support the circuit's parallel gate demand."""
    pass

# --- THIS IS THE FULLY UPGRADED, STATE-OF-THE-ART COMPILER LOGIC ---
def generate_hardware_instructions(
    schedule,
    canonical_mapping,
    busiest_pairs,
    num_qubits,
    R,
    C,
    physical_layout,
    r_blk,
    r_int = 1,
    options: Optional[CompilerOptions] = None,
):
    """
    Dynamic Active-First Strategy:
    - Tries to keep adjacent pairs in place if blockade-compatible
    - Falls back to static layout for pairs that need movement
    - Has full-revert fallback if dynamic slots block the grid

    `schedule` is a list of (timestamp_name, edges) produced by
    analyze_qasm_file -- each entry is one DAG layer with its list of
    two-qubit (q_min, q_max) pairs.
    """
    hardware_instructions = []
    current_qubit_positions = {}
    is_first_placement = True

    options = options or CompilerOptions()
    rng = random.Random(options.random_seed)

    # Pre-compute right-filled table for smart idle parking (only if enabled)
    right_filled_table = None
    if options.idle_parking_mode == IdleParkingMode.RFT_GREEDY or options.enable_rft_hungarian_bias:
        right_filled_table = build_right_filled_table(schedule, num_qubits)

    for timestamp_name, original_active_pairs in schedule:
        # Get right-filled info for this timestamp
        current_future_partners = right_filled_table.get(timestamp_name, {}) if right_filled_table else {}

        if not original_active_pairs:
            instructions_for_this_step = [f"--- Processing {timestamp_name} ---", "No two-qubit 'C' gates in this timestamp. Skipping."]
            hardware_instructions.append("\n".join(instructions_for_this_step))
            continue

        # --- SERIALIZATION LOOP ---
        # If the grid cannot handle all pairs at once, split them into serial batches.
        pending_pairs = list(original_active_pairs)
        sub_step_index = 0
        
        while pending_pairs:
            sub_step_index += 1
            instructions_for_this_step = [f"--- Processing {timestamp_name} (Batch {sub_step_index}) ---"]
            
            # We try to map ALL pending pairs. If we run out of space, the logic below will truncate.
            active_pairs_to_map = list(pending_pairs)
            num_active_pairs_to_map = len(active_pairs_to_map)
            
            final_target_positions = {}
            active_qubit_targets = {}

            # --- PHASE 1: WISHLIST GENERATION ---
            # Priority 0: Already adjacent (stay put)
            # Priority 1: Can become adjacent with 1-qubit move
            wishlist_slots = []  # (priority, slot_coords, pair_index, move_dict)
            
            occupied_positions = set(current_qubit_positions.values())
            
            for i, (q1, q2) in enumerate(active_pairs_to_map):
                p1 = current_qubit_positions.get(q1)
                p2 = current_qubit_positions.get(q2)
                
                if not p1 or not p2:
                    continue  # Should not happen if initialization is correct

                dist = euclid_dist(p1, p2)
                
                # Priority 0: Already Adjacent (Stay Put)
                if options.enable_keep_adjacent and dist <= r_int + 1e-6:
                    wishlist_slots.append((0, (p1, p2), i, {}))
                    continue
                
                # Priority 1: Try to move ONE qubit to an empty neighbor of the other
                if not options.enable_one_qubit_move:
                    continue
                
                neighbors_p2 = [n for n in get_neighbors(p2, R, C, r_int) if n not in occupied_positions]
                neighbors_p1 = [n for n in get_neighbors(p1, R, C, r_int) if n not in occupied_positions]
                
                # Option A: Move q1 -> neighbor of p2
                if neighbors_p2:
                    best_n = min(neighbors_p2, key=lambda n: euclid_dist(n, p1))
                    slot = (best_n, p2)
                    wishlist_slots.append((1, slot, i, {q1: best_n}))
                    continue # Found a move, skip Option B
                
                # Option B: Move q2 -> neighbor of p1
                if neighbors_p1:
                    best_n = min(neighbors_p1, key=lambda n: euclid_dist(n, p2))
                    slot = (p1, best_n)
                    wishlist_slots.append((1, slot, i, {q2: best_n}))
            
            # --- PHASE 2: GREEDY VALIDATION ---
            # Sort by priority: 0 (Stay) -> 1 (Move 1 qubit)
            wishlist_slots.sort(key=lambda x: x[0])
            
            accepted_dynamic_slots = []
            accepted_pair_local_indices = set()
            claimed_empty_spots = set()
            accepted_moves = {}  # local_idx -> move_dict
            
            for priority, slot, idx, move_dict in wishlist_slots:
                # Check 1: Collision
                collision = False
                for target_pos in move_dict.values():
                    if target_pos in claimed_empty_spots:
                        collision = True; break
                if collision: continue

                # Check 2: Blockade Compatibility
                is_compatible = True
                for existing_slot in accepted_dynamic_slots:
                    if not is_slot_compatible(slot, existing_slot, r_blk):
                        is_compatible = False; break
                
                if is_compatible:
                    accepted_dynamic_slots.append(slot)
                    accepted_pair_local_indices.add(idx)
                    accepted_moves[idx] = move_dict
                    for target_pos in move_dict.values():
                        claimed_empty_spots.add(target_pos)
            
            # Identify leftover pairs that need movement/fallback
            leftover_local_indices = [i for i in range(num_active_pairs_to_map) if i not in accepted_pair_local_indices]

            # --- PHASE 3: FILLING THE GAPS (Hybrid with Static Layout) ---
            compatible_static_slots = []
            
            # Filter static layout against accepted dynamic slots
            for static_slot in physical_layout:
                is_compatible = True
                for dyn_slot in accepted_dynamic_slots:
                    if not is_slot_compatible(tuple(static_slot), dyn_slot, r_blk):
                        is_compatible = False; break
                if is_compatible:
                    compatible_static_slots.append(static_slot)
            
            # Check capacity for leftover pairs
            # If we don't have enough static slots, we must DEFER the excess pairs to the next batch.
            num_slots_available = len(compatible_static_slots)
            num_leftover_pairs = len(leftover_local_indices)
            
            pairs_to_assign_now_indices = leftover_local_indices # Default: try all
            
            if num_slots_available < num_leftover_pairs:
                # Truncate!
                pairs_to_assign_now_indices = leftover_local_indices[:num_slots_available]
                # The rest remain in 'pending_pairs' effectively because we won't mark them as done
            
            # If dynamic slots "blocked the grid" significantly but we still have capacity issues?
            # Actually, accepted_dynamic_slots are already 'in'.
            # We only care about fitting the rest.
            
            # --- PHASE 4: ASSIGNMENT ---
            # A. Assign accepted dynamic pairs
            finished_batch_indices = list(accepted_pair_local_indices) + list(pairs_to_assign_now_indices)
            
            for idx in accepted_pair_local_indices:
                q1, q2 = active_pairs_to_map[idx]
                move_dict = accepted_moves.get(idx, {})
                active_qubit_targets[q1] = move_dict.get(q1, current_qubit_positions[q1])
                active_qubit_targets[q2] = move_dict.get(q2, current_qubit_positions[q2])

            # B. Assign movers (Hungarian) for the subset that fits
            if pairs_to_assign_now_indices:
                movers = [active_pairs_to_map[i] for i in pairs_to_assign_now_indices]
                
                # Recalculate CoM for JUST these movers
                mover_qubits = [q for pair in movers for q in pair]
                if mover_qubits and current_qubit_positions:
                    avg_r = sum(current_qubit_positions.get(q, (R/2, C/2))[0] for q in mover_qubits) / len(mover_qubits)
                    avg_c = sum(current_qubit_positions.get(q, (R/2, C/2))[1] for q in mover_qubits) / len(mover_qubits)
                    center_of_mass = (avg_r, avg_c)
                else:
                    center_of_mass = (R/2, C/2)
                
                # Select best candidate slots
                if options.candidate_slots_mode == CandidateSlotsMode.ALL_COMPATIBLE:
                    candidate_slots = list(compatible_static_slots)
                else:
                    candidate_slots = sorted(
                        compatible_static_slots,
                        key=lambda s: euclid_dist(s[0], center_of_mass) + euclid_dist(s[1], center_of_mass),
                    )[: len(movers)] # Take best N slots

                if options.assignment_mode == AssignmentMode.RANDOM:
                    if len(candidate_slots) < len(movers): candidate_slots = list(compatible_static_slots)
                    rng.shuffle(candidate_slots)
                    chosen_slots = candidate_slots[: len(movers)]
                    for (q1, q2), (s1, s2) in zip(movers, chosen_slots):
                        # ... (Assignment logic same as before, simplified copy for brevity) ...
                        # For random, we just pick random order
                        active_qubit_targets[q1], active_qubit_targets[q2] = tuple(s1), tuple(s2) # (Assume s1,s2 format ok)
                else:
                    # Hungarian — vectorized cost matrix construction.
                    # Per (mover i, slot j):
                    #   cost_A = ||p1_i - s1_j|| + ||p2_i - s2_j||  (orientation A)
                    #   cost_B = ||p1_i - s2_j|| + ||p2_i - s1_j||  (orientation B, swapped)
                    #   cost[i,j] = min(cost_A, cost_B)
                    # With RFT bias, future-partner distance terms are added per orientation.

                    def _future_anchor(q: int):
                        if not options.enable_rft_hungarian_bias or options.rft_hungarian_bias_weight <= 0: return None, 0.0
                        partners = current_future_partners.get(q, [])
                        if not partners: return None, 0.0
                        partner, time_dist = sorted(partners, key=lambda x: x[1])[0]
                        if time_dist > options.rft_hungarian_bias_max_time_dist: return None, 0.0
                        partner_pos = active_qubit_targets.get(partner) or current_qubit_positions.get(partner)
                        if partner_pos is None: return None, 0.0
                        return partner_pos, (1.0 / (time_dist + 1))

                    fallback_pos = (R / 2, C / 2)
                    P1 = np.array([current_qubit_positions.get(q1, fallback_pos) for q1, _ in movers], dtype=float)
                    P2 = np.array([current_qubit_positions.get(q2, fallback_pos) for _, q2 in movers], dtype=float)
                    S1 = np.array([s[0] for s in candidate_slots], dtype=float)
                    S2 = np.array([s[1] for s in candidate_slots], dtype=float)

                    def _pairwise_dist(A, B):
                        diff = A[:, None, :] - B[None, :, :]
                        return np.sqrt(np.einsum('ijk,ijk->ij', diff, diff))

                    cost_A = _pairwise_dist(P1, S1) + _pairwise_dist(P2, S2)
                    cost_B = _pairwise_dist(P1, S2) + _pairwise_dist(P2, S1)

                    if options.enable_rft_hungarian_bias and options.rft_hungarian_bias_weight > 0:
                        # Per-mover anchors (zeros + W=0 means "no contribution")
                        M = len(movers)
                        A1 = np.zeros((M, 2), dtype=float)
                        A2 = np.zeros((M, 2), dtype=float)
                        W1 = np.zeros(M, dtype=float)
                        W2 = np.zeros(M, dtype=float)
                        for i_m, (q1, q2) in enumerate(movers):
                            anc1, w1 = _future_anchor(q1)
                            anc2, w2 = _future_anchor(q2)
                            if anc1 is not None:
                                A1[i_m] = anc1; W1[i_m] = w1
                            if anc2 is not None:
                                A2[i_m] = anc2; W2[i_m] = w2

                        # Distance from each slot's s_k to per-mover anchor
                        d_s1_a1 = _pairwise_dist(A1, S1)
                        d_s2_a2 = _pairwise_dist(A2, S2)
                        d_s2_a1 = _pairwise_dist(A1, S2)
                        d_s1_a2 = _pairwise_dist(A2, S1)

                        future_A = d_s1_a1 * W1[:, None] + d_s2_a2 * W2[:, None]
                        future_B = d_s2_a1 * W1[:, None] + d_s1_a2 * W2[:, None]
                        cost_A = cost_A + options.rft_hungarian_bias_weight * future_A
                        cost_B = cost_B + options.rft_hungarian_bias_weight * future_B

                    cost_matrix = np.minimum(cost_A, cost_B)

                    row_ind, col_ind = linear_sum_assignment(cost_matrix)
                    for r, c in zip(row_ind, col_ind):
                        q1, q2 = movers[r]
                        s1, s2 = candidate_slots[c]
                        # Simple dist check to decide orientation (re-calculating for simplicity)
                        curr_p1 = current_qubit_positions.get(q1, (R/2, C/2))
                        dist_A = euclid_dist(curr_p1, s1)
                        dist_B = euclid_dist(curr_p1, s2)
                        if dist_A <= dist_B:
                            active_qubit_targets[q1], active_qubit_targets[q2] = tuple(s1), tuple(s2)
                        else:
                            active_qubit_targets[q1], active_qubit_targets[q2] = tuple(s2), tuple(s1)

            # --- FINALIZE STEP ---
            final_target_positions.update(active_qubit_targets)
            
            # Idle placement logic (same as before, but only for qubits NOT active in this batch)
            # Important: Qubits that are 'pending' for next batch are technically idle NOW.
            # But we shouldn't move them aggressively if they are about to act.
            # For simplicity, we keep the original logic: anyone not in active_qubit_targets is 'idle'.
            
            if is_first_placement and sub_step_index == 1:
                instructions_for_this_step.append("[INITIAL PLACEMENT]")
                # We only place the ones active in this first batch?
                # No, we should probably place everyone initially if possible.
                # But 'generate_hardware_instructions' assumes incremental updates.
                
                # Fix: If it's the very first batch of the very first timestamp, place ALL qubits.
                # If we split batches, subsequent batches are just [SHUTTLING].
                
                # Check unplaced qubits
                unplaced_qubits = set(range(num_qubits)) - set(final_target_positions.keys())
                available_positions = list(set((r, c) for r in range(R) for c in range(C)) - set(final_target_positions.values()))
                
                # If this is really the first ever placement, we place active ones first (done above), then fill rest.
                # The logic handles this via 'active_qubit_targets' being set.
                
                # Place remaining idle qubits (including those pending for later batches)
                for qubit in unplaced_qubits:
                    if not available_positions: break
                    best_pos = _pick_idle_position(
                        qubit=qubit,
                        available_positions=available_positions,
                        current_qubit_positions=current_qubit_positions,
                        final_target_positions=final_target_positions,
                        center_of_mass=center_of_mass, # specific to batch? use global?
                        current_future_partners=current_future_partners,
                        options=options,
                        rng=rng,
                        max_partner_dist=3,
                        is_evicted=False
                    )
                    if best_pos:
                        final_target_positions[qubit] = best_pos
                        available_positions.remove(best_pos)
                        instructions_for_this_step.append(f"  PLACE idle qubit {qubit} at position {best_pos}")
                
                for q, pos in final_target_positions.items():
                    if q in active_qubit_targets: # It was "placed" logic above, just ensuring instruction
                        instructions_for_this_step.append(f"  PLACE active qubit {q} at position {pos}")
                
                is_first_placement = False
            
            else:
                # [SHUTTLING] will be appended inside generate_safe_shuttle_instructions
                
                # Determine idle qubits (everyone not acting in this batch)
                idle_qubits = set(range(num_qubits)) - set(active_qubit_targets.keys())
                evicted_qubits = set()
                for q in idle_qubits:
                    current_pos = current_qubit_positions[q]
                    if current_pos in active_qubit_targets.values():
                        evicted_qubits.add(q)
                    else:
                        final_target_positions[q] = current_pos # Stay put
                
                # Park evicted
                if evicted_qubits:
                    all_grid_pos = set((r, c) for r in range(R) for c in range(C))
                    available_parking_spots = list(all_grid_pos - set(final_target_positions.values()))
                    
                    if len(available_parking_spots) < len(evicted_qubits):
                        instructions_for_this_step.append("  ERROR: Not enough free space for evicted qubits!")
                        # This causes a crash downstream usually, but let's persist
                    else:
                        for qubit in evicted_qubits:
                            best_spot = _pick_idle_position(
                                qubit=qubit,
                                available_positions=available_parking_spots,
                                current_qubit_positions=current_qubit_positions,
                                final_target_positions=final_target_positions,
                                center_of_mass=center_of_mass,
                                current_future_partners=current_future_partners,
                                options=options,
                                rng=rng,
                                max_partner_dist=2,
                                is_evicted=True
                            )
                            if best_spot:
                                final_target_positions[qubit] = best_spot
                                available_parking_spots.remove(best_spot)

                shuttle_instructions = generate_safe_shuttle_instructions(current_qubit_positions, final_target_positions, R, C)
                if not shuttle_instructions:
                    instructions_for_this_step.append("  No shuttling required.")
                else:
                    instructions_for_this_step.extend(shuttle_instructions)

            current_qubit_positions = final_target_positions
            
            # Execute the pairs for this batch
            executed_pairs = [active_pairs_to_map[i] for i in finished_batch_indices]
            instructions_for_this_step.append(f"[EXECUTE {timestamp_name} Batch {sub_step_index}]")
            for pair in executed_pairs:
                instructions_for_this_step.append(f"  CZ q[{pair[0]}], q[{pair[1]}] (at locations {current_qubit_positions.get(pair[0])}, {current_qubit_positions.get(pair[1])})")
            
            hardware_instructions.append("\n".join(instructions_for_this_step))
            
            # Remove executed pairs from pending
            # Note: active_pairs_to_map was a copy of pending_pairs at start of loop
            # We identified finished_batch_indices relative to active_pairs_to_map
            # So we can construct the new pending list
            
            finished_pair_set = set(tuple(active_pairs_to_map[i]) for i in finished_batch_indices)
            pending_pairs = [p for p in pending_pairs if tuple(p) not in finished_pair_set]
            
            if not finished_pair_set and pending_pairs:
                # STUCK CHECK: If we didn't execute *any* pairs but still have pending, we are in an infinite loop
                # (e.g. grid capacity is 0 or logic failed). Break to avoid hang.
                hardware_instructions.append("  CRITICAL ERROR: No pairs could be scheduled in this batch (Grid Full?). Aborting timestamp.")
                break

    return hardware_instructions

    return hardware_instructions
