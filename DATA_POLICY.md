# Actual-data-only policy

This reproduction has one non-negotiable rule: scientific values in its tables,
figures, and summaries must come from a script reading a machine-readable raw
input or a file produced by a real model run.

The package therefore:

- never parses the article PDF or screenshots of its tables and figures;
- never transcribes an article or supplementary-table value into code or CSV;
- never hardcodes a publication result as a target assertion;
- preserves all rows and groups found in the raw inputs, including failed runs;
- reports actual run outputs even when they do not match publication results;
- treats missing checkpoints, predictions, and source arrays as unavailable data,
  not as permission to redraw reported values.
- permits only non-numeric bibliographic scope metadata (for example a figure or
  table identifier) to map coverage; this metadata is never used as a scientific
  input or comparison target.

`scripts/reproduce_actual_data.py` derives the raw-data tables and plots.
`scripts/summarize_actual_runs.py` derives the DEV execution summaries and plots.
`scripts/verify_package.py` recomputes both in memory and checks every file hash.
`scripts/generate_coverage_report.py` computes the scope status exclusively from
the files that are present under `inputs/` and `results/dev/`.

The article and its rendered pages are intentionally excluded from this
computational package. They may be consulted by a person as background, but no
package script has a path to them.
