#!/usr/bin/env python3
"""Refresh the package file manifest after a local evidence update."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.package_root.resolve()
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in {"PACKAGE_MANIFEST.json", ".DS_Store"}:
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        files.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "schema_version": "polygen-gap-package-v1",
        "generated_by": "evidence/scripts/refresh_package_manifest.py",
        "files": files,
    }
    (root / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"files": len(files), "manifest": str(root / "PACKAGE_MANIFEST.json")}))


if __name__ == "__main__":
    main()
