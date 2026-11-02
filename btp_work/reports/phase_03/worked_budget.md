# Worked Phase 03 budget and atom states

[Raw stress schedule](../../runs/phase_03/pilot_03/raw/evaluations/synthetic_heating/extended_registered_cooling/schedule.json), [full event audit](../../runs/phase_03/pilot_03/raw/evaluations/synthetic_heating/extended_registered_cooling/result.json). This is a fixed synthetic route under declared extra hardware. Before/after physical carriers, sites, suboperations, times and incremental E are saved.

Initial a0/a1 sites:(0,0)/(0,2), spacing3um. Each batch translates both15um with shared progress, alternating row0 and row5. Duration sqrt(6*15/.05)=42.426406871us. With omega=2*pi*.08rad/us and x=.038um, each actual mover gains13.5601158019 excess quanta. Initial n=3. Ordinary trap transfer preserves n.

| Move completion | n per carrier before cooling | Action after charging both survival factors | n at next original CZ |
| --- | ---: | --- | ---: |
|1 |16.5601158019 | Bank0 handoff |0 |
|2 |13.5601158019 | No trigger |13.5601158019 |
|3 |27.1202316038 | Bank1 handoff |0 |
|4 |13.5601158019 | No trigger |13.5601158019 |
|5 |27.1202316038 | Bank2 handoff |0 |

A handoff charges300us registration+300us cold zero-state preparation. Each atom then executes H(cold),CZ(hot,cold),H(cold),H(hot),CZ(hot,cold),H(hot):2*.2+4*.625=2.9us. Pairs are serial. Both CZs receive the warm-hot plus cold vibrational penalty. Two20us parallel transfer substages retire hot atoms and return cold carriers; four physical transfer factors per two-atom episode. The normal unload follows. Logical information changes physical carrier only at completion. Retired hot identities are not reused. Independent amplitudes check the2CNOT handoff with an entangled reference.

Per episode:600+2*2.9+40=645.8us,4CZ,8H,four extra atom transfers. Three episodes add1937.4us,12CZ,24H and12 transfers. Base time:five42.426406871us moves+ten20us transfer stages+five.2us original CZ stages=413.132034356us. Total2350.532034356us. Each logical qubit is exposed for the full span; E_decoherence=2*2350.532034356/1500000=.00313404271247. No second movement/cooling exposure is added.

The [six terms](error_budget_pilot.md) sum to.8626180041677581. Cooling gate bases occur only in E_cooling_gate; their heating occurs only in E_heating_gate. All32 physical atom-transfer events occur once in E_transfer; concurrent time is charged by stage. Cooling subtotals are diagnostics, never added twice. Without resources, n never resets and every nonzero move still charges conditional risk.
