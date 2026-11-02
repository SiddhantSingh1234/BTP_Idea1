"""NEW Phase 03: pure um/us physics functions and stable conditional costs."""
import math
from implementation.movement_error.profiles import number, probability

TERMS = ('E_native_gate','E_transfer','E_heating_gate','E_movement_loss','E_cooling_gate','E_decoherence')


def zero_budget():
    return dict.fromkeys(TERMS, 0.0)


def neglog_failure(p):
    probability(p)
    return math.inf if p == 1 else -math.log1p(-p)


def neglog_fidelity(f):
    probability(f,'fidelity')
    return math.inf if f == 0 else -math.log(f)


def movement_time(distance_um, movement):
    d=number(distance_um,'distance')
    if d == 0:return 0.0
    family=movement['family'];a=movement['acceleration_um_per_us2'];v=movement['velocity_cap_um_per_us']
    if family=='linear':t=d/movement['speed_um_per_us']
    elif family=='cubic':
        t=math.sqrt(6*d/a)
        if v is not None:t=max(t,1.5*d/v)
    elif family=='triangular':
        t=2*math.sqrt(d/a) if v is None or d<=v*v/a else d/v+v/a
    else:raise ValueError('Unknown trajectory')
    return max(t,movement['minimum_duration_us'])


def progress(elapsed_us, duration_us, family, distance_um=None, movement=None):
    number(elapsed_us,'elapsed');number(duration_us,'duration')
    if elapsed_us>duration_us:raise ValueError('Time outside trajectory')
    if duration_us==0:return 1.0
    u=elapsed_us/duration_us
    if family=='linear':return u
    if family=='cubic':return u*u*(3-2*u)
    if family!='triangular':raise ValueError('Unknown trajectory')
    # Time dilation preserves bounds when a minimum duration slows a batch.
    if movement is None or distance_um is None or distance_um==0 or movement['velocity_cap_um_per_us'] is None:
        return 2*u*u if u<=.5 else 1-2*(1-u)**2
    a=movement['acceleration_um_per_us2'];v=movement['velocity_cap_um_per_us'];d=distance_um
    if d<=v*v/a:return 2*u*u if u<=.5 else 1-2*(1-u)**2
    fastest=d/v+v/a;t=u*fastest;ta=v/a
    if t<ta:return .5*a*t*t/d
    if t<=fastest-ta:return (v*t-.5*v*v/a)/d
    return 1-.5*a*(fastest-t)**2/d


def position(start, end, elapsed_us, duration_us, family, **kwargs):
    s=progress(elapsed_us,duration_us,family,**kwargs)
    return [a+(b-a)*s for a,b in zip(start,end)]


def angular_frequency(heating):
    return 2*math.pi*heating['cyclic_frequency_khz']*.001


def heating_increment(distance_um, duration_us, heating):
    d=number(distance_um,'distance');t=number(duration_us,'duration')
    if d==0 or heating['law']=='disabled' or heating['multiplier']==0:return 0.0
    if t==0:raise ValueError('Nonzero movement requires positive duration')
    w=angular_frequency(heating)
    return heating['multiplier']*.5*(6*d/(heating['x_zpf_um']*w*w*t*t))**2


def log_erfc_positive(x):
    # erfc underflows in the tail; asymptotic series is stable for x>=20.
    if x<20:return math.log(math.erfc(x))
    term=1.0;series=1.0
    for k in range(1,30):
        term*=-(2*k-1)/(2*x*x);series+=term
        if abs(term)<abs(series)*1e-16:break
    return -x*x-math.log(x)-.5*math.log(math.pi)+math.log(series)


def movement_loss_cost(n, capacity):
    number(n,'n');number(capacity,'capacity',positive=True)
    if n==0:return 0.0
    z=(capacity-n)/math.sqrt(2*n)
    if z>=0:return neglog_failure(.5*math.erfc(z))
    return math.log(2)-log_erfc_positive(-z)


def heating_gate_cost(n_sum, profile):
    number(n_sum,'gate n')
    if profile['heating']['law']=='disabled':return 0.0
    p=profile['heating']['lambda']*(1-profile['noise']['f_cz'])*n_sum
    return neglog_failure(p)


def local_batch_cost(n_by_qubit, distances_by_qubit_um, profile, *, duration_us=None, next_cz_pairs=(), register_qubits=None):
    """Increment relative to no batch; exact only for supplied boundary assumptions.

    Does not plan routing/cooling, infer later gates or hide their suffix effects.
    """
    m=profile['movement'];h=profile['heating'];noise=profile['noise'];ex=profile['exposure']
    ds={q:number(d,'distance') for q,d in distances_by_qubit_um.items()};moving={q:d for q,d in ds.items() if d>0}
    t=movement_time(max(moving.values(),default=0),m) if duration_us is None else number(duration_us,'duration')
    if moving and t+1e-8<movement_time(max(moving.values()),m):raise ValueError('Prediction duration violates trajectory bounds')
    after=dict(n_by_qubit);b=zero_budget();threshold=[]
    for q,d in moving.items():
        after[q]=after[q]+heating_increment(d,t,h)
        if h['loss_enabled']:b['E_movement_loss']+=movement_loss_cost(after[q],h['loss_capacity'])
        if after[q]>profile['cooling']['threshold_n']:threshold.append(q)
    if moving:b['E_transfer']=2*len(moving)*neglog_fidelity(noise['f_transfer'])
    for a,c in next_cz_pairs:
        baseline=heating_gate_cost(n_by_qubit[a]+n_by_qubit[c],profile)
        if not math.isfinite(baseline):raise ValueError('Infinite baseline requires full replay; local marginal is undefined')
        b['E_heating_gate']+=heating_gate_cost(after[a]+after[c],profile)-baseline
    span=t+2*noise['transfer_duration_us'] if moving else 0.0
    qs=register_qubits if register_qubits is not None else list(n_by_qubit)
    for q in qs:
        rate_time=(t*ex['rates']['move']+2*noise['transfer_duration_us']*ex['rates']['transfer']) if q in moving else span*ex['rates']['stationary']
        b['E_decoherence']+=rate_time/ex['T2_by_qubit_us'].get(str(q),ex['T2_us'])
    return {'terms':b,'total_E':sum(b.values()),'duration_us':span,'move_duration_us':t,'n_after':after,'threshold_exceeded_qubits':threshold,
            'assumptions':['one legal shared-progress batch','load and unload once per nonzero mover','no cooling','only supplied next CZs; no later suffix gates'],
            'requires_full_replay':bool(threshold)}