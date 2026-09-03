# Actual KO-POCHI / ARC DEV end-to-end probe

All values in this record were observed from live HTTP responses by scripts/probe_kozo_dev.py.

- Core database chain passed: `true`
- Every launcher health URL was reachable: `true`
- Every launcher entry was semantically healthy: `true`
- Full launcher aggregate passed: `true`

## Launcher health matrix

| App | Health path | HTTP reachable | Semantic health | Status fields | Error fields |
|---|---|---:|---:|---|---|
| KO-POCHI | `/health` | true | true | `{"status": "healthy"}` | `{}` |
| CL-POCHI | `/health` | true | true | `{"status": "healthy"}` | `{}` |
| SO-POCHI | `/health` | true | true | `{"status": "healthy"}` | `{}` |
| PI-POCHI | `/health` | true | true | `{"status": "healthy"}` | `{}` |
| BI-POCHI | `/build-api/health` | true | true | `{"status": "ok"}` | `{}` |
| SS-POCHI | `/arc-api/health` | true | true | `{"status": "ok"}` | `{}` |
| MD-POCHI | `/arc-md-api/api/md/health` | true | true | `{"mcpServerStatus": "operational", "status": "ok"}` | `{}` |

## Database and structure path

- Query: `Li-Fe-P-O`
- Backend/gateway user responses equal: `true`
- Expected user match: `[{"id": "yi_cao", "name": "Yi Cao"}]`
- Search HTTP status: `200`
- Search reported total: `15493`
- Search returned rows: `50`
- First result: `{"energy": -5590.5205078125, "formula": "Fe2Li2O8P2", "nsites": 14, "original_id": 11723, "source": 6}`
- CIF HTTP status: `200`
- CIF bytes/lines: `1066` / `38`
- CIF contains atom-site fields: `true`

This report is regenerated from `results/dev/kozo-dev-e2e-probe.json`; it is not manually maintained.
