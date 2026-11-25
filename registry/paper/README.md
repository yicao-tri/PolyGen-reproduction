# Paper coordination and typed results registry

This **extends project retrieval in a separate paper namespace**. The existing `registry/output/polygen_evidence.sqlite` remains immutable historical evidence; its schema, bytes and old claim gates are not overwritten. `registry/paper/output/paper_progress.sqlite` is the canonical index for this paper's stages, review decisions and versioned result summaries. It is not raw transport truth, a human approval service, or the old internship tracking database.

## Read now

```bash
python3 registry/paper/progress.py query stages
python3 registry/paper/progress.py query results
python3 registry/paper/progress.py query decisions
python3 registry/paper/progress.py query reviews
```

The five-stage dashboard has S1 **complete as design delivery**, human review **pending**, S2 blocked, S3 planned, S4 blocked, and S5 optional. The two historical C1 hit summaries do not complete the new S3 contract. There are no completed new-study results.

## Every new result: record, rebuild, review, commit

1. Keep raw output immutable; put a compact, reviewable source artifact/manifest under the appropriate repository evidence path. Preserve source SHA, units, conditions, independent unit, failures and interpretation. Do not put large trajectories/checkpoints into SQLite.
2. Write a JSON record based on `result_record.example.json` **outside `records/`**. Give it a new stable `record_id`, UTC `recorded_at`, unique result/observation/source IDs, source path and exact SHA-256. `record` computes the actual source size. Use `historical_context` versus `new_study`, and the correct evidence tier. Missing outcomes have `value: null` and a reason; never replace missing with zero.
3. Ingest once:

   ```bash
   python3 registry/paper/progress.py record --input /absolute/path/new-record.json
   python3 registry/paper/progress.py query results
   python3 registry/paper/progress.py query stages
   ```

   Input is validated against real repository files and hashes before an immutable record is published. Repeating the same input is idempotent. A reused ID with changed content is rejected; corrections use a **new** ID and `supersedes`, preserving the old row. The database is deterministically rebuilt via a temporary file and atomic replace. Invalid batches leave the prior database/records intact.
4. Read the result's interpretation boundary. Stage advancement is an explicit `stage_events` record with new evidence, not an automatic side effect of an improved metric. A scientific stage cannot complete solely on a design record; S4 additionally requires completed new physical evidence. Agent checks and human review are distinct rows. Human approval records require a real attestation file.
5. Run the focused registry tests and review/commit the immutable input plus derived SQLite, query outputs and build receipt in the result PR. Update the linked roadmap stage only when its acceptance is met. Do not alter frozen historical science to repair a summary.

No background job or automation was installed. The update protocol is part of each future result integration, not a claim that files appearing elsewhere are automatically ingested. Respect the repository/common-dir lock used by active project chats when mutating records or Git state.

## Schema and query contract

`schema.sql` contains source/asset hashes, data dictionary and named query catalog, stages and append-only events, proposed decisions, typed reviews, result sets and observations. Each observation records unit, independent sample count, optional replicate identity, confidence limits and explicit missingness. Conditions are per result set; physical records require temperature, salt, loading, DP and force field. No source-free or synthetic result silently becomes a physical conclusion.

```bash
python3 registry/paper/progress.py build
python3 -m unittest discover -s registry/paper/tests -v
```

The same inputs/schema under the same SQLite runtime produce the same database SHA. Build receipts record input hashes and counts. Read-only integrity, foreign-key and named-query checks are required. Binary reproducibility across different SQLite versions is not assumed. Stage 1 packaging adds its exact document source records in the stacked PR; the main-thread originals and prior registry are untouched.
