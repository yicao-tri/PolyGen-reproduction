# Figure caption

**Signed target deviation distributions under the Q80 training boundary.**
Each vertical panel corresponds to one requested target: the actual Q80
training boundary, Q85, Q90, and Q95. The horizontal axis is the signed
difference between the RF prediction for a generated polymer unit and its
requested target, in log10(S cm−1); negative values indicate under-target
prediction and zero indicates exact target agreement. Curves show the median
kernel density estimate across five matched seeds, with ribbons representing
the seed-level 10–90% range. The `valid n/N` annotations report how many
candidates entered the density estimate out of the full cell budget; invalid
outputs are not silently treated as zero deviation. Vertical grey reference
lines mark absolute deviations of 0.10, 0.25, and 0.50, and the black dashed
line marks zero deviation.

The primary figure uses the Q80-only blind RF, trained on the 4,819 rows at or
below the frozen Q80 boundary. Candidate rows are from
`results/upper-tail/candidate_predictions.csv`; target labels and cell budgets
come from the frozen Upper-tail manifest. The companion full-source RF audit
uses the same generated candidates but an RF trained on all source rows,
including the locked Q80–Q95 tail; it is therefore post-hoc and is not used as
independent evidence of extrapolation.

The density curves summarize verifier-level target deviation only. They do not
represent MD or experimental conductivity, and the figure does not establish
validated frontier crossing.
