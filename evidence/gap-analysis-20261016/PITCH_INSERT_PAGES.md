---
title: PolyGen Improve-loop pitch insert pages
date: 2026-10-16
status: ready-to-insert; physical-validation elements remain planned
---

# Slide P1 — A generator can look better on every dashboard and still not help the decision

## On-slide claim

Continuous conditioning improves verifier-defined target adherence inside the
frozen support, but it trades away validity and novelty. These are surrogate
metrics, not measured conductivity.

## Figure

Use `assets/figures/P1_decision_value_tradeoff.pdf`.

## On-slide numbers

- C1 strict-hit rate: continuous `0.1780` vs binary `0.1587`; paired effect `+0.0193`, 95% paired-seed t interval `[+0.0064, +0.0322]`.
- Target MAE: continuous `0.6331` vs binary `0.6940`.
- Validity: continuous `0.4547` vs binary `0.5220`.
- Novelty: continuous `0.4313` vs binary `0.5033`.
- Replication unit: five paired training seeds; not independent candidate replicates.

## Speaker note

The continuous arm changes the local surrogate behavior in the intended
direction, but the same intervention lowers validity and novelty. The correct
claim is a support-aware tradeoff, not unconditional generator superiority.

# Slide P2 — The verifier is blind exactly where the decision concentrates

## On-slide claim

Zero RF-predicted frontier crossings do not identify a generator failure when
the blind verifier compresses the locked-tail response into a narrow range.

## Figure

Use `assets/figures/P2_verifier_blind_locked_tail.pdf`.

## On-slide numbers

- Locked-tail rows: `1,205`.
- Blind RF MAE: `0.310` log10(S/cm).
- Mean observed-minus-predicted residual: `+0.310` log10(S/cm).
- Training boundary: `−4.0845` log10(S/cm).
- Full-source RF MAE `0.131` is post-hoc only and is not a leakage-free endpoint.

## Speaker note

The locked-tail observations extend toward approximately `−3.3`, while the
blind RF predictions occupy a much narrower band below the frozen boundary.
Therefore the honest diagnosis is verifier-limited, or unresolved between
verifier-limited and generator-limited. Physical observation is the next
experiment.

# Slide P3 — The next action is the experiment that repairs the verifier

## On-slide claim

The next loop action is a stratified physical experiment, not another RF-only
reranking pass.

## Figure

Use `assets/figures/P3_verifier_repair_experiment.pdf`.

## On-slide status labels

- Observed: frozen RF response and one-structure PFP smoke anchor.
- Planned: PCFF+ parameterized candidate queue, five replicas per structure,
  convergence gate, RF-to-MD residual calibration.
- Not a result: any dashed PCFF+/PFP ladder segment and any synthetic decision-change bar.

## Speaker note

The PFP pilot is labelled `NON_CONVERGED_SMOKE_ONLY` and cannot establish a
physical ranking. The physical route remains gated because complete PCFF+
parameter coverage and ARC PCFF+ integration are not yet available. Once the
gate passes, compare RF ranking with residual-calibrated ranking using confirmed
MD hits per unit cost, then update the generator only from blinded outcomes.

# Backup — Freeze card

Use `assets/tables/T6_freeze_card.csv` to show the candidate identity, model
SHA, verifier version, replica policy, convergence rule, and stopping rule.
The MD hit criterion is explicitly labelled `proposed_not_yet_TRI_approved`;
do not present it as an approved physical result.

