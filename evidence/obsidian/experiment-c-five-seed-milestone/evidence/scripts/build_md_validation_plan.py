#!/usr/bin/env python3
"""Freeze a leakage-resistant MD validation manifest for Experiment C."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "results/experiment-c/c1/candidate_structures/md_validation_top20_by_arm.csv"
PUBLISHED = ROOT / "inputs/official-supplement/41524_2024_1470_MOESM2_ESM.csv"
OUT = ROOT / "results/experiment-c/md-validation"


def stable_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    queue = pd.read_csv(QUEUE)
    continuous = queue[queue.arm.eq("continuous")].copy()
    binary = queue[queue.arm.eq("binary")].copy()
    continuous.insert(0, "cohort", "continuous_top20")
    binary.insert(0, "cohort", "binary_top20")
    continuous.to_csv(OUT / "continuous_top20.csv", index=False)
    binary.to_csv(OUT / "binary_top20.csv", index=False)

    published = pd.read_csv(PUBLISHED)
    published["incomplete_bool"] = published.incomplete.astype(str).str.lower().eq("true")
    complete = published[~published.incomplete_bool & published["ionic_conductivity(S/cm)"].notna()].copy()
    legacy = complete.groupby("monomer_smiles").agg(
        published_replicates=("ionic_conductivity(S/cm)", "size"),
        published_mean_conductivity_S_cm=("ionic_conductivity(S/cm)", "mean"),
        published_sd_conductivity_S_cm=("ionic_conductivity(S/cm)", "std"),
    ).reset_index()
    # Selection is independent of the published conductivity outcome: canonical
    # string hashes fix a representative legacy control panel reproducibly.
    legacy["selection_hash"] = legacy.monomer_smiles.map(stable_key)
    legacy = legacy.sort_values("selection_hash").head(20).copy()
    legacy.insert(0, "cohort", "legacy_polygen_hash20")
    legacy.insert(1, "rank_within_cohort", range(1, len(legacy) + 1))
    legacy.to_csv(OUT / "legacy_polygen_hash20.csv", index=False)

    manifest_rows = []
    for cohort, frame, smiles_col in [
        ("continuous_top20", continuous, "smiles"),
        ("binary_top20", binary, "smiles"),
        ("legacy_polygen_hash20", legacy, "monomer_smiles"),
    ]:
        rank_col = "rank_within_arm" if "rank_within_arm" in frame else "rank_within_cohort"
        for _, row in frame.iterrows():
            manifest_rows.append({
                "cohort": cohort,
                "rank": int(row[rank_col]),
                "repeat_unit": row[smiles_col],
                "replicates": 5,
                "salt": "LiTFSI",
                "temperature_K": 353,
                "protocol": "match published PolyGen short all-atom MD before any long-MD escalation",
                "status": "PLANNED_NOT_RUN",
            })
    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(OUT / "md_batch_manifest.csv", index=False)

    protocol = """# Prospective MD validation protocol

## Primary question

Do the 20 continuous-conditioning candidates selected before MD achieve higher independently simulated ionic conductivity than candidates from binary PolyGen and the published PolyGen candidate pool under one common protocol?

## Frozen cohorts

- 20 continuous candidates requested at log conductivity -3, ranked by `predicted_log_sigma - 1.96 × uncertainty` after validity, novelty, support and uncertainty gates.
- 20 binary candidates selected by the identical rule.
- 20 published PolyGen candidates selected by a SHA-256 ordering of p-SMILES, independent of their already published conductivity outcomes. Their historical outcomes are retained only for audit and must not be used for prospective triage.
- Add PEO as a protocol control when its exact build specification is recovered from the original workflow.

## Simulation and analysis contract

Use the same LiTFSI formulation, 353 K condition, chain construction, PCFF+ parameters, relaxation, equilibration, production length and cluster Nernst–Einstein estimator as the published PolyGen workflow. Run five independently initialized replicas per structure. Randomize and blind cohort labels during build/simulation. Record build and force-field failures as outcomes rather than silently replacing structures.

Primary estimand: difference in structure-level mean log10 conductivity between continuous and binary cohorts. Secondary estimands: continuous versus legacy controls; probability of exceeding the best training-set benchmark; lower-confidence-bound yield; build success; transference number where available. Use structure—not trajectory frames—as the independent unit. Report bootstrap confidence intervals over structures and a permutation test of cohort labels. Do not select the best replica.

## Escalation gate

The current manifest is `PLANNED_NOT_RUN`. First execute standardized short MD for all cohorts. Long MD is permitted only under a frozen rule based on short-MD uncertainty and build success, applied identically across cohorts.
"""
    (OUT / "MD_VALIDATION_PROTOCOL.md").write_text(protocol)


if __name__ == "__main__":
    main()
