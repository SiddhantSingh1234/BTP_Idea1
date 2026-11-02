"""Oriented physical predictors over one immutable placement/commitment snapshot."""
from dataclasses import dataclass
from copy import deepcopy
import json
import math
from pathlib import Path
import time
from implementation.lookahead.potential import FuturePotential
from implementation.movement_error.physics import local_batch_cost
from implementation.validation.checker import line_compatible
from implementation.assignment.matching import solve

SCHEMA = 'assignment_options.phase05.v1'
TERMS = ('distance', 'conflict', 'transfer', 'heating', 'future')


def validate_options(value):
    config = deepcopy(value)
    keys = {'schema_version', 'variant_id', 'mode', 'metric', 'objective', 'candidate_policy',
            'expansion_factor', 'weights', 'normalizers', 'include_displacements'}
    if set(config) != keys or config['schema_version'] != SCHEMA:
        raise ValueError('Unknown/missing assignment options')
    if not isinstance(config['variant_id'], str) or not config['variant_id']:
        raise ValueError('Missing assignment identity')
    if config['mode'] not in ('phase04_passthrough', 'oriented'):
        raise ValueError('Unknown integration mode')
    if config['metric'] not in ('pair_distance', 'max_distance', 'move_time', 'composite'):
        raise ValueError('Unknown oriented metric')
    if config['objective'] not in ('sum', 'bottleneck_sum'):
        raise ValueError('Unknown assignment objective')
    if config['candidate_policy'] not in ('com', 'expanded', 'all'):
        raise ValueError('Unknown candidate policy')
    if type(config['expansion_factor']) is not int or config['expansion_factor'] < 1:
        raise ValueError('Invalid expansion factor')
    if type(config['include_displacements']) is not bool:
        raise ValueError('Displacement estimate must be explicitly enabled/disabled')
    if set(config['weights']) != set(TERMS) or set(config['normalizers']) != {'distance_um', 'conflict', 'transfer_events', 'error_E'}:
        raise ValueError('Weights/normalizers incomplete')
    for value in config['weights'].values():
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('Invalid weight')
    for value in config['normalizers'].values():
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('Invalid normalizer')
    return config


def load_options(path):
    return validate_options(json.loads(Path(path).read_text(encoding='utf-8')))


def compatible_slots(a, b, radius):
    return all(math.dist(x, y) >= radius - 1e-9 for x in a for y in b)


def slot_legal(slot, committed, committed_slots, geometry):
    if len(slot) != 2 or slot[0] == slot[1]:
        return False
    for site in slot:
        if len(site) != 2 or any(type(x) is not int for x in site):
            return False
        if not (0 <= site[0] < geometry['rows'] and 0 <= site[1] < geometry['columns']):
            return False
        if site in committed.values():
            return False
    return math.dist(*slot) <= geometry['r_int'] + 1e-9 and all(
        compatible_slots(slot, other, geometry['r_blk']) for other in committed_slots)


def candidates(slots, center, m, config):
    # Stable original order resolves equal CoM distances, as in the source.
    ordered = sorted(slots, key=lambda s: math.dist(s[0], center) + math.dist(s[1], center))
    if config['candidate_policy'] == 'all':
        return list(slots)
    count = m if config['candidate_policy'] == 'com' else config['expansion_factor'] * m
    return ordered[:count]


@dataclass(frozen=True)
class Problem:
    pairs: tuple
    slots: tuple
    oriented_costs: tuple
    details: tuple
    committed_moves: tuple
    build_seconds: float

    @property
    def costs(self):
        return tuple(tuple(min(entry) for entry in row) for row in self.oriented_costs)


