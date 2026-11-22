# PolyGen evidence index

Rebuild: `python3 registry/build_registry.py` (standard-library Python only).
Read: `sqlite3 -readonly registry/output/polygen_evidence.sqlite 'SELECT * FROM claims;'`.
Registered queries and their interpretation boundaries are in `query_catalog`; exact query outputs and snapshot hash are in `output/build_receipt.json`.

No pre-existing scoped SQL registry was found. This new index registers compact evidence snapshots and exact CSV text with source hashes. It is not the scientific results master and not the external handoff tracking database. Original results and immutable archives remain the evidence sources. No absent result is imputed as zero. The source-copy manifest locates excluded checkpoints and large files in the full archive. Rebuild is deterministic; database integrity, named query columns and a second-build snapshot equality are checked in handoff validation.
