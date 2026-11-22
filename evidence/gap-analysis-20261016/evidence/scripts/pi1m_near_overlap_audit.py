#!/usr/bin/env python3
"""Exploratory PI1M near-duplicate audit against the HTP benchmark.

The audit uses Morgan radius-2 fingerprints (2048 bits) and an inverted-bit
candidate index.  It reports a heuristic candidate set, followed by exact
Tanimoto evaluation.  Because the anchor index is intentionally bounded, the
result is not a proof of absence: the output is marked exploratory and must
not replace a preregistered near-duplicate definition.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from array import array
from collections import defaultdict
from pathlib import Path

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator


N_BITS = 2048
RADIUS = 2
RDLogger.DisableLog("rdApp.*")
MORGAN_GENERATOR = rdFingerprintGenerator.GetMorganGenerator(
    radius=RADIUS, fpSize=N_BITS
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_smiles(value: str) -> str:
    return value.replace("[Au]", "*").replace("[Cu]", "*")


def fingerprint(value: str):
    molecule = Chem.MolFromSmiles(normalize_smiles(value))
    if molecule is None:
        return None
    return MORGAN_GENERATOR.GetFingerprint(molecule)


def canonical(value: str):
    molecule = Chem.MolFromSmiles(normalize_smiles(value))
    return Chem.MolToSmiles(molecule) if molecule is not None else None


def read_htp(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            smiles = row.get("mol_smiles") or row.get("SMILES")
            fp = fingerprint(smiles or "")
            rows.append({
                "row_index": index,
                "sample_id": row.get("sample_id") or row.get("Unnamed: 0") or str(index),
                "smiles": smiles,
                "conductivity": row.get("conductivity"),
                "fp": fp,
                "canonical": canonical(smiles or ""),
            })
    return rows


def pi_smiles(row: dict) -> str:
    return row.get("SMILES") or row.get("smiles") or row.get("mol_smiles") or ""


def build_index(path: Path, sample_stride: int) -> tuple[list[array], list[int], int, int, int]:
    index = [array("I") for _ in range(N_BITS)]
    counts = [0] * N_BITS
    rows = 0
    sampled_rows = 0
    parse_failures = 0
    with path.open(newline="") as handle:
        for row_id, row in enumerate(csv.DictReader(handle)):
            rows += 1
            if row_id % sample_stride != 0:
                continue
            sampled_rows += 1
            fp = fingerprint(pi_smiles(row))
            if fp is None:
                parse_failures += 1
                continue
            for bit in fp.GetOnBits():
                index[bit].append(row_id)
                counts[bit] += 1
            if rows % 100000 == 0:
                print(f"indexed PI1M rows: {rows}")
    return index, counts, rows, sampled_rows, parse_failures


def candidate_map(htp_rows: list[dict], index: list[array], counts: list[int], anchor_count: int, min_shared: int):
    row_to_queries: dict[int, list[int]] = defaultdict(list)
    candidate_counts = []
    for query_id, row in enumerate(htp_rows):
        if row["fp"] is None:
            candidate_counts.append(0)
            continue
        bits = sorted(row["fp"].GetOnBits(), key=lambda bit: counts[bit])[:anchor_count]
        shared: dict[int, int] = defaultdict(int)
        for bit in bits:
            for pi_row_id in index[bit]:
                shared[pi_row_id] += 1
        chosen = [pi_row_id for pi_row_id, count in shared.items() if count >= min_shared]
        candidate_counts.append(len(chosen))
        for pi_row_id in chosen:
            row_to_queries[pi_row_id].append(query_id)
    return row_to_queries, candidate_counts


def evaluate(path: Path, htp_rows: list[dict], row_to_queries: dict[int, list[int]]) -> list[dict]:
    best = [
        {
            "max_tanimoto": -1.0,
            "pi_row_id": None,
            "pi_smiles": None,
            "pi_canonical": None,
        }
        for _ in htp_rows
    ]
    with path.open(newline="") as handle:
        for row_id, row in enumerate(csv.DictReader(handle)):
            queries = row_to_queries.get(row_id)
            if not queries:
                continue
            pi_fp = fingerprint(pi_smiles(row))
            if pi_fp is None:
                continue
            for query_id in queries:
                similarity = float(DataStructs.TanimotoSimilarity(htp_rows[query_id]["fp"], pi_fp))
                if similarity > best[query_id]["max_tanimoto"]:
                    best[query_id] = {
                        "max_tanimoto": similarity,
                        "pi_row_id": row_id,
                        "pi_smiles": pi_smiles(row),
                        "pi_canonical": canonical(pi_smiles(row)),
                    }
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--pi1m", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--anchor-count", type=int, default=16)
    parser.add_argument("--min-shared", type=int, default=4)
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--sample-stride", type=int, default=10)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Use the release table that carries the stable sample_id used by the
    # exact-overlap provenance audit; htpmd-trainset.csv is a richer row table
    # with a different ordering.
    htp_path = args.canonical_root / "inputs/release-data/PolyGen-train-set-from-HTP-MD.csv"
    htp_rows = read_htp(htp_path)
    index, counts, pi_rows, pi_sampled_rows, pi_parse_failures = build_index(
        args.pi1m, args.sample_stride
    )
    row_to_queries, candidate_counts = candidate_map(
        htp_rows, index, counts, args.anchor_count, args.min_shared
    )
    best = evaluate(args.pi1m, htp_rows, row_to_queries)

    records = []
    for htp, match, candidates in zip(htp_rows, best, candidate_counts):
        records.append({
            "htp_row_index": htp["row_index"],
            "sample_id": htp["sample_id"],
            "conductivity": htp["conductivity"],
            "max_morgan_tanimoto": match["max_tanimoto"] if match["pi_row_id"] is not None else None,
            "pi1m_row_id": match["pi_row_id"],
            "pi1m_smiles": match["pi_smiles"],
            "exact_canonical_match": (
                match["pi_canonical"] is not None
                and match["pi_canonical"] == htp["canonical"]
            ),
            "candidate_count": candidates,
        })
    with (args.output_dir / "htp_nearest_matches.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    similarities = sorted(
        record["max_morgan_tanimoto"]
        for record in records
        if record["max_morgan_tanimoto"] is not None
    )
    summary = {
        "status": "exploratory_near_overlap_complete",
        "htp_rows": len(htp_rows),
        "htp_parse_failures": sum(row["fp"] is None for row in htp_rows),
        "pi1m_rows": pi_rows,
        "pi1m_sampled_rows": pi_sampled_rows,
        "pi1m_sampling_rule": f"systematic row_id % {args.sample_stride} == 0",
        "pi1m_parse_failures": pi_parse_failures,
        "pi1m_sha256": sha256(args.pi1m),
        "fingerprint": {"family": "Morgan", "radius": RADIUS, "n_bits": N_BITS},
        "candidate_index": {
            "anchor_count": args.anchor_count,
            "min_shared": args.min_shared,
            "mean_candidates_per_htp": sum(candidate_counts) / len(candidate_counts),
            "max_candidates_per_htp": max(candidate_counts),
        },
        "threshold": args.threshold,
        "sampled_near_overlap_rows_at_or_above_threshold": int(
            sum(
                record["max_morgan_tanimoto"] is not None
                and record["max_morgan_tanimoto"] >= args.threshold
                for record in records
            )
        ),
        "sampled_nonexact_near_overlap_rows_at_or_above_threshold": int(
            sum(
                record["max_morgan_tanimoto"] is not None
                and record["max_morgan_tanimoto"] >= args.threshold
                and not record["exact_canonical_match"]
                for record in records
            )
        ),
        "similarity_quantiles": {
            str(q): float(similarities[int(q * (len(similarities) - 1))])
            for q in (0.5, 0.9, 0.95, 0.99)
        },
        "interpretation": "Systematic PI1M sample plus heuristic candidate retrieval; no absence claim is valid for HTP rows whose nearest candidate was not retrieved or whose near match fell outside the sample. Exact PI1M overlap remains separately reported in the canonical audit.",
        "source_is_external_not_redistributed": True,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
