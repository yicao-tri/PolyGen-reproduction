#!/usr/bin/env python3
"""Validate the machine-readable research blueprint and its evidence links."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "research/blueprint/status.json"
ALLOWED = {"complete", "current", "planned", "blocked", "superseded"}
EXPECTED = [f"S{i}" for i in range(8)]


def main() -> None:
    errors: list[str] = []
    data = json.loads(STATUS.read_text())
    stages = data.get("stages", [])
    ids = [stage.get("id") for stage in stages]
    if ids != EXPECTED:
        errors.append(f"stage ids/order must be {EXPECTED}, found {ids}")
    current = [stage["id"] for stage in stages if stage.get("status") == "current"]
    if current != [data.get("current_stage")]:
        errors.append(f"exactly one current stage must match current_stage: {current}")
    for stage in stages:
        if stage.get("status") not in ALLOWED:
            errors.append(f"{stage.get('id')}: invalid status {stage.get('status')}")
        for key in ("name", "paper_sections", "evidence", "blockers", "next_target"):
            if key not in stage:
                errors.append(f"{stage.get('id')}: missing {key}")
        for evidence in stage.get("evidence", []):
            if not (ROOT / evidence).exists():
                errors.append(f"{stage.get('id')}: missing evidence path {evidence}")
    if not (ROOT / data.get("canonical_blueprint", "")).is_file():
        errors.append("canonical_blueprint does not exist")
    if errors:
        print("Research blueprint validation: FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Research blueprint validation: PASS ({len(stages)} stages; current={current[0]})")


if __name__ == "__main__":
    main()
