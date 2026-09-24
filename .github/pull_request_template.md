## Blueprint position

- Primary stage (`S0`–`S7`):
- Exploratory branch ID, if any:
- Stage before this PR:
- Stage after this PR:
- Blueprint/status files updated: [ ] yes [ ] no — explain if no

## Research question

What precise question does this PR answer? State the estimand or engineering gate,
not only the implementation task.

## Article mapping

- Manuscript section(s):
- Figure/table/supplement item(s):
- PolyGen original-paper experiment aligned or extended:
- Claim tier affected: [ ] executable [ ] offline-controlled [ ] physically validated [ ] system-level controlled [ ] self-improving

## Work completed

- Code/data/protocol changes:
- Experiment arms, budgets, seeds, and splits:
- Statistical unit and analysis method:
- Exact output artifacts:

## Findings

- Positive findings:
- Null or negative findings:
- Unexpected observations:
- Does this change any manuscript-ready claim? If yes, quote old and proposed wording.

## Interpretation and discussion

- What the evidence supports:
- What it does not support:
- Main limitations or alternative explanations:
- Points requiring deeper investigation:

## Exploratory work

- Is a separate exploratory branch needed? [ ] no [ ] yes
- Proposed branch name and question:
- Why it must remain separate from the frozen primary analysis:
- Rule for accepting/rejecting it into the main blueprint:

## Acceptance evidence

- Stage checklist items closed by this PR:
- Commands/tests/verification run:
- Provenance, hashes, or manifests:
- Protocol deviations or failed runs retained:

## Next blueprint target

- Remaining blocker in the current stage:
- Concrete next experiment or gate:
- Expected paper contribution if successful:

## Safety checks

- [ ] No generated candidate or trajectory frame was treated as an independent biological-style replicate.
- [ ] No frozen split, cohort, primary estimand, or analysis rule changed silently.
- [ ] Failed builds/runs remain visible in denominators.
- [ ] New physical/discovery wording is backed by MD or experimental evidence.
- [ ] `scripts/validate_research_blueprint.py` passes.
