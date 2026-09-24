#!/usr/bin/env python3
"""Create honest, per-candidate full-atom MD handoff folders.

No force-field/system files are fabricated. Each folder remains blocked until
the p-SMILES-to-PCFF+ builder used by the original authors is supplied.
"""
from pathlib import Path
import argparse, json, shutil
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run',type=Path,required=True); a=ap.parse_args()
    src=a.run/'tables/md_candidates.csv'; out=a.run/'md_handoff'; out.mkdir(exist_ok=True)
    df=pd.read_csv(src)
    template=a.run.parents[1]/'vendor/PolyGen-1.0.0/Example-simulation-files'
    for i,row in df.reset_index(drop=True).iterrows():
        cid=f"{row.arm}_{i+1:03d}"; d=out/cid; d.mkdir(exist_ok=True)
        payload={k:(None if pd.isna(v) else v.item() if hasattr(v,'item') else v) for k,v in row.items()}
        payload.update({'candidate_id':cid,'status':'WAITING_FOR_SYSTEM_BUILD',
                        'required_replicas':5,'temperature_K':353,'production_ns':5,'timestep_fs':2,
                        'salt':'LiTFSI','salt_concentration_mol_per_kg':1.5,'force_field':'PCFF+'})
        (d/'candidate.json').write_text(json.dumps(payload,indent=2))
        (d/'STATUS.txt').write_text('WAITING_FOR_SYSTEM_BUILD\nNo publication builder/parameterization workflow is present in the public release.\n')
        for rel in ('equilibration/equilibration.in','production/production.in'):
            target=d/Path(rel).name; shutil.copy2(template/rel,target)
    (out/'README.md').write_text('''# Full-atom MD handoff

These 40 folders contain selected binary/continuous candidates and the public
LAMMPS input examples. They are **not runnable systems** yet: the official
public release does not include the publication p-SMILES → linear polymer →
PCFF+ parameterization builder. Do not substitute a generic topology silently.

Required completion per candidate: construct a linear homopolymer with at least
150 backbone heavy atoms; add LiTFSI at 1.5 mol kg⁻¹; parameterize PCFF+; run the
published sequential NVT/NPT equilibration; launch five independent 353 K NVT
replicas for 5 ns with a 2 fs step; compute conductivity with the cluster
Nernst–Einstein analysis; record failures as failures. Aggregate replicate mean,
SD and 95% interval, then compare requested vs MD conductivity for binary and
continuous arms using the same predeclared criteria.
''')

if __name__=='__main__': main()
