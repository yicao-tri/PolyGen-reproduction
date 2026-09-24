#!/usr/bin/env python3
"""Create deterministic C1 polymer candidate sheets and structure comparisons.

Selection is deliberately stratified by arm, seed, and requested target.  Within
each stratum, eligible unique structures are ranked by target error and verifier
uncertainty.  This keeps the gallery reproducible and prevents post-hoc selection
from whichever seed or target happens to look most favorable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Lipinski, rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

ROOT = Path(__file__).resolve().parents[1]
ARM_COLOR = {"binary": "#6F55C5", "continuous": "#E24A3B"}
SHARED_COLOR = "#2E9F6B"
RDLogger.DisableLog("rdApp.*")


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def canonical(smiles: str) -> str | None:
    # The generator's validity contract treats Cu/Au as endpoint placeholders,
    # so canonicalization must do the same instead of applying metal valence.
    normalized = str(smiles).replace("[Cu]", "[*:1]").replace("[Au]", "[*:2]")
    mol = Chem.MolFromSmiles(normalized)
    return None if mol is None else Chem.MolToSmiles(mol, canonical=True)


def load_samples(bases: list[Path]) -> pd.DataFrame:
    files = []
    for base in bases:
        files.extend(sorted(base.glob("*-seed*/samples.csv")))
    if not files:
        raise FileNotFoundError(f"no C1 samples found below: {bases}")
    frames = [pd.read_csv(path).assign(source_file=str(path.relative_to(ROOT))) for path in files]
    data = pd.concat(frames, ignore_index=True)
    data["canonical_smiles"] = data.smiles.map(canonical)
    data["eligible"] = (
        data.valid.astype(bool) & data.novel.astype(bool) & data.canonical_smiles.notna()
        & data.support.ge(.35) & data.uncertainty.lt(.35)
    )
    data["selection_score"] = data.target_error + .25 * data.uncertainty
    return data


def descriptors(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    heavy = mol.GetNumHeavyAtoms()
    hetero = sum(a.GetAtomicNum() not in (1, 6, 29, 79) for a in mol.GetAtoms())
    return {
        "heavy_atoms": heavy,
        "heteroatom_fraction": hetero / heavy if heavy else 0.0,
        "ring_count": Lipinski.RingCount(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "logp": Descriptors.MolLogP(mol),
        "tpsa": Descriptors.TPSA(mol),
    }


def select_stratified(data: pd.DataFrame, per_stratum: int) -> pd.DataFrame:
    eligible = data[data.eligible].sort_values(
        ["arm", "seed", "target", "selection_score", "index"], kind="stable"
    )
    eligible = eligible.drop_duplicates(["arm", "seed", "target", "canonical_smiles"])
    return eligible.groupby(["arm", "seed", "target"], group_keys=False).head(per_stratum).copy()


def molecule_image(smiles: str, size=(500, 290)) -> Image.Image:
    mol = Chem.MolFromSmiles(smiles)
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DCairo(*size)
    opts = drawer.drawOptions()
    opts.bondLineWidth = 2.0
    opts.padding = .08
    opts.minFontSize = 14
    opts.maxFontSize = 25
    opts.updateAtomPalette({29: (.72, .34, .18), 79: (.84, .62, .10)})
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    import io
    return Image.open(io.BytesIO(drawer.GetDrawingText())).convert("RGB")


def draw_sheet(rows: pd.DataFrame, path: Path, title: str, columns=3) -> None:
    card_w, card_h = 520, 385
    header_h, footer_h = 82, 42
    nrows = max(1, (len(rows) + columns - 1) // columns)
    canvas = Image.new("RGB", (columns * card_w, header_h + nrows * card_h + footer_h), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((25, 18), title, fill="#202027", font=font(29, True))
    draw.text((25, 53), "Green border = structure occurs in both eligible arm pools", fill="#55555F", font=font(15))
    for pos, (_, row) in enumerate(rows.reset_index(drop=True).iterrows()):
        x, y = (pos % columns) * card_w, header_h + (pos // columns) * card_h
        border = SHARED_COLOR if bool(row.shared_between_arms) else ARM_COLOR[row.arm]
        draw.rounded_rectangle((x + 9, y + 7, x + card_w - 9, y + card_h - 7), radius=10,
                               outline=border, width=5, fill="#FFFFFF")
        image = molecule_image(row.canonical_smiles, (card_w - 34, 285))
        canvas.paste(image, (x + 17, y + 18))
        label = f"{row.candidate_id}  seed {int(row.seed)}  target {row.target:.1f}"
        draw.text((x + 22, y + 305), label, fill=border, font=font(18, True))
        hit = "hit" if bool(row.hit) else "miss"
        detail = f"pred {row.predicted_log_sigma:.3f}  |  error {row.target_error:.3f}  |  {hit}"
        draw.text((x + 22, y + 334), detail, fill="#303038", font=font(15))
        draw.text((x + 22, y + 357), f"support {row.support:.2f}  |  uncertainty {row.uncertainty:.2f}",
                  fill="#66666E", font=font(13))
    draw.text((25, canvas.height - 29), "[*:1] and [*:2] are the two polymer connection endpoints (Cu/Au in raw p-SMILES).",
              fill="#55555F", font=font(14))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, dpi=(300, 300))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", dest="inputs",
                        help="C1 result root; may be repeated (default: base plus all extra-seed batches)")
    parser.add_argument("--output", type=Path, default=ROOT / "results/experiment-c/c1/candidate_structures")
    parser.add_argument("--per-stratum", type=int, default=2)
    args = parser.parse_args()
    inputs = args.inputs or [
        ROOT / "results/experiment-c/c1",
        *sorted(path for path in (ROOT / "results/experiment-c/extra-seeds").glob("*") if path.is_dir()),
    ]
    data = load_samples(inputs)
    arms_by_seed = data.groupby("seed").arm.agg(set)
    incomplete = arms_by_seed[arms_by_seed.map(lambda x: x != {"binary", "continuous"})]
    if len(incomplete):
        raise RuntimeError(f"unpaired candidate seeds: {incomplete.to_dict()}")
    selected = select_stratified(data, args.per_stratum)

    pools = {
        arm: set(data[(data.arm == arm) & data.eligible].canonical_smiles)
        for arm in ("binary", "continuous")
    }
    shared = pools["binary"] & pools["continuous"]
    selected["shared_between_arms"] = selected.canonical_smiles.isin(shared)
    selected["candidate_id"] = ""
    for arm, prefix in (("binary", "B"), ("continuous", "C")):
        idx = selected.index[selected.arm == arm]
        selected.loc[idx, "candidate_id"] = [f"{prefix}{i:02d}" for i in range(1, len(idx) + 1)]

    args.output.mkdir(parents=True, exist_ok=True)
    # Remove only renderer-owned sheets so a changed seed roster cannot leave
    # obsolete 3-seed/5-seed galleries beside the current authoritative output.
    for pattern in ("binary_*_candidates.png", "continuous_*_candidates.png", "shared_*_selected_candidates.png"):
        for stale in args.output.glob(pattern):
            stale.unlink()
    selected.to_csv(args.output / "candidate_structure_index.csv", index=False)
    for arm in ("binary", "continuous"):
        arm_rows = selected[selected.arm == arm]
        draw_sheet(arm_rows, args.output / f"{arm}_{len(arm_rows)}_candidates.png",
                   f"C1 {arm.capitalize()} candidates — stratified across seed × target")

    shared_rows = selected[selected.canonical_smiles.isin(shared)].drop_duplicates("canonical_smiles")
    if len(shared_rows):
        draw_sheet(shared_rows, args.output / f"shared_{len(shared_rows)}_selected_candidates.png",
                   f"Selected structures shared between arms (n={len(shared_rows)})")

    unique = data[data.eligible].sort_values("selection_score").drop_duplicates(["arm", "canonical_smiles"]).copy()
    desc = pd.DataFrame([descriptors(s) for s in unique.canonical_smiles], index=unique.index)
    unique = pd.concat([unique, desc], axis=1)
    unique.to_csv(args.output / "eligible_unique_candidates.csv", index=False)
    # Freeze a conservative, deduplicated queue for the next MD validation stage.
    # The -3 target is the high-conductivity request; ranking penalizes verifier
    # uncertainty and is deliberately independent of whether a sample is a hit.
    md_pool = data[data.eligible & data.target.eq(-3.0)].copy()
    md_pool["conservative_log_sigma"] = md_pool.predicted_log_sigma - 1.96 * md_pool.uncertainty
    md_pool = md_pool.sort_values(
        ["arm", "conservative_log_sigma", "support", "uncertainty"],
        ascending=[True, False, False, True], kind="stable",
    ).drop_duplicates(["arm", "canonical_smiles"])
    md_queue = md_pool.groupby("arm", group_keys=False).head(20).copy()
    md_queue["rank_within_arm"] = md_queue.groupby("arm").cumcount() + 1
    md_queue.to_csv(args.output / "md_validation_top20_by_arm.csv", index=False)
    metrics = []
    for arm in ("binary", "continuous"):
        q = unique[unique.arm == arm]
        row = {
            "arm": arm,
            "eligible_unique": len(q),
            "exclusive_unique": len(pools[arm] - shared),
            "shared_unique": len(shared),
        }
        for col in ("heavy_atoms", "heteroatom_fraction", "ring_count", "rotatable_bonds", "logp", "tpsa"):
            row[f"mean_{col}"] = float(q[col].mean())
            row[f"median_{col}"] = float(q[col].median())
        metrics.append(row)
    summary = pd.DataFrame(metrics)
    summary["eligible_jaccard"] = len(shared) / len(pools["binary"] | pools["continuous"])
    summary.to_csv(args.output / "structure_comparison.csv", index=False)
    manifest = {
        "selection_rule": "two lowest (target_error + 0.25*uncertainty) eligible unique structures per arm/seed/target",
        "eligibility": "valid and novel and support >= 0.35 and uncertainty < 0.35",
        "input_roots": [str(path.relative_to(ROOT)) for path in inputs],
        "paired_seeds": sorted(int(seed) for seed in data.seed.unique()),
        "selected_per_arm": selected.groupby("arm").size().to_dict(),
        "eligible_unique_per_arm": {arm: len(pool) for arm, pool in pools.items()},
        "shared_eligible_unique": len(shared),
        "eligible_jaccard": len(shared) / len(pools["binary"] | pools["continuous"]),
        "md_queue_rule": "top 20 unique eligible structures per arm at target -3 by predicted_log_sigma - 1.96*uncertainty",
        "md_queue_per_arm": md_queue.groupby("arm").size().to_dict(),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
