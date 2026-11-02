"""NEW Phase04 future-distance potential; current/committed anchors only."""
from dataclasses import dataclass
import json,math
from pathlib import Path

SCHEMA='lookahead_options.phase04.v1'


def validate_options(value):
    p=dict(value)
    required={'schema_version','variant_id','lookahead_policy','h','gamma','weight_mode','current_distance_weight','anchor_policy','assignment_future_bias'}
    if set(p)!=required:raise ValueError('Unknown or missing lookahead option')
    if p['schema_version']!=SCHEMA or not isinstance(p['variant_id'],str) or not p['variant_id']:raise ValueError('Options identity')
    if p['lookahead_policy'] not in ('legacy_exact','next_events'):raise ValueError('Unknown lookahead policy')
    if type(p['h']) is not int or p['h']<1:raise ValueError('h must be positive')
    if type(p['gamma']) not in (int,float) or not math.isfinite(p['gamma']) or not 0<p['gamma']<=1:raise ValueError('gamma must be in (0,1]')
    if p['weight_mode']!='uniform' or p['current_distance_weight']!=0:raise ValueError('Only explicit equal-weight pure future distance is enabled')
    if p['anchor_policy']!='committed_active_else_current' or p['assignment_future_bias'] is not False:raise ValueError('Unsupported anchor/assignment policy')
    return p


def load_options(path):return validate_options(json.loads(Path(path).read_text(encoding='utf-8')))


@dataclass(frozen=True,slots=True)
class FuturePotential:
    # (gate_id,partner,delta,immutable anchor). No future schedule is accepted.
    resolved:tuple
    missing_gate_ids:tuple
    gamma:float
    spacing_um:float

    @classmethod
    def from_events(cls,events,known_positions,*,gamma,spacing_um):
        if not math.isfinite(gamma) or not 0<gamma<=1 or not math.isfinite(spacing_um) or spacing_um<=0:raise ValueError('Invalid potential parameters')
        resolved=[];missing=[]
        for event in events:
            delta=event['logical_layer_delta']
            if type(delta) is not int or delta<0:raise ValueError('Negative/noninteger future distance')
            q=event['partner']
            if q not in known_positions:missing.append(event['gate_id']);continue
            anchor=tuple(known_positions[q])
            if len(anchor)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in anchor):raise ValueError('Invalid known anchor')
            resolved.append((event['gate_id'],q,delta,anchor))
        return cls(tuple(resolved),tuple(missing),float(gamma),float(spacing_um))

    def score(self,site):
        if len(site)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in site):raise ValueError('Invalid site')
        if not self.resolved:return {'scaled_distance_um':0.0,'raw_distance_um':0.0,'log_common_scale':0.0,'reference_delta':None,'raw_underflow':False}
        reference=min(e[2] for e in self.resolved)
        scaled=math.fsum(self.gamma**(delta-reference)*math.dist(site,anchor)*self.spacing_um for _,_,delta,anchor in self.resolved)
        log_scale=reference*math.log(self.gamma);raw=math.exp(log_scale)*scaled
        return {'scaled_distance_um':scaled,'raw_distance_um':raw,'log_common_scale':log_scale,'reference_delta':reference,
                'raw_underflow':raw==0 and scaled>0,'cross_qubit_scores_require_common_scale':True}

    def choose(self,available_positions,center_of_mass):
        if not available_positions:return None,[]
        candidates=[]
        for site in available_positions:
            score=self.score(site)
            value=score['scaled_distance_um'] if self.resolved else math.dist(site,center_of_mass)*self.spacing_um
            candidates.append({'site':list(site),'selection_cost':value,'score':score})
        best=min(candidates,key=lambda item:(item['selection_cost'],tuple(item['site'])))
        return tuple(best['site']),candidates