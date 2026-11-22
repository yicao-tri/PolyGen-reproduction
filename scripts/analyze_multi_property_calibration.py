#!/usr/bin/env python3
"""Create locked-row surrogate calibration tables; no MD values are inferred."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/multi-property/extrapolation"
PROPS = ["conductivity", "li_diffusivity", "tfsi_diffusivity", "poly_diffusivity", "transference_number", "molality"]
rows = pd.read_csv(OUT / "locked_tail_verifier_audit.csv")
manifest = json.loads((OUT / "frozen_manifest.json").read_text())
maxima = manifest.get("joint_training_maxima", {})
out = []
for prop in PROPS:
    obs, pred, unc = rows[f"observed_{prop}"], rows[f"predicted_{prop}"], rows[f"uncertainty_{prop}"]
    ok = np.isfinite(obs) & np.isfinite(pred)
    err = pred - obs
    for label, mask in [("all", ok), ("support_lt_0.35", ok & (rows.support < .35)), ("support_0.35_0.5", ok & rows.support.ge(.35) & rows.support.lt(.5)), ("support_ge_0.5", ok & (rows.support >= .5))]:
        e = err[mask]
        u = unc[mask]
        out.append({"property": prop, "stratum": label, "n": int(mask.sum()), "bias_pred_minus_observed": float(e.mean()) if len(e) else np.nan, "mae": float(np.abs(e).mean()) if len(e) else np.nan, "rmse": float(np.sqrt(np.mean(e * e))) if len(e) else np.nan, "coverage_abs_error_le_2tree_sd": float((np.abs(e) <= 2 * u).mean()) if len(e) else np.nan, "md_residual_status": "unavailable_no_md"})
cal = pd.DataFrame(out)
cal.to_csv(OUT / "locked_surrogate_calibration.csv", index=False)
summary = {"status": "surrogate_only", "rows": int(len(rows)), "properties": PROPS, "md_calibration": "unavailable_no_md", "residual_definition": "log_sigma_MD - log_sigma_RF; unavailable because MD was not run"}
(OUT / "locked_surrogate_calibration.json").write_text(json.dumps(summary, indent=2) + "\n")
print(cal.to_string(index=False))
