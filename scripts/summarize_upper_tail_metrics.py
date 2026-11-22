#!/usr/bin/env python3
"""Create a complete publication-facing metric table without changing estimands."""
import csv, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/upper-tail/metrics_by_cell.csv"
OUT = ROOT / "results/upper-tail/publication/upper_tail_all_metrics.csv"

metrics = [
    "validity", "novelty", "uniqueness", "diversity", "failure_rate",
    "target_mae", "strict_hit_rate", "rf_prediction_mean",
    "rf_uncertainty_mean", "support_mean", "support_eligible_rate",
    "upper_tail_predicted_hit_rate",
]

with IN.open(newline="") as f:
    rows = list(csv.DictReader(f))

groups = {}
for row in rows:
    groups.setdefault((row["arm"], row["target_label"]), []).append(row)

out = []
for (arm, target_label), group in groups.items():
    result = {"arm": arm, "target_label": target_label, "target": group[0]["target"], "n_seeds": len(group)}
    for metric in metrics:
        values = []
        for row in group:
            value = row.get(metric, "")
            if value not in ("", "nan", "NaN"):
                try:
                    values.append(float(value))
                except ValueError:
                    pass
        result[metric] = sum(values) / len(values) if values else ""
        if len(values) > 1:
            mean = result[metric]
            sd = math.sqrt(sum((x - mean) ** 2 for x in values) / (len(values) - 1))
            result[metric + "_sem"] = sd / math.sqrt(len(values))
        else:
            result[metric + "_sem"] = ""
    out.append(result)

fields = list(out[0])
with OUT.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(out)
print(OUT)
