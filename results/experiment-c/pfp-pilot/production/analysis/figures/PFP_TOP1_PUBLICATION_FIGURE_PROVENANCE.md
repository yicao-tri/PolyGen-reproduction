# Provenance: PFP top-1 publication figure

## Purpose

This figure is a publication-style summary of the already completed paired
PFP/HTP-MD top-1 pilot. It is intended to make the workflow result reviewable;
it does not replace the raw trajectory evidence or upgrade the one-replica
200-ps pilot to a converged transport estimate.

## Inputs

- `../paired/paired_results.csv`: final paired PFP and RF-proxy values,
  trajectory SHA-256 fingerprints, frame counts, temperatures, diffusivities,
  cNE conductivity, residuals, and convergence labels.
- `../continuous/convergence.csv` and `../binary/convergence.csv`: cumulative
  window cNE estimates at 20, 40, 80, 120, and 160 ps.
- `../../SHA256SUMS`: fingerprints for the committed evidence package and
  remote-only production artifacts.
- `PFP_TOP1_PUBLICATION_FIGURE_CAPTION.md`: manuscript-ready caption and claim
  boundary.

## Reproduction command

From the repository root:

```bash
python3 scripts/render_pfp_top1_publication_figure.py
```

The command writes `pfp_top1_publication_figure.svg`, `.pdf`, and `.png` to
this directory. The script reads the committed CSV files; it does not contain
trajectory values or synthetic uncertainty estimates.

## Source and pairing

The continuous trajectory fingerprint is
`c8a920f0bc0cc7bc0f52f7272860b134e345cd9b81c931938ec8d89f1376a57f` and the
binary fingerprint is
`5e92e931ec697ba03340286c4d4684fc874f01e0b0a1a30cc9a14ecd5d98d234`. Both
trajectories contain 2,001 frames over 200 ps. The final reported values use
the final 160 ps after a 40 ps discard. The two arms are compared as one
matched continuous/binary top-1 pair, not as replicated populations.

## Interpretation boundary

The figure supports technical completion and directional comparison: the
continuous candidate has higher PFP cNE conductivity in this pilot and the RF
proxy preserves that ordering. It does not support a converged absolute
conductivity claim, an experimental-error estimate, a general superiority claim,
or a multi-candidate effect size. The pilot remains
`NON_CONVERGED_SMOKE_ONLY`; the next stage requires concentration matching,
multiple independent replicas, and ns-scale production trajectories.