def make_problem(pairs, slots, current, committed, committed_slots, geometry, *,
                 index, layer, completed, active, n_by_qubit, profile, lookahead, config):
    started = time.perf_counter()
    config = validate_options(config)
    pairs = tuple(tuple(pair) for pair in pairs)
    slots = tuple(tuple(tuple(site) for site in slot) for slot in slots)
    current = {q: tuple(site) for q, site in current.items()}
    committed = {q: tuple(site) for q, site in committed.items()}
    if len({q for pair in pairs for q in pair}) != 2 * len(pairs):
        raise ValueError('Assignment rows must be disjoint pairs')
    if len(set(slots)) != len(slots):
        raise ValueError('Duplicate candidate slots')
    for i, slot in enumerate(slots):
        for other in slots[i + 1:]:
            if not compatible_slots(slot, other, geometry['r_blk']):
                raise ValueError('Candidate columns must be mutually safe slots')
    snapshot = {**current, **committed}
    fixed = tuple((q, current[q], dest) for q, dest in sorted(committed.items())
                  if q in current and current[q] != dest)
    spacing = geometry['spacing_um']
    normal = config['normalizers']
    potentials = {}
    for pair in pairs:
        for q in pair:
            events = index.query(q, layer, lookahead['h'], completed=completed, active=active)
            potentials[q] = FuturePotential.from_events(events, snapshot,
                gamma=lookahead['gamma'], spacing_um=spacing)
    active_qubits = {q for pair in pairs for q in pair} | set(committed)
    occupancy = {site: q for q, site in current.items()}
    matrix, detail_rows = [], []
    for pair in pairs:
        cost_row, detail_row = [], []
        for slot in slots:
            entry, detail_entry = [], []
            for orientation in (0, 1):
                targets = slot if orientation == 0 else slot[::-1]
                legal = slot_legal(slot, committed, committed_slots, geometry)
                if not legal:
                    entry.append(math.inf)
                    detail_entry.append({'legal': False})
                    continue
                # Unplaced endpoints incur no physical movement. The source's
                # center fallback is used only by pure-distance controls.
                virtual = (geometry['rows'] / 2, geometry['columns'] / 2)
                score_distances = [math.dist(current.get(q, virtual), dest) * spacing for q, dest in zip(pair, targets)]
                distances = {q: math.dist(current[q], dest) * spacing if q in current else 0.
                             for q, dest in zip(pair, targets)}
                moves = [(q, current[q], dest) for q, dest in zip(pair, targets)
                         if q in current and current[q] != dest]
                displaced = []
                if config['include_displacements']:
                    reserved = set(current.values()) | set(committed.values()) | set(targets)
                    free = [(r, c) for r in range(geometry['rows']) for c in range(geometry['columns'])
                            if (r, c) not in reserved]
                    for dest in targets:
                        q = occupancy.get(dest)
                        if q is None or q in active_qubits:
                            continue
                        ev = index.query(q, layer, lookahead['h'], completed=completed, active=active)
                        potential = FuturePotential.from_events(ev, snapshot,
                            gamma=lookahead['gamma'], spacing_um=spacing)
                        parking, _ = potential.choose(free, virtual)
                        if parking is None:
                            legal = False
                            break
                        free.remove(parking)
                        distances[q] = math.dist(current[q], parking) * spacing
                        moves.append((q, current[q], parking))
                        displaced.append({'qubit': q, 'estimated_site': list(parking)})
                if not legal:
                    entry.append(math.inf)
                    detail_entry.append({'legal': False, 'reason': 'bounded displacement estimator has no vacancy'})
                    continue
                conflict = sum(not line_compatible(a, b, x, y) for _, a, b in moves for _, x, y in fixed)
                # Both endpoints of this row are known: their internal
                # incompatibility can be charged without depending on new rows.
                internal = sum(not line_compatible(a, b, x, y)
                    for k, (_, a, b) in enumerate(moves) for _, x, y in moves[k + 1:])
                predicted = local_batch_cost(n_by_qubit, distances, profile,
                    next_cz_pairs=[pair], register_qubits=tuple(n_by_qubit))
                predicted['n_after'] = {q: predicted['n_after'][q] for q in distances}
                terms = predicted['terms']
                future = math.fsum(potentials[q].score(dest)['raw_distance_um'] for q, dest in zip(pair, targets))
                components = {
                    'distance': sum(distances.values()) / normal['distance_um'],
                    'conflict': (conflict + internal) / normal['conflict'],
                    'transfer': 2 * sum(d > 0 for d in distances.values()) / normal['transfer_events'],
                    'heating': (terms['E_heating_gate'] + terms['E_movement_loss']) / normal['error_E'],
                    'future': future / (2 * lookahead['h'] * normal['distance_um'])}
                metric = config['metric']
                if metric == 'pair_distance':
                    cost = sum(score_distances)
                elif metric == 'max_distance':
                    cost = max(distances.values(), default=0.)
                elif metric == 'move_time':
                    cost = predicted['duration_us']
                else:
                    cost = math.fsum(config['weights'][key] * value for key, value in components.items() if config['weights'][key] > 0)
                if not math.isfinite(cost):
                    cost = math.inf
                entry.append(cost)
                detail_entry.append({'legal': math.isfinite(cost), 'targets': [list(p) for p in targets],
                    'components': components, 'committed_conflicts': conflict, 'internal_conflicts': internal,
                    'predicted': predicted, 'distances_um': distances, 'displaced': displaced,
                    'future_raw_um': future, 'predictor_single_batch_compatible': internal == 0, 'missing_anchor_events': sum(len(potentials[q].missing_gate_ids) for q in pair)})
            cost_row.append(tuple(entry))
            detail_row.append(tuple(detail_entry))
        matrix.append(tuple(cost_row))
        detail_rows.append(tuple(detail_row))
    return Problem(pairs, slots, tuple(matrix), tuple(detail_rows), fixed, time.perf_counter() - started)


def assign(problem, objective):
    result = solve(problem.costs, objective)
    mapping, selected = {}, []
    for row, col in enumerate(result.columns):
        entry = problem.oriented_costs[row][col]
        orientation = 0 if entry[0] <= entry[1] else 1
        targets = problem.slots[col] if orientation == 0 else problem.slots[col][::-1]
        mapping.update(zip(problem.pairs[row], targets))
        selected.append({'row': row, 'column': col, 'orientation': orientation,
                         'cost': entry[orientation], **deepcopy(problem.details[row][col][orientation])})
    return mapping, selected, result
