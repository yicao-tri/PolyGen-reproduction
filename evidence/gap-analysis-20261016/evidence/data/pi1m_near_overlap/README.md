# PI1M exploratory near-overlap audit

This directory contains a real-data exploratory screen against PI1M_v2.csv
(SHA-256 `8b8d3ce5720d43a3c241385083aa34acfb8bf009b314cd4dc588f2d00ce9e77e`).
The source is external and is not redistributed in this package.

Method: Morgan radius-2, 2,048-bit fingerprints; a systematic 1-in-10 PI1M
sample (99,580 of 995,799 rows); 16 rare-bit anchors with at least four shared
anchors; exact Tanimoto evaluation on retrieved candidates. At threshold 0.85,
21 HTP rows have a sampled candidate, of which 7 are canonical exact matches
and 14 are non-exact fingerprint-near candidates.

This is not an absence proof: near matches outside the systematic sample or
outside the bounded anchor candidate set are not excluded. A preregistered,
full-source near-duplicate audit is still required before claiming that the 59
exact overlaps have all been removed.
