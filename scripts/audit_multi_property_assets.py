#!/usr/bin/env python3
"""Freeze a read-only feasibility audit for the multi-property benchmark."""
from __future__ import annotations
import hashlib, json, platform, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "inputs/release-data/htpmd-trainset.csv"
OUT = ROOT / "results/multi-property/manager-audit"
PROPS = ["conductivity", "li_diffusivity", "tfsi_diffusivity", "poly_diffusivity", "transference_number", "molality"]
LOG_PROPS = {"conductivity", "li_diffusivity", "tfsi_diffusivity", "poly_diffusivity"}

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(SOURCE)
    audit = {
        "status": "feasibility_audit_only",
        "source": str(SOURCE), "source_sha256": sha256(SOURCE),
        "rows": int(len(d)), "columns": list(d.columns),
        "properties": {}, "metadata": {},
        "existing_multi_property_model": False,
        "definitive_generation_status": "not_run",
    }
    for c in PROPS:
        x = pd.to_numeric(d[c], errors="coerce")
        z = np.log10(x) if c in LOG_PROPS else x
        audit["properties"][c] = {
            "nonmissing": int(x.notna().sum()), "finite": int(np.isfinite(x).sum()),
            "unique": int(x.nunique()), "min": float(x.min()), "max": float(x.max()),
            "quantiles_raw": {str(q): float(x.quantile(q)) for q in (.5, .8, .9, .95, 1.0)},
            "transform": "log10_train_only" if c in LOG_PROPS else "raw_train_only",
            "quantiles_transformed": {str(q): float(z.quantile(q)) for q in (.5, .8, .9, .95, 1.0)},
        }
    for c in ["force_field", "temperature", "sim_time", "material_group", "salt_cation", "salt_anion", "trajectory_id", "structure", "mol_smiles"]:
        if c in d:
            audit["metadata"][c] = {"unique": int(d[c].nunique()), "missing": int(d[c].isna().sum())}
    # A train-only Q80 feasibility table: this is an audit, not a model fit.
    q80 = {c: float((np.log10(d[c]) if c in LOG_PROPS else d[c]).quantile(.8)) for c in PROPS}
    train_mask = np.ones(len(d), dtype=bool)
    for c in PROPS:
        v = np.log10(d[c].to_numpy()) if c in LOG_PROPS else d[c].to_numpy()
        train_mask &= v <= q80[c]
    audit["joint_q80_intersection"] = {
        "rule": "all six transformed properties <= full-source Q80",
        "rows": int(train_mask.sum()), "fraction": float(train_mask.mean()),
        "property_q80_transformed": q80,
    }
    audit["asset_constraints"] = [
        "Existing PolyGen conditioning implementation is scalar conductivity-only.",
        "No released six-dimensional checkpoint exists.",
        "No released joint surrogate/GNN pipeline exists.",
        "The definitive multi-property generation experiment therefore remains unrun; this file does not substitute for it.",
    ]
    audit["environment"] = {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__}
    try:
        audit["git_status"] = subprocess.run(["git", "status", "--short"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.splitlines()
    except Exception as e:
        audit["git_status_error"] = str(e)
    (OUT / "source_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    pd.DataFrame([{"property": c, **v} for c, v in audit["properties"].items()]).to_json(OUT / "property_audit.json", orient="records", indent=2)
    pd.DataFrame([{"cell": "joint_q80_intersection", "status": "audit_only", "rows": int(train_mask.sum()), "reason": "requires new multi-property model and joint surrogate"}]).to_csv(OUT / "unsupported_cells.csv", index=False)
    (OUT / "REPORT.md").write_text("""# Multi-property manager asset audit\n\nThis is a feasibility audit only; it is not a definitive multi-property generation result.\n\n- Source and property coverage are recorded in `source_audit.json` and `property_audit.json`.\n- The six requested fields are present and non-missing in the released HTP-MD table.\n- The current released PolyGen assets expose only scalar conductivity conditioning.\n- No multi-property checkpoint or joint surrogate is present, so generation, pairing, leakage, and publication claims remain pending.\n- `unsupported_cells.csv` explicitly records the joint-Q80 cell as audit-only pending the new model/surrogate.\n""")
    print(json.dumps({"output": str(OUT), "rows": len(d), "joint_q80_rows": int(train_mask.sum())}, indent=2))

if __name__ == "__main__":
    main()
