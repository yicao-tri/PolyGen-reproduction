# Heartbeat monitor scope

Registered Codex heartbeat: `polygen` (`ACTIVE`, every 3 hours), attached to the current task.

Purpose: monitor readiness and state changes for the blocked physical-validation queue without launching, restarting, deleting, or modifying canonical jobs.

Canonical state files to inspect:

- `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/extrapolation/candidate_selection_for_md.csv`
- `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/experiment-c/md-validation/md_batch_manifest.csv`
- `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/experiment-c/md-validation/top1_readiness_audit.json`
- `/Users/yicao/Documents/ARC/PolyGen-reproduction/results/extrapolation/verification.json` when present

Notify only when one of these conditions changes:

- PCFF+ parameter coverage changes from FAIL to a complete, auditable PASS.
- The MD manifest changes from `PLANNED_NOT_RUN` to a terminal run state.
- A candidate/replica becomes convergence-qualified, or a run fails and needs owner action.
- The evidence package can be rebuilt with new real measurements.

When unchanged, remain silent. The monitor must not infer physical conductivity from RF output, treat the PFP smoke anchor as converged evidence, submit or restart remote work, or delete/rewrite canonical artifacts. Once a terminal complete/failed state is reported, pause the monitor pending owner review.
