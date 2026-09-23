#!/usr/bin/env python3
"""Audit released leakage and materialize corrected split evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mingpt_split import build_split


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source = args.input.resolve()
    released = build_split(source, "released-random", seed=args.seed)
    corrected = build_split(source, "structure-disjoint", seed=args.seed)
    report = {
        "claim": "The released balanced rows are split after positive structures were duplicated.",
        "source": str(source),
        "source_sha256": digest(source),
        "released_random": released.metadata,
        "structure_disjoint": corrected.metadata,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
