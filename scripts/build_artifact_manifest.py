#!/usr/bin/env python3
"""Hash every package file except the manifest itself."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "tables" / "artifact_manifest.csv"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    paths = sorted(path for path in ROOT.rglob("*") if path.is_file() and path != OUTPUT and "__pycache__" not in path.parts)
    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        for path in paths:
            writer.writerow({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)})
    print(f"WROTE {OUTPUT.relative_to(ROOT)} with {len(paths)} entries")


if __name__ == "__main__":
    main()
