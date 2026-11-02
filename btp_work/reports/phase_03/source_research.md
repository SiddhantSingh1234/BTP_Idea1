# Phase 03 primary-source research and citations

NEW Phase03 work, Codex /root,28 October2026. Papers/Proposal and the additional primary source below were used. Intern_Report was excluded. No subagents were used. Author artifact code was inspected, never executed as a compiler.

| Reference used | Reading and role |
| --- | --- |
| Wang et al., Atomique, ISCA2024 | [Local PDF](../../../Papers/4_ISCA59077.2024.00030.pdf), pp6-7 SectionIV/TableI, p11 sensitivity: heating, gate penalty, movement retention and cooling populations. [DOI](https://doi.org/10.1109/ISCA59077.2024.00030). |
| Huang et al., ZAP | [Local PDF](../../../Papers/2_ZAP_Zoned_Architecture_and_Performant_Compiler_for_Field-Programmable_Atom_Array.pdf), p5 Eqs4-5/Table1: triangular timing, transfer fidelity, exposure notation. Its zoned/global architecture is not imported. |
| Huang et al., DasAtom | [Local PDF](../../../Papers/3_DasAtom_A_Divide-and-Shuttle_Atom_Approach_to_Quantum_Circuit_Transformation.pdf), p7 Eqs3-5 and architecture: historical time/exposure, preserved separately. |
| Priyanshu and Aditya, RFT manuscript | [Local PDF](../../../Papers/Priyanshu_Aditya_ISVLSI2026_AK_O.pdf), method, architecture, movement objective and fidelity assumptions. No exact-paper reproduction claim. |
| BTP proposal | [Local PDF](../../../Proposal/BTP_Research_Proposal.pdf), Idea1 Step1,p2. C2-C5 in the [prior review](../../source_review/SOURCE_REVIEW.md) correct missing heating-gate and per-atom cooling terms. |
| Bluvstein et al., A quantum processor based on coherent transport of entangled atom arrays, Nature604,451-456(2022) | Additional primary experiment: [retained PDF](../../source_review/phase03_additional/Bluvstein_2022_coherent_transport.pdf), Methods pp7-8, heating Eqs1-2 and coherence context. [DOI](https://doi.org/10.1038/s41586-022-04592-6), [author PDF origin](https://eapg.mit.edu/wp-content/uploads/2022/10/Q-Processor-coherent-transport-Nature-Bluvstein.pdf), [checksum/extraction](../../source_review/phase03_additional/manifest.json). |
| Atomique author artifact | [Zenodo10995324](https://zenodo.org/records/10995324), fpqa-revision-AE.zip. [Retained manifest](../../runs/phase_03/research/research_manifest.json). SHA256 `2d8169e888910c96ed9a4428f2540e239dd3733bb0228066d65757e2d2917f8a`; MD5 matches publisher. Relevant unmodified [hyperparams.py](../../source_review/phase03_atomique/fpqa-revision-AE/hyperparams.py), [analyzer.py](../../source_review/phase03_atomique/fpqa-revision-AE/compilers/analyzer.py). |

Local visual verification used isolated pypdfium2-5.14.0 without changing the benchmark environment. [Atomique equation](../../runs/phase_03/research/4_page_6.png), [parameters/loss/cooling](../../runs/phase_03/research/4_page_7.png), [sensitivity](../../runs/phase_03/research/4_page_11.png), [ZAP equation/table](../../runs/phase_03/research/2_page_5.png), [historical DasAtom equations](../../runs/phase_03/research/3_page_7.png). Extraction distorts fractions/radicals; the rendered originals were checked.

## Resolutions

Angular frequency is2*pi*f. The artifact explicitly sets omega_0=2*pi*80*1e3 radians/s, recovering the printed heating examples. The experiment derives cubic-path heating under harmonic confinement, large omega*T and phase averaging. Its circuit operating context includes40kHz. Published parameters are not necessarily one operating point:80kHz/38nm is retained as Atomique's analytical scenario, not asserted isotope/mass consistency. A calibrated device requires mutually consistent mass, trap depth, frequency and initial temperature.

Artifact lambda=.109375; the paper rounds it to.109. Profiles record the artifact value. Printed retention values at n15/20/30 are recovered; extreme tails agree with independent SciPy normal-log-CDF calculations.

Cubic peak acceleration is6D/T^2, giving compatible sqrt(6D/a) time. ZAP's2sqrt(D/a) belongs to another trajectory. Either square-root distance time cancels D in the approximate heating of a maximally accelerated longest path. Shorter synchronized atoms still use actual D_i and shared T. No invented distance penalty is added.

The Atomique analyzer resets vibrational state and charges cooling CZs without scheduling the entire cooling procedure; allocation destruction also resets stored array n. Phase03 instead follows moved-atom cadence, preserves heating on physical carriers through ordinary transfer and explicitly charges cooling time/resources. These are declared architecture adaptations. Both heated carriers contribute at gate start where appropriate.

The effective coherence constant is not an assertion that T1=T2. Long experimental coherence uses decoupling. This profile assumes an effective controlled coherence and does not add a second movement-decoherence factor or silently model additional decoupling-pulse errors.

## Limits

There is no joint measured RFT calibration. Loss is an event-product approximation, not an exact absorbing-boundary process. Short omega*T is unsupported; negative survival is invalid. Background trap heating, vacuum hazard, correlated/coherent noise, full optical control and loss recovery are not invented. Original omitted computation1Q operations remain outside normalized-CZ timing; auxiliary cooling H gates are charged. Bank storage, preparation/registration and trap handovers are an explicitly hypothetical resource contract, not a measured continuous multi-array proof. Native physical evidence and final Phase01 dataset acceptance remain limited even when synthetic schedules pass within their declared model.
