# MolMiner × PolyGen apple-to-apple generation comparison

Status: design frozen for the first reproducibility pass; definitive runs wait
for a real MolMiner checkpoint file.

## Primary question

Can Raul's released polymer MolMiner package generate valid polymer repeat units
for the same conductivity-conditioning query points used in the PolyGen C1
generation experiment, and how do its output support, validity, novelty, size,
and conditional response differ from PolyGen?

The first pass is a generation-behaviour comparison. It is not yet a matched
held-out performance claim because the available MolMiner checkpoint was
trained on the merged corpus, which includes the HTP-MD source used by PolyGen.

## Comparison arms and pairing

| Arm | Model | Conditioning | Query points | Samples |
| --- | --- | --- | --- | --- |
| `polygen_binary` | PolyGen gpt-nano soft-prefix | HTP-MD high/low split at `-4.0` | `-5.0`, `-4.0`, `-3.0` log10 S/cm | 100/query × seed |
| `polygen_continuous` | PolyGen gpt-nano soft-prefix | continuous log10 conductivity | same | 100/query × seed |
| `molminer_continuous` | MolMiner polymer checkpoint | continuous `log_conductivity` | same | 100/query × seed |

The PolyGen pairing unit remains `arm × seed × target × config_id`; the MolMiner
run is paired to the same target list and sample allocation, but not to the
same model seed stream because the two decoders have different random-state
consumption and action spaces. The primary cross-model contrast is descriptive,
with PolyGen's existing paired binary/continuous contrast retained separately.

Frozen first-pass config:

- PolyGen fixed C1 split: `train_test_split(..., test_size=0.2,
  random_state=20260923, stratify=deciles of log conductivity)`.
- PolyGen model: `gpt-nano`, 1,000 optimizer steps, temperature 1.0.
- MolMiner checkpoint: Raul's `best_polyru_s42.pth` once the LFS object is
  available and its SHA-256 matches the pointer OID.
- MolMiner prompt: `{"log_conductivity": target}` only; all other properties
  withheld by the model's condition mask.
- Targets: `-5.0`, `-4.0`, `-3.0` log10 S/cm.
- Raw allocation: 100 generated requests per target, 300 per arm/run.
- MolMiner decoding: stochastic sampling, `greedy=False`, fixed per-target
  batch seeds derived from the run seed; `max_fragments=80`. This is a documented
  CPU-feasibility guard: over-limit trajectories are recorded as failures, not
  truncated or silently replaced. A later sensitivity arm can test 120/200.
- Primary repeat-unit validity: exactly two `*` endpoints and a sanitizing
  head-to-tail dimer, using `molminer.repeat_unit.validate`.
- Secondary diagnostics: canonical uniqueness/novelty against the MolMiner
  corpus, endpoint count, fragment count where available, backbone fraction,
  requested-target coverage, generated property distributions if a common
  verifier is applied, and rejection/docking statistics.

## Known confounds and controls

1. MolMiner's released checkpoint is trained on a merged 13,605-row corpus
   (HTP-MD, Tg, PI1070, Bicerano), whereas PolyGen C1 trains on the HTP-MD
   split. The released-checkpoint result is therefore labelled `pretrained /
   support-mismatched`.
2. MolMiner uses a fragment/action representation with geometry-aware 3-D
   context and legality checks; PolyGen emits SMILES-like tokens and validates
   after decoding. Validity is a representation diagnostic, not a pure model
   quality score.
3. MolMiner conditions on an unscaled continuous property through an empirical
   quantile transform and may marginalise unprompted properties. PolyGen's
   continuous arm uses a z-scored scalar prefix and its binary arm thresholds
   at `-4.0`. These are reported as interface differences.
4. A strict matched-train-support comparison requires a future MolMiner
   retraining arm on the exact PolyGen C1 training rows, with a held-out common
   verifier. That arm is planned but not silently substituted for the released
   checkpoint.

## Artifact contract

Each run must preserve: source commit, source-tree status, input hashes,
checkpoint hash, environment, full command, seed schedule, prompt schedule,
raw sample table, validity/rejection counts, and a machine-readable summary.
No result is considered complete from process exit alone.
