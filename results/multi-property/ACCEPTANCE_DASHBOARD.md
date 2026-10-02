# Multi-property acceptance dashboard

All three regions pass the frozen prediction-phase controls: source/split/target/scaler records, explicit six-property transforms, matched arms and seeds, candidate-level provenance, unsupported/failure reporting, surrogate/MD separation, and paired identity/leakage audits where the regional verifier is available.

The common MD gate is not complete. MD-confirmed frontier crossing and `logσ_MD − logσ_RF` residual calibration are unavailable because no symmetric PCFF+ MD run has been accepted. Extrapolation additionally has a 48-slot stratified MD proposal with unsupported slots retained; it is planned, not run.

Use `ACCEPTANCE_DASHBOARD.json` for machine-readable status and the regional evidence packages for numeric claims. No surrogate frontier crossing should be described as true physical extrapolation.

The interpolation Nature-style evidence package is tracked at `evidence/obsidian/multi-property-interpolation-milestone/`; its package validator passes with zero warnings and includes the derived paired-effect, monotonicity, diversity and failure-mode audit. The cross-region Obsidian index is `evidence/obsidian/Multi-property benchmark — acceptance index.md`.
