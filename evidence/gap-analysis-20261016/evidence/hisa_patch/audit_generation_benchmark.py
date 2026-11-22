#!/usr/bin/env python3
"""Audit existing C1 evidence and freeze the Layer 1/2 benchmark contract.

This script is deliberately analysis-only: it never launches generation, PFP, or MD.
"""
from pathlib import Path
import hashlib, json, platform, subprocess, sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/experiment-c/generation-benchmark-audit"
SEEDS = [17, 42, 202, 303, 907]
TARGETS = [-5.0, -4.0, -3.0]

def sha(path):
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def files():
    out=[]
    for seed in SEEDS:
        base = ROOT / ("results/experiment-c/c1" if seed in [17,42,907] else "results/experiment-c/extra-seeds/seeds202-303")
        for arm in ["binary", "continuous"]:
            out.append((arm, seed, base / f"{arm}-seed{seed}/samples.csv"))
    return out

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows=[]; file_audit=[]
    for arm, seed, path in files():
        d=pd.read_csv(path)
        elig=d.valid & d.novel & (d.support >= .35) & (d.uncertainty < .35)
        file_audit.append({"evidence_layer":"existing C1 evidence","arm":arm,"seed":seed,
          "config_id":"c1_gptnano_steps1000_temp1.0_raw300_seedtarget100",
          "source_file":str(path.relative_to(ROOT)),"raw_samples":int(len(d)),
          "valid_count":int(d.valid.sum()),"eligible_count":int(elig.sum()),"strict_hit_count":int(d.hit.sum()),
          "targets":sorted(d.target.unique().tolist()),"status":"audited"})
        d=d.copy(); d["arm"]=arm; d["seed"]=seed; d["config_id"]="c1_gptnano_steps1000_temp1.0_raw300_seedtarget100"; d["eligible"]=elig
        rows.append(d)
    raw=pd.concat(rows, ignore_index=True)
    raw.to_csv(OUT/"existing_c1_raw_with_identity.csv", index=False)
    pd.DataFrame(file_audit).to_csv(OUT/"existing_c1_file_audit.csv", index=False)
    metrics=[]
    for (arm,seed,target), g in raw.groupby(["arm","seed","target"], sort=True):
        valid=g[g.valid]
        pred=valid.predicted_log_sigma
        metrics.append({"evidence_layer":"existing C1 evidence","arm":arm,"seed":int(seed),"target":float(target),
          "config_id":g.config_id.iloc[0],"raw_n":int(len(g)),"validity":float(g.valid.mean()),
          "uniqueness":float(g.smiles[g.valid].nunique()/len(g)) if len(g) else np.nan,
          "novelty":float(g.novel.mean()),"similarity_in_support":float((g.support>=.35).mean()),
          "uncertainty_gate_rate":float((g.uncertainty<.35).mean()),"strict_hit_rate":float(g.hit.mean()),
          # A single target value has zero variance; correlation is not
          # defined within this group and must not be reported as a metric.
          "target_mae":float(g.target_error.mean()),"target_prediction_correlation":np.nan,
          "mean_uncertainty":float(g.uncertainty.mean()),"monotonicity_not_defined_at_single_target":True})
    m=pd.DataFrame(metrics); m.to_csv(OUT/"existing_c1_arm_seed_target_metrics.csv",index=False)
    def cross_target_corr(group):
        target = group["target"].to_numpy(dtype=float)
        pred = group["predicted_log_sigma"].to_numpy(dtype=float)
        mask = np.isfinite(target) & np.isfinite(pred)
        if mask.sum() < 2 or np.ptp(target[mask]) == 0.0 or np.ptp(pred[mask]) == 0.0:
            return np.nan
        return float(np.corrcoef(target[mask], pred[mask])[0, 1])

    arm_seed = m.groupby(["arm","seed"], as_index=False).agg(
        raw_n=("raw_n","sum"), validity=("validity","mean"),
        uniqueness=("uniqueness","mean"), novelty=("novelty","mean"),
        strict_hit_rate=("strict_hit_rate","mean"), target_mae=("target_mae","mean"),
        mean_uncertainty=("mean_uncertainty","mean"),
    )
    raw_corr = raw.groupby(["arm", "seed"], as_index=False).apply(
        cross_target_corr, include_groups=False
    ).rename(columns={None: "target_prediction_correlation"})
    arm_seed = arm_seed.merge(raw_corr, on=["arm", "seed"], how="left")
    arm_seed.to_csv(OUT/"existing_c1_arm_seed_metrics.csv",index=False)
    targets=raw.groupby(["arm","target"],as_index=False).agg(
        predicted_mean=("predicted_log_sigma","mean"),
        strict_hit_rate=("hit","mean"),
        target_mae=("target_error","mean"),
    )
    targets.to_csv(OUT/"existing_c1_target_summary.csv",index=False)
    contract={"status":"FROZEN_AUDIT_ONLY_PENDING_EXECUTION","primary_arms":["binary","continuous"],"generator":"vendor/PolyGen-1.0.0/minGPT with scripts/run_experiment_c1.py semantics","model_size":"gpt-nano only; no larger checkpoint available; no fabricated sensitivity","paired_seeds":SEEDS,"targets_log10_S_cm":TARGETS,"temperatures":[1.0,0.8,1.2],"training_steps":[1000,2000],"raw_allocation":{"per_arm_config":1000,"per_seed_arm_config":200,"per_target":int(200/3),"allocation_note":"exact integer allocation must be frozen before launch; use 334/333/333 per arm/config if one config is run with one seed"},"identity_key":"evidence_layer x arm x seed x target x config_id","primary_ranking":"valid AND novel AND support>=0.35 AND uncertainty<0.35; sort predicted_log_sigma - 1.96*uncertainty descending; top 50 per arm/config","secondary_pareto":["predicted_log_sigma x novelty","predicted_log_sigma x diversity","predicted_log_sigma x synthesizability"],"no_pfp_md":True,"stage_3":"requires explicit user sign-off; this package does not authorize or execute PFP/MD","new_sensitivity_status":"NOT_EXECUTED: torch and deepchem unavailable in current runtime; no released larger model checkpoint"}
    (OUT/"FROZEN_GENERATION_CONTRACT.json").write_text(json.dumps(contract,indent=2)+"\n")
    env={"python":sys.version,"platform":platform.platform(),"cwd":str(ROOT),"git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"packages":{}}
    for mod in ["torch","deepchem","pandas","numpy","rdkit","sklearn"]:
        try:
            x=__import__(mod); env["packages"][mod]=getattr(x,"__version__","present")
        except Exception as e: env["packages"][mod]=f"UNAVAILABLE: {type(e).__name__}: {e}"
    env["source_sha256"]={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/"inputs/release-data/htpmd-trainset.csv",ROOT/"scripts/run_experiment_c1.py",ROOT/"patches/polygen-v1.0.0-reproducibility.patch"]}
    (OUT/"environment_and_provenance.json").write_text(json.dumps(env,indent=2)+"\n")
    report={"status":"PARTIAL_AUDIT_COMPLETE_NEW_RUNS_BLOCKED","existing_c1":{"raw_total":int(len(raw)),"raw_per_arm":{a:int((raw.arm==a).sum()) for a in ["binary","continuous"]},"eligible_total":int(raw.eligible.sum()),"eligible_by_arm":raw.groupby("arm").eligible.sum().astype(int).to_dict()},"new_sensitivity":{"status":"not executed","reason":"missing torch and deepchem; no larger checkpoint"},"layer_1":"existing C1 raw/verifier metrics audited; generation rerun not performed","layer_2":"top-50 and Pareto audit contract frozen; candidate ranking cannot be completed for new configs","top50_audit":"blocked for new configs; existing C1 candidate panel remains separate","stage_3_readiness":"BLOCKED; explicit user sign-off required before any PFP/MD","files":["existing_c1_file_audit.csv","existing_c1_arm_seed_target_metrics.csv","existing_c1_raw_with_identity.csv","FROZEN_GENERATION_CONTRACT.json","environment_and_provenance.json","AUDIT_CHECKLIST.md"]}
    (OUT/"generation_benchmark_audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__ == "__main__": main()
