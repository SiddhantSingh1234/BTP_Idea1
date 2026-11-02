"""Bounded pair/parking neighborhoods ranked from actual routed transitions."""
from copy import deepcopy
import math
from implementation.repair.replay import positions, check_targets
from implementation.validation.checker import line_compatible
from implementation.lookahead.potential import FuturePotential
from implementation.movement_error.physics import local_batch_cost
from implementation.trace.model import fingerprint


def route_metrics(boundary):
    current, targets = positions(boundary['current_positions']), positions(boundary['targets'])
    moves = [(q, current[q], p) for q, p in sorted(targets.items()) if current[q] != p]
    degree = dict.fromkeys((q for q, _, _ in moves), 0)
    edges = 0
    for i, (q, a, b) in enumerate(moves):
        for r, c, d in moves[i + 1:]:
            if not line_compatible(a, b, c, d):
                edges += 1
                degree[q] += 1
                degree[r] += 1
    maximum = {}
    critical = {}
    for batch in boundary['route_batches']:
        duration = batch['duration_us']
        ds = {int(q): d for q, d in batch['distances_um'].items()}
        largest = max(ds.values(), default=0.)
        for q, d in ds.items():
            maximum[q] = max(maximum.get(q, 0.), d)
            if abs(d - largest) <= 1e-12 and d > 0:
                critical[q] = critical.get(q, 0.) + duration
    return {'direct_conflict_edges': edges, 'degree': degree, 'largest_segment_um': maximum,
            'critical_move_us': critical, 'actual_batches': len(boundary['route_batches']),
            'move_time_us': sum(r['duration_us'] for r in boundary['route_batches'])}


def rank_boundaries(compilation, options, minimum_order=0):
    values = []
    for boundary in compilation['repair_boundaries']:
        if boundary['order'] < minimum_order or not boundary['route_batches']:
            continue
        metric = route_metrics(boundary)
        # The actual routed move duration is the primary rank; conflicts break
        # ties. Neither graph degree nor this rank is the acceptance objective.
        values.append((boundary, metric))
    return sorted(values, key=lambda item: (-item[1]['move_time_us'], -item[1]['direct_conflict_edges'],
                                            item[0]['order'], item[0]['key']))[:options['transitions_per_round']]


def complete_targets(boundary, updates, case, index, lookahead):
    current = positions(boundary['current_positions'])
    targets = positions(boundary['targets'])
    targets.update({int(q): tuple(p) for q, p in updates.items()})
    active = {q for pair in boundary['active_pairs'] for q in pair}
    active_sites = [targets[q] for q in active]
    if len(set(active_sites)) != len(active_sites):
        return None
    known = {**current, **{q: targets[q] for q in active}}
    evicted = [q for q in sorted(targets) if q not in active and targets[q] in set(active_sites)]
    for q in evicted:
        occupied = {site for other, site in targets.items() if other != q}
        free = [(r, c) for r in range(case['geometry']['rows']) for c in range(case['geometry']['columns'])
                if (r, c) not in occupied]
        events = index.query(q, boundary['logical_layer'], lookahead['h'],
            completed=frozenset(boundary['prefix_state']['completed_gate_ids']),
            active=frozenset(boundary['active_gate_ids']))
        potential = FuturePotential.from_events(events, known, gamma=lookahead['gamma'],
                                                spacing_um=case['geometry']['spacing_um'])
        site, _ = potential.choose(free, (case['geometry']['rows'] / 2, case['geometry']['columns'] / 2))
        if site is None:
            return None
        targets[q] = site
    try:
        targets = check_targets(targets, current, boundary['active_pairs'], case['geometry'])
    except ValueError:
        return None
    return {str(q): list(p) for q, p in targets.items()}


