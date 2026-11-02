# Phase 03 movement and error model specification

Owner: Codex /root, 28 October 2026. This is NEW Phase 03 work, specified before implementation. Earlier compiler, scorer, trace-v1, fixtures, native outputs and live benchmark worker remain original. Phase 02 engineering is accepted by the user's latest instruction; Phase 01 measurements and final dataset audit remain pending. See D004.

## Evidence and physical scope

Primary local evidence: [Atomique, PDF pp.6-7,11](../../../Papers/4_ISCA59077.2024.00030.pdf), [ZAP, PDF p.5](../../../Papers/2_ZAP_Zoned_Architecture_and_Performant_Compiler_for_Field-Programmable_Atom_Array.pdf), [DasAtom, PDF p.7](../../../Papers/3_DasAtom_A_Divide-and-Shuttle_Atom_Approach_to_Quantum_Circuit_Transformation.pdf), [RFT manuscript](../../../Papers/Priyanshu_Aditya_ISVLSI2026_AK_O.pdf), and [proposal, Idea 1 Step 1](../../../Proposal/BTP_Research_Proposal.pdf). C2-C5 of the [source review](../../source_review/SOURCE_REVIEW.md) apply. Local rendered pages and checksums are retained in runs/phase_03/research. The additional primary experiment is Bluvstein et al., *A quantum processor based on coherent transport of entangled atom arrays*, Nature 604, 451-456 (2022), [DOI](https://doi.org/10.1038/s41586-022-04592-6), Methods: dynamic reconfiguration and motional heating. It supplies the cubic-trajectory derivation, frequency convention and approximation limits. The [Atomique author artifact](https://zenodo.org/records/10995324) is inspected as source evidence only, never executed as a compiler.

The result is an independent-error success proxy, not calibrated state fidelity. Computation scope is the normalized CZ routing skeleton: omitted original one-qubit gates are not silently reconstructed or timed. Cooling's auxiliary one-qubit gates ARE charged. Full-circuit semantic evidence remains Phase 02's separate sidecar. Individual addressing and the frozen source geometry remain required. A profile that changes physics never establishes missing native physical evidence.

## Units, parameters and uncertainty

Canonical units are um, us, rad/us; n is dimensionless. 1 nm = .001 um, 1 ns = .001 us, 1 s = 1e6 us, and 1 m/s^2 = 1e-6 um/us^2. Source facts and architecture assumptions must be stored separately with each resolved profile and content hash.

| Quantity | Original source/value | Canonical default | Range/sensitivity and certainty |
| --- | --- | --- | --- |
| CZ fidelity/duration | DasAtom p.7/Table I and pinned legacy: .995, 200 ns | .995, .2 us | [0,1], positive duration; historical baseline constants |
| Transfer fidelity/time | ZAP p.5: .999, 15 us; DasAtom baseline: ideal,20 us | extended .999,20 us | [0,1], positive; mixed-source analytical adaptation, not one measured device |
| Legacy speed/grid spacing | pinned RFT/DasAtom .55 um/us,3 um | unchanged source hardware | positive; preserve historical inputs |
| Coherence | DasAtom/ZAP:1.5 s | 1.5e6 us per logical qubit | positive; decoupling-dependent effective coherence, not universal T1/T2 equality |
| Cyclic trap frequency | Atomique p.7:80 kHz; experiment Methods:2*pi*40 kHz during circuit,2*pi*80 kHz loading | .08 cycles/us -> .5026548245743669 rad/us | 40-80 kHz from sources; 80 is Atomique scenario,40 is experimental circuit sensitivity |
| Zero-point size | Atomique/experiment:38 nm | .038 um | >0; independently supplied source approximation; not recomputed from inconsistent masses/frequencies |
| Heating multiplier | analytical uncertainty choice | 1 | >=0; .5,1,2 sensitivity; not a fitted constant |
| Initial excess n | model reference relative to prepared cold state | 0 | >=0; initial finite thermal occupation is absorbed into approximate effective capacity |
| Gate-heating lambda | Atomique p.7 prints .109; author artifact hyperparams.py uses .109375 | .109375 | >=0; uncalibrated when transferred to RFT |
| Loss capacity | Atomique p.7:33; experiment approximate fitted capacity around30 | 33 | >0; sensitivity30,33; excess-state reference must agree |
| Cooling threshold | Atomique p.7:15 | 15 | >0; source sensitivity12-25; no weight optimization here |
| Acceleration ceiling | ZAP p.5 printed a < 2.75 um/us^2 | default .001 um/us^2 =1000 m/s^2 | default DERIVED from Atomique15um/300us cubic peak6D/T^2;2.75 is a source upper bound, not a calibrated default |
| Optional velocity cap | new analytical extension | absent | >0 when supplied; not inferred from average legacy speed |
| Cooling H fidelity/time | Atomique Table I .99992,625ns for generic1Q | .99992,.625us | assumption H takes generic1Q cost |
| Spare banks / separation / sink | new hypothetical resource contract | finite banks, registered cold partner at every grid site,3um offset, hot sink | not RFT hardware; full capacity and initial preparation declared; no free replenishment |

Profile validation rejects nonfinite, negative or inconsistent values and any probability outside [0,1]. Zero fidelity/loss probability1 produces infinite E. Negative gate survival is invalid, never clipped. Profile files will retain complete numerical values and parameter provenance.

## Compatible trajectories and synchronized batches

Every atom and each axis in a movement batch uses the SAME monotone progress u=t/T. Thus shared AOD rows/columns preserve their equality/order whenever endpoints do. Euclidean D_i is computed from both axes in um; the longest actual path sets T. Shorter paths are slowed to T and heating uses D_i,T, never independent fastest times. Analytic clearance is unchanged by a common monotone progress reparameterization.

* Historical linear: s(u)=u, T=Dmax/v. This preserves the old accounting path and is not the cubic heating trajectory.
* Source-consistent cubic: s(u)=3u^2-2u^3, v=(D/T)*6u(1-u), a=(6D/T^2)(1-2u), j=-12D/T^3. Rest-to-rest, constant negative jerk within the move; endpoint acceleration changes remain idealizations. T>=sqrt(6Dmax/a_max) and T>=1.5Dmax/v_max if a cap exists. These bounds are compatible with the chosen path.
* ZAP triangular acceleration: s=2u^2 for u<=1/2, otherwise1-2(1-u)^2; T=2sqrt(Dmax/a). Atomique heating on this family is explicitly a SURROGATE. It is never called a derived physical heating law.
* Optional capped triangular/trapezoidal extension: switch at D=vmax^2/a. Below, T=2sqrt(D/a); above, T=D/vmax+vmax/a. A shared progress is generated by the longest path's acceleration, cruise and deceleration segments. Shorter paths scale by D_i/Dmax.
* Dmax=0 gives zero movement time and zero heating/loss; it creates no inferred transfer.

## Heating, gate error and movement survival

Atomique's visually checked expression is dn=.5*[6D/(xzpf*omega0^2*T^2)]^2. The experiment derives it for harmonic confinement, omega0*T >> 1, and averaging phase oscillations over a small trap-frequency distribution. It is an approximate incoherent increment, not a coherent motional-state simulator. Frequency is ANGULAR: omega0=2*pi*f. Using 80kHz,38nm,300us gives dn=.0054,.13,.54 for15,75,150um, agreeing with printed examples; treating80kHz as radians/s is wrong by(2*pi)^4. The independent experimental55um/200us/40kHz example is approximately6. The implementation reports omega*T outside the declared asymptotic regime; it must not quietly claim physical validity there.

At each nonzero movement COMPLETION: add dn to each actual moved carrier, then charge conditional survival at its new n. For n>0, p_loss=.5*erfc[(nmax-n)/sqrt(2n)]; for n=0, p_loss=0. For small p, use -log1p(-p); for large n with tiny survival use direct erfc survival and a stable log-tail expansion. Repeated risky moves contribute repeatedly, following Atomique's event-product proxy; this is not asserted to be an exact absorbing-boundary process.

At a computation CZ START: base E_native=-ln(fCZ) and extra E_heating=-log1p[-lambda*(1-fCZ)*(n_a+n_b)]. Both carriers retain heating even after unloading to SLM: transferring traps is not cooling. This is an explicit adaptation from Atomique's sum for two heated carriers. For a genuine unmoved/cold partner n=0, it reduces to a single contribution.

At fixed T, doubling D quadruples dn; at fixed D, doubling T divides it by16. Substituting either T proportional to sqrt(D) makes D^2/T^4 independent of D for the longest path. This cancellation is real within the analytical combination, including the compatible cubic profile. Batch slowing, velocity caps and fixed-duration sweeps restore other distance dependences; no monotonic heating penalty is invented.

## Cooling resources, carrier handoff and exact costs

No-cooling is the default RFT resource track. Exceeding threshold is a warning; continue heating/loss and never reset n. Impossible gate survival is invalid. Cooling cannot rescue loss already charged at the previous move.

A SEPARATE hypothetical registered-bank profile extends the device. Each finite bank is a prepared, initially cold, zero-state array with one atom per legal grid site. Banks begin in disjoint storage planes100um apart. Each selected bank explicitly spends300us registering to a3um-offset interaction dock, then300us preparing its cold zero state in an isolated optical-control region. These times and storage planes are hypothetical resource requirements, not measured RFT capabilities. In-flight cold-bank spatial control is a declared primitive contract; it is not a continuous multi-array optical proof. Each bank is consumed once as an array-wide episode. Banks, all their atoms, an exclusive handoff controller and a hot-atom sink are declared physical resources; no in-circuit refill or reuse is assumed. Initial bank preparation is outside circuit time, just like initial data loading, and its population is reported. Exhaustion is unsupported, never free cooling. This expensive abstraction is not claimed available on basic RFT hardware.

After a nonzero movement and the charged bank registration/preparation stages, while movers remain on AOD, if any exceeds threshold, cool the ENTIRE loaded population of that batch. A registered cold partner at each destination must be within CZ range and satisfy the declared cross-plane clearance. Each affected atom executes CNOT(hot,cold) then CNOT(cold,hot), implemented as H-CZ-H for each CNOT: exactly2CZ+4H PER ATOM. On arbitrary |psi>|0> this yields |0>|psi>; independent amplitude checks must verify the map. Pairs execute serially to avoid cross-pair blockade; per-pair time=2tCZ+4tH. Heating penalty applies to both CZs BEFORE discarding the hot state. Base CZ/H costs belong only to E_cooling_gate.

Then two explicit parallel physical transfer substages retire hot atoms to the sink and hand the cold carriers back to the data trap rail, each duration t_transfer and one fidelity factor per affected physical atom. Finally normal unloading proceeds. These primitive trap handovers preserve n, as declared for all transfers; detailed beam/potential dynamics are not calibrated. The compound event records every suboperation, physical before/after carriers, docking sites, reserved bank/sink/controller, and durations. Only at completion does the logical-carrier mapping change and cold n reset. Retired hot carriers no longer own logical decoherence exposure. Bank spatial handling is a DECLARED PRIMITIVE CONTRACT, not a continuous optical-control proof.

## Exposure, event ordering and stable budgets

The extended default integrates one effective rate per logical qubit from initialization to circuit end, including stationary, transfer, motion, computation gates and cooling: E_deco=sum_q integral dt/T2_q. This adapts Atomique's all-register elapsed-time exposure and avoids counting transport a second time. Per-state rate multipliers and per-qubit T2 overrides allow declared sensitivity; zero gate rate implements exclusion of BOTH CZ operands' active gate intervals. Only one mode is active per qubit at a time. Spare atoms carry no logical state before handoff; during the internal entangled handoff the logical state is exposed for the whole primitive duration. Zero-qubit/empty schedules have zero exposure.

Intervals are half-open. Process completions (move heating/loss, completed handoff) before starts at a shared boundary; computation gates see all completed heating. Reject overlapping operations on the same logical or physical carrier and reserved resources. Simultaneous independent transfers cost time once and fidelity per atom. Sequential stages add time. Every event is audited with before/after n and incremental E.

E=E_native_gate+E_transfer+E_heating_gate+E_movement_loss+E_cooling_gate+E_decoherence. Cooling-transfer and cooling-time subtotals are diagnostics only. All sums are in negative log space; finite E is retained even when exp(-E) underflows. JSON uses null plus an explicit infinite flag rather than nonstandard Infinity.

## Integration and invariants

Use a NEW neutral_atom_schedule.phase03.v1 envelope around an immutable source trace and a fully resolved hashed profile. It has rescore, retime, and retime_and_cool operations. Original trace-v1 files and scorer are unchanged. Untimed native evidence cannot yield an extended time score without an explicitly labelled reconstruction. A frozen two-transfer-stage reconstruction can be scored repeatedly without changing its events. Heating on historical linear or triangular paths requires an explicit surrogate profile and is flagged.

Retiming preserves the ordered logical gate/movement decisions and geometry, changes times/trajectory and logs each addition/change. Cooling additionally changes physical carriers and adds operations, never placements. The independent Phase 03 checker validates carrier/bank lifetime, primitive resources/cost populations, event ordering and timing, then uses an explicit monotone-path projection for Phase 02's independent grid/line/clearance/DAG checker. The projection is a proof adapter for the declared primitive contract, not a native physical-evidence claim. Invalid/unsupported source status is retained and blocks accepted native comparisons.

Historical scoring always calls the ORIGINAL implementation/metrics/legacy.py on the frozen SOURCE trace. Its four-transfer alias, N*T-G*tCZ exposure and speed stay unchanged. Legacy compatibility tests cover the precise old timing/exposure convention; extended default exposure is intentionally different. Report historical source score, frozen-trace rescore, and changed-schedule result in separate fields/rows.

A local batch predictor accepts actual n, distances, shared duration and explicit next CZ pairs; it returns movement, transfer, exposure and next-gate marginal terms, assuming no other batches/cooling. Its boundary assumptions and omitted future gates are reported. A prediction-versus-replay fixture will show exact agreement under those assumptions and a nonzero suffix-heating error when the assumption is violated. Future phases must call this API instead of copying a private formula.

## Required validation and pilot

Independent checks: published heating/retention values; SI conversion; zero distance/heating/loss; fixed-T scaling; sqrt(D) cancellation; triangular/capped/cubic intermediate positions and bounds; equal/unequal synchronized moves; sequential sums; two risky moves; zero/one/invalid probability; large-n tails; underflow; per-qubit exposure; completion-before-gate; no double charging; cooling2CZ+4H and2transfer populations; cold resource exhaustion; bad docking; stale carriers; duplicate cooling/reset; immutable legacy results and preserved decisions. Existing Phase 02 acceptance tests must still pass.

The fixed pilot uses saved RFT/DasAtom QFT5 and a Table-II pair, plus the separately named corrected DasAtom QFT10 control and synthetic high-heating/synchronization cases. It reports all six E terms, source/derived validation, hashes, exposure, moved/transfer/cooling populations and rankings. Invalid/unsupported native cases stay excluded from accepted physical rankings. Sweeps cover40/80kHz, heating multiplier.5/1/2, declared acceleration and cooling thresholds. No heuristic weights are tuned and no physical or algorithmic gain is promised.

## Implemented evidence and controls

The implementation uses artifact lambda.109375 (paper rounded.109), seven profiles including frozen_ideal to isolate transfer fidelity, and explicit300us bank registration plus300us cold preparation per episode. [Research/citations](source_research.md), [validation](validation_report.md), [pilot](error_budget_pilot.md), [worked states](worked_budget.md), [handoff](../../handoffs/phase_03.md). Phase03 code is separate; original shared contracts and historical code are retained.
