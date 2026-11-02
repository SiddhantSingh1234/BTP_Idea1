"""Scoped critical-remaining-depth weighting of parking decisions only.

No accepted Phase04/05/06 source is edited. The original assignment-future
predictor and repair neighborhood remain unchanged, isolating parking weights.
"""
from contextlib import contextmanager
import math
from implementation.lookahead.potential import FuturePotential


def critical_depths(circuit):
    """Longest remaining CZ-DAG path, in gate counts including the current gate."""
    gates = circuit['gates']
    ids = {g['gate_id'] for g in gates}
    successors = {g: [] for g in ids}
    seen = set()
    for gate in gates:
        for parent in gate['dependencies']:
            if parent not in seen:
                raise ValueError('Critical-depth calculation requires topologically ordered gates')
            successors[parent].append(gate['gate_id'])
        if gate['gate_id'] in seen:
            raise ValueError('Duplicate gate identity')
        seen.add(gate['gate_id'])
    result = {}
    for gate in reversed(gates):
        gid = gate['gate_id']
        result[gid] = 1 + max((result[s] for s in successors[gid]), default=0)
    return result


class WeightedPotential:
    def __init__(self, base, depths):
        self.base = base
        self.resolved = base.resolved
        self.missing_gate_ids = base.missing_gate_ids
        maximum = max((depths[g] for g, *_ in self.resolved), default=1)
        self.weights = tuple(depths[g] / maximum for g, *_ in self.resolved)

    def score(self, site):
        # Delegate site/parameter validation to the original independent API.
        result = self.base.score(site)
        if not self.resolved:
            return result
        reference = result['reference_delta']
        scaled = math.fsum(w * self.base.gamma ** (delta-reference) * math.dist(site, anchor) * self.base.spacing_um
                          for w, (_, _, delta, anchor) in zip(self.weights, self.resolved))
        raw = math.exp(result['log_common_scale']) * scaled
        return {**result, 'scaled_distance_um': scaled, 'raw_distance_um': raw,
                'raw_underflow': raw == 0 and scaled > 0,
                'parking_weighting': 'critical_remaining_CZ_depth', 'normalized_event_weights': list(self.weights)}

    def choose(self, available_positions, center_of_mass):
        if not available_positions:
            return None, []
        candidates = []
        for site in available_positions:
            score = self.score(site)
            value = score['scaled_distance_um'] if self.resolved else math.dist(site, center_of_mass) * self.base.spacing_um
            candidates.append({'site': list(site), 'selection_cost': value, 'score': score})
        best = min(candidates, key=lambda item: (item['selection_cost'], tuple(item['site'])))
        return tuple(best['site']), candidates


@contextmanager
def parking_weight_scope(circuit, mode):
    import implementation.lookahead.integration as integration
    if mode == 'uniform':
        yield
        return
    if mode != 'critical_remaining_depth':
        raise ValueError('Unsupported parking weighting')
    depths = critical_depths(circuit)
    original_potential = integration.FuturePotential
    original_validate = integration.validate_options

    class Factory:
        @classmethod
        def from_events(cls, events, known_positions, **kwargs):
            return WeightedPotential(FuturePotential.from_events(events, known_positions, **kwargs), depths)

    def validate(value):
        if value.get('weight_mode') != mode:
            return original_validate(value)
        original = original_validate({**value, 'weight_mode': 'uniform'})
        return {**original, 'weight_mode': mode}
    integration.FuturePotential = Factory
    integration.validate_options = validate
    try:
        yield
    finally:
        integration.FuturePotential = original_potential
        integration.validate_options = original_validate
