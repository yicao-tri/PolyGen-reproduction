#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "evidence/obsidian/multi-property-true-extrapolation"
files = []
for p in sorted(root.rglob("*")):
    if p.is_file() and p.name != "PACKAGE_MANIFEST.json":
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        files.append({"path": str(p.relative_to(root)), "bytes": p.stat().st_size, "sha256": h})
(root / "PACKAGE_MANIFEST.json").write_text(json.dumps({"package": root.name, "files": files}, indent=2) + "\n")
print(f"WROTE {len(files)} file hashes")
