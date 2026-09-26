# Continuous-vs-binary PolyGen Layer 1/2 audit

Status: partial audit complete; new sensitivity execution is blocked by the current runtime.

- [x] Existing C1 five paired seeds kept separate from any new configuration.
- [x] Existing C1 raw and eligible counts audited at `arm × seed × target × config_id`.
- [x] Source hashes, git head, runtime and missing dependencies recorded.
- [x] Frozen ranking rule recorded: valid + novel + in-support + uncertainty gate, then `predicted_log_sigma - 1.96 * uncertainty`.
- [x] PFP/MD not started by this benchmark; Stage 3 requires explicit user sign-off.
- [ ] New sensitivity runs: temperature, training budget, and model-size grid.
- [ ] New runs with at least 1,000 raw samples per arm/config and immutable configs.
- [ ] Full Layer 1/2 metrics for each new arm/config, including synthesizability and buildable yield.
- [ ] Top-50 per arm/config and the three requested Pareto tables.

## Blocking items

1. Install/activate a compatible PyTorch runtime and the project's tokenizer dependency (`deepchem`), or provide an approved equivalent environment.
2. Confirm whether the only available model is `gpt-nano`; do not claim model-size sensitivity without a real larger checkpoint/training definition.
3. Freeze the exact sensitivity allocation and execute in a new output root, preserving `existing C1 evidence` and `new sensitivity evidence` labels.
4. Audit synthesizability/buildability definitions and required verifier inputs before interpreting those metrics.
5. Obtain user sign-off before any Stage 3 PFP/MD action.
