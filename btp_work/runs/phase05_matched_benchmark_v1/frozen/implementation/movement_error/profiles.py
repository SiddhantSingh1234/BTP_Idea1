"""NEW Phase 03: validated analytical profiles, independent of frozen hardware."""
from copy import deepcopy
import json
import math
from pathlib import Path
from implementation.trace.model import fingerprint

PROFILE_SCHEMA = 'movement_error_profile.phase03.v1'
MODES = ('stationary', 'move', 'transfer', 'gate', 'cooling')


def number(value, name, minimum=0.0, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{name}: finite number required')
    if value < minimum or (positive and value <= minimum):
        raise ValueError(f'{name}: out of range')
    return value


def probability(value, name='probability'):
    number(value, name)
    if value > 1:
        raise ValueError(f'{name}: must be <= 1')
    return value


def validate_profile(profile):
    p = deepcopy(profile)
    if p.get('schema_version') != PROFILE_SCHEMA or not p.get('profile_id'):
        raise ValueError('Unknown profile schema/identity')
    if p.get('computation_scope') != 'normalized_CZ_skeleton':
        raise ValueError('Only explicit normalized CZ scope is supported')
    if p.get('scorer') not in ('legacy', 'extended'):
        raise ValueError('Unknown scorer')
    if not p.get('sources') or not p.get('assumptions'):
        raise ValueError('Parameter provenance and assumptions required')
    m, h, c, noise, exposure = (p[k] for k in ('movement','heating','cooling','noise','exposure'))
    if m['family'] not in ('linear','cubic','triangular'):
        raise ValueError('Unknown movement family')
    number(m['speed_um_per_us'], 'legacy speed', positive=True)
    number(m['acceleration_um_per_us2'], 'acceleration', positive=True)
    number(m['minimum_duration_us'], 'minimum duration')
    if m['velocity_cap_um_per_us'] is not None:
        number(m['velocity_cap_um_per_us'], 'velocity cap', positive=True)
    if h['law'] not in ('disabled','atomique_cubic','atomique_surrogate'):
        raise ValueError('Unknown heating law')
    for key in ('cyclic_frequency_khz','x_zpf_um','loss_capacity','asymptotic_omega_T_min'):
        number(h[key], key, positive=True)
    for key in ('multiplier','lambda','initial_n'):
        number(h[key], key)
    for key,value in h.get('initial_n_by_qubit',{}).items():
        if not key.isdigit():raise ValueError('Initial n override key must be a qubit index')
        number(value, 'initial n override')
    if type(h['loss_enabled']) is not bool:raise ValueError('loss_enabled must be boolean')
    if h['law']=='atomique_cubic' and m['family']!='cubic':
        raise ValueError('Atomique heating requires cubic trajectory or explicit surrogate')
    for key in ('f_cz','f_transfer','f_h'):
        probability(noise[key], key)
    for key in ('cz_duration_us','transfer_duration_us','h_duration_us'):
        number(noise[key], key, positive=True)
    number(exposure['T2_us'], 'T2', positive=True)
    if set(exposure['rates']) != set(MODES):raise ValueError('All exposure modes must be declared')
    for key,value in exposure['rates'].items():number(value, 'rate '+key)
    for key,value in exposure['T2_by_qubit_us'].items():
        if not key.isdigit():raise ValueError('T2 override key must be a qubit index')
        number(value,'T2 override',positive=True)
    if type(c['enabled']) is not bool:raise ValueError('cooling enabled must be boolean')
    number(c['threshold_n'], 'cooling threshold', positive=True)
    number(c['cold_n'], 'cold n')
    if c['cold_n']>=c['threshold_n']:raise ValueError('Cooling must reset below trigger')
    if type(c['bank_count']) is not int or c['bank_count']<0:raise ValueError('Finite nonnegative bank count required')
    if c['enabled']:
        if c['bank_count']<1 or c['primitive']!='registered_bank_two_cnot':
            raise ValueError('Cooling requires declared cold banks and primitive')
        if c['population']!='entire_loaded_batch' or not c['sink_resource'] or not c['controller_resource']:
            raise ValueError('Cooling population, sink and controller required')
        number(c['dock_offset_um'],'dock offset',positive=True)
        for key in ('bank_registration_us','bank_preparation_us','bank_storage_plane_pitch_um'):
            number(c[key],key,positive=True)
        if c['bank_storage_plane_pitch_um']<=c['dock_offset_um']:raise ValueError('Banks require disjoint storage planes beyond the dock')
    elif c['bank_count']!=0:raise ValueError('No-cooling track cannot claim spare banks')
    return p


def load_profile(path):
    return validate_profile(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def profile_hash(profile):
    return fingerprint(validate_profile(profile))