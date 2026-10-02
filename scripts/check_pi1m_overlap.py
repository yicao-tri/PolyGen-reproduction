#!/usr/bin/env python
"""PI1M vs HTP-MD overlap / leakage check (exact canonical structure match).

HTP-MD monomers use [Au]/[Cu] as the two chain-end dummy atoms; PI1M uses '*'.
Both are mapped to '*' and canonicalised with RDKit. Inputs are read from disk;
PI1M_v2.csv is downloaded from github.com/RUIMINMA1996/PI1M (MIT, academic use).
"""
import argparse, json, hashlib, pathlib
import pandas as pd
from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")

def canon(smi, htp=False):
    if not isinstance(smi, str): return None
    if htp: smi = smi.replace("[Au]", "*").replace("[Cu]", "*")
    m = Chem.MolFromSmiles(smi)
    if m is None: return None
    return Chem.MolToSmiles(m)

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

ap = argparse.ArgumentParser()
ap.add_argument("--pi1m", required=True)
ap.add_argument("--out", default="results/data-sources/pi1m-overlap")
a = ap.parse_args()
out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)

src = pd.read_csv("inputs/release-data/PolyGen-train-set-from-HTP-MD.csv")
tr = pd.read_csv("results/upper-tail/train_rows.csv")
lk = pd.read_csv("results/upper-tail/locked_tail_rows.csv")
src["canon"] = [canon(s, True) for s in src.mol_smiles]
split = {}
for df, name in ((tr, "train_leq_Q80"), (lk, "locked_Q80_to_Q95")):
    for i in df.source_row_id: split[int(i)] = name
src["split"] = [split.get(int(i), "above_Q95_or_unassigned") for i in src.sample_id] \
    if False else [split.get(i, "above_Q95_or_unassigned") for i in range(len(src))]

pi = pd.read_csv(a.pi1m)
pi["canon"] = [canon(s) for s in pi.SMILES]
n_bad = int(pi.canon.isna().sum())
pi_valid = pi.dropna(subset=["canon"])
pi_set = set(pi_valid.canon)

src["in_pi1m"] = src.canon.isin(pi_set)
# lowest-rung caveat: same repeat unit written with ends swapped is already handled by canonical '*' form
summary = {
    "pi1m_file": a.pi1m, "pi1m_sha256": sha(a.pi1m), "pi1m_rows": len(pi),
    "pi1m_unparseable": n_bad, "pi1m_unique_canonical": len(pi_set),
    "htp_rows": len(src), "htp_unparseable": int(src.canon.isna().sum()),
    "htp_unique_canonical": int(src.canon.nunique()),
    "htp_exact_overlap_rows": int(src.in_pi1m.sum()),
    "by_split": {k: {"rows": int(len(g)), "in_pi1m": int(g.in_pi1m.sum())}
                 for k, g in src.groupby("split")},
}
# does PI1M overlap concentrate in high-conductivity rows?
hi = src[src.conductivity >= src.conductivity.quantile(0.8)]
summary["overlap_in_top20pct_conductivity"] = int(hi.in_pi1m.sum())
src[src.in_pi1m][["sample_id", "mol_smiles", "conductivity", "split", "canon"]].to_csv(out / "overlap_rows.csv", index=False)
(out / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
