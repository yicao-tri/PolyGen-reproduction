#!/usr/bin/env python3
"""Audit finite checkpoints and validation metrics for an epoch sweep."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import torch


def finite_state_dict(state_dict: dict) -> bool:
    for value in state_dict.values():
        if torch.is_tensor(value) and not bool(torch.isfinite(value).all()):
            return False
    return True


def audit_seed(path: Path, seed: int, epochs: int) -> dict:
    checkpoints = sorted(path.glob(f"last_c1_extended{epochs}_seed{seed}_*.pth"))
    rows = []
    all_finite = True
    for checkpoint in checkpoints:
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        finite = finite_state_dict(payload["model_state_dict"])
        all_finite = all_finite and finite
        rows.append({
            "epoch": int(payload["epoch"]),
            "checkpoint": checkpoint.name,
            "finite": finite,
            "mean_val_loss": float(payload["mean_val_loss"]),
            "nonterm_top1": float(payload["nonterm_top1"]),
            "best_val_loss": float(payload["best_val_loss"]),
        })
    rows.sort(key=lambda row: row["epoch"])
    best = min(rows, key=lambda row: row["mean_val_loss"]) if rows else None
    final = rows[-1] if rows else None
    return {
        "training_seed": seed,
        "checkpoint_count": len(rows),
        "expected_checkpoint_count": epochs,
        "all_checkpoints_finite": all_finite and len(rows) == epochs,
        "best_epoch": best["epoch"] if best else None,
        "best_val_loss": best["mean_val_loss"] if best else None,
        "best_nonterm_top1": best["nonterm_top1"] if best else None,
        "final_epoch": final["epoch"] if final else None,
        "final_val_loss": final["mean_val_loss"] if final else None,
        "final_nonterm_top1": final["nonterm_top1"] if final else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[17, 23, 31, 47, 59])
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    args = parser.parse_args()

    rows = [audit_seed(args.root / f"seed{seed}" / "checkpoints", seed, args.epochs) for seed in args.seeds]
    frame = pd.DataFrame(rows)
    frame.to_csv(args.summary_csv, index=False)
    audit = {
        "status": "finite_checkpoint_audit_pass" if all(row["all_checkpoints_finite"] for row in rows) else "finite_checkpoint_audit_fail",
        "epochs": args.epochs,
        "training_seeds": args.seeds,
        "all_checkpoints_finite": all(row["all_checkpoints_finite"] for row in rows),
        "rows": rows,
    }
    args.audit_json.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
