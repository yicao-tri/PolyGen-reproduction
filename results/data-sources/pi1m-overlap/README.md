# PI1M overlap audit provenance

This directory records the overlap audit between the HTP benchmark rows and
the external PI1M source used for the audit. The PI1M source file itself is
not redistributed in this repository.

## Source identity

- Expected source basename: `PI1M_v2.csv`
- Observed local path at audit time: `/tmp/pi1m/PI1M_v2.csv`
- SHA-256: `8b8d3ce5720d43a3c241385083aa34acfb8bf009b314cd4dc588f2d00ce9e77e`
- Source status: external, not committed here

The observed `/tmp` path is historical provenance only and is not a portable
reproduction path. A rerun requires obtaining the same source release or an
authorized equivalent, verifying the SHA-256 hash, and placing it at a local
path before running the audit.

## Recorded outputs

- `summary.json` contains row counts, parseability checks, split-specific
  overlap counts, and the top-20%-conductivity overlap count.
- `overlap_rows.csv` contains the compact overlap records used by the audit;
  it does not contain the full PI1M source table.

The overlap audit is provenance evidence only. It does not establish that the
external records are experimentally comparable to the benchmark, nor does it
provide a physical validation of generated candidates.