def prediction(boundary, targets, case, profile):
    current = positions(boundary['current_positions'])
    destination = positions(targets)
    spacing = case['geometry']['spacing_um']
    distances = {q: math.dist(p, destination[q]) * spacing for q, p in current.items()}
    n = {int(q): v for q, v in boundary['prefix_state']['heating_n'].items()}
    result = local_batch_cost(n, distances, profile, next_cz_pairs=boundary['active_pairs'],
                              register_qubits=tuple(current))
    moves = [(p, destination[q]) for q, p in current.items() if p != destination[q]]
    conflicts = sum(not line_compatible(a, b, c, d) for i, (a, b) in enumerate(moves) for c, d in moves[i + 1:])
    return {'optimistic_one_batch_E': result['total_E'], 'one_batch_transport_us': result['duration_us'],
            'direct_conflicts': conflicts, 'maximum_distance_um': max(distances.values(), default=0.),
            'exact_routed_objective': False}


def generate(boundary, case, index, lookahead, profile, options):
    metric = route_metrics(boundary)
    current, targets = positions(boundary['current_positions']), positions(boundary['targets'])
    active = {q for pair in boundary['active_pairs'] for q in pair}
    decisions = []
    for pair in boundary['active_pairs']:
        if any(current[q] != targets[q] for q in pair):
            decisions.append(('pair', tuple(pair), max(metric['critical_move_us'].get(q, 0.) for q in pair),
                              sum(metric['degree'].get(q, 0) for q in pair)))
    for q in sorted(current):
        if q not in active and current[q] != targets[q]:
            decisions.append(('parking', (q,), metric['critical_move_us'].get(q, 0.), metric['degree'].get(q, 0)))
    decisions.sort(key=lambda d: (-d[2], -d[3], d[0], d[1]))
    output, seen = [], set()
    for kind, qubits, critical, conflicts in decisions[:options['decisions_per_transition']]:
        raw = []
        if kind == 'pair':
            a, b = qubits
            own = (targets[a], targets[b])
            raw.append(('orientation_flip', {a: own[1], b: own[0]}))
            for slot in boundary['candidate_slots'][:options['slot_scan_limit']]:
                for oriented in (slot, slot[::-1]):
                    raw.append(('alternative_phase05_slot', {a: oriented[0], b: oriented[1]}))
            others = [tuple(pair) for pair in boundary['active_pairs'] if tuple(pair) != qubits]
            for c, d in others[:options['swap_pair_scan_limit']]:
                second = (targets[c], targets[d])
                for first_targets in (second, second[::-1]):
                    for second_targets in (own, own[::-1]):
                        raw.append(('pair_slot_exchange', {a: first_targets[0], b: first_targets[1],
                                                          c: second_targets[0], d: second_targets[1]}))
        else:
            q = qubits[0]
            occupied = {p for other, p in targets.items() if other != q}
            free = [(r, c) for r in range(case['geometry']['rows']) for c in range(case['geometry']['columns'])
                    if (r, c) not in occupied and (r, c) != targets[q]]
            free.sort(key=lambda p: (math.dist(current[q], p), p))
            raw.extend(('alternative_parking', {q: site}) for site in free[:options['parking_site_scan_limit']])
        candidates = []
        for move_kind, updates in raw:
            replacement = complete_targets(boundary, updates, case, index, lookahead)
            if replacement is None or replacement == boundary['targets']:
                continue
            digest = fingerprint(replacement)
            if digest in seen:
                continue
            try:
                predicted = prediction(boundary, replacement, case, profile)
            except (ValueError, OverflowError):
                continue
            seen.add(digest)
            candidates.append({'boundary_key': boundary['key'], 'boundary_order': boundary['order'],
                'prefix_sha256': boundary['prefix_sha256'], 'targets': replacement,
                'kind': move_kind, 'selected_qubits': list(qubits),
                'reason': 'routed_straggler' if critical > 0 else 'conflict_serialization',
                'selection_critical_us': critical, 'selection_conflict_degree': conflicts,
                'predicted': predicted, 'target_sha256': digest})
        candidates.sort(key=lambda c: (c['predicted']['optimistic_one_batch_E'], c['predicted']['direct_conflicts'],
                                        c['target_sha256']))
        output.extend(candidates[:options['candidates_per_decision']])
    return output
