# Full-atom MD handoff

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
