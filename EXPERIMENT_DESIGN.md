# Frozen paired experiment design

Primary question: holding PolyGen's HTP-MD rows, 80/20 split (seed 42), gpt-nano architecture, 64-token context, five-position prefix, optimizer, training budget, temperature, and sampling budget fixed, does a scalar log10 conductivity prefix produce valid/novel p-SMILES across requested conductivity values?

Arms: (A) released binary high-conductivity token repeated five times; (B) continuous log10(S/cm), standardized on the training fold and mapped by a two-layer MLP to a five-position soft prefix. Both are trained from the same random initialization seed for 10,000 optimizer steps. The binary discovery prompt is HIGH. The continuous arm is sampled at training-fold q05, q50, and q95.

Primary metrics: RDKit validity plus exactly one single-bonded [Cu] and [Au] endpoint, novelty against the training fold, uniqueness, and generated-set Morgan-fingerprint diversity. These are generation-quality metrics, not physical validation.

Final physical validation boundary: candidates must be screened and then run through the paper's full-atom PCFF+/LAMMPS protocol. The public release does not include the publication GNN predictor checkpoint or a turnkey structure/force-field construction workflow for arbitrary new p-SMILES, so surrogate predictions cannot be called final validation.
