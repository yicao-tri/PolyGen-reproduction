#!/usr/bin/env python3
"""Frozen interpolation benchmark using existing C1 checkpoints (prediction only)."""
import json, hashlib
from pathlib import Path
import numpy as np, pandas as pd, torch
from rdkit import DataStructs
import run_experiment_c1 as c1

ROOT=c1.ROOT; OUT=ROOT/'results/interpolation'
SEEDS=(17,42,202,303,907); ARMS=('continuous','binary'); N=100

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    train,test=c1.prepare(); verifier,train_fp,vm=c1.verifier(train,test)
    tok=c1.SmilesTokenizer(vocab_file=str(c1.REPO/'minGPT/vocab.txt'))
    qs=(.50,.65,.80); targets=[float(train.log_sigma.quantile(q)) for q in qs]
    manifest={'benchmark':'continuous-vs-binary interpolation','region':'interpolation',
      'source_data':str(ROOT/'inputs/release-data/htpmd-trainset.csv'),
      'source_sha256':sha(ROOT/'inputs/release-data/htpmd-trainset.csv'),
      'split':{'method':'train_test_split stratified deciles','random_state':20260923,'train_rows':len(train),'test_rows':len(test)},
      'targets':[{'quantile':q,'target_log10_sigma':t} for q,t in zip(qs,targets)],
      'arms':list(ARMS)+['unconditional_reranking'],'seeds':list(SEEDS),'samples_per_cell':N,
      'matched_settings':{'checkpoint':'existing results/experiment-c/c1/{arm}-seed{seed}/final.pt','temperature':1.0,'top_k':40,'block_size':c1.BLOCK},
      'unconditional_reranking_status':'blocked: no released unconditional generator checkpoint in this repository; no surrogate-ranked proxy is reported as generation evidence.'}
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'frozen_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    train.assign(split='generator_train_and_verifier_train').to_csv(OUT/'train_rows.csv',index=False); test.assign(split='verifier_test_only').to_csv(OUT/'test_rows.csv',index=False)
    rows=[]
    for seed in SEEDS:
      for arm in ARMS:
        ck=ROOT/f'results/experiment-c1/c1/{arm}-seed{seed}/final.pt'
        if not ck.exists(): ck=ROOT/f'results/experiment-c/extra-seeds/seeds202-303/{arm}-seed{seed}/final.pt'
        if not ck.exists(): ck=ROOT/f'results/experiment-c/c1/{arm}-seed{seed}/final.pt'
        cfg=c1.GPT.get_default_config(); cfg.model_type='gpt-nano'; cfg.vocab_size=tok.vocab_size; cfg.block_size=c1.BLOCK
        model=c1.SoftConditionGPT(cfg,arm,float(train.log_sigma.mean()),float(train.log_sigma.std())); model.load_state_dict(torch.load(ck,map_location='cpu')); model.eval()
        for q,target in zip(qs,targets):
          torch.manual_seed(seed+int(q*1000)); toks=model.generate(torch.full((N,),target),N)
          for i,t in enumerate(toks):
            s=c1.decode(tok,t); f=c1.fp(s) if s else None; valid=f is not None and s.count('[Cu]')==1 and s.count('[Au]')==1
            if valid:
              a=c1.arr(f).reshape(1,-1); tree=np.array([e.predict(a)[0] for e in verifier.estimators_]); pred=float(tree.mean()); unc=float(tree.std(ddof=1)); support=max(DataStructs.TanimotoSimilarity(f,z) for z in train_fp); novel=s not in set(train.mol_smiles)
            else: pred=unc=support=np.nan; novel=False
            rows.append({'arm':arm,'seed':seed,'quantile':q,'target':target,'candidate_index':i,'smiles':s,'valid':valid,'novel':novel,'predicted_log_sigma':pred,'uncertainty':unc,'support':support,'target_error':abs(pred-target) if valid else np.nan,'strict_hit':bool(valid and novel and support>=.35 and unc<.35 and abs(pred-target)<.5),'filter_decision':'eligible' if valid and novel and support>=.35 and unc<.35 else 'filtered'})
    raw=pd.DataFrame(rows); raw.to_csv(OUT/'candidate_predictions.csv',index=False)
    summ=raw.groupby(['arm','seed','quantile'],as_index=False).agg(n=('candidate_index','size'),validity=('valid','mean'),novelty=('novel','mean'),uniqueness=('smiles','nunique'),support_mean=('support','mean'),uncertainty_mean=('uncertainty','mean'),target_mae=('target_error','mean'),strict_hit_rate=('strict_hit','mean'),failure_rate=('valid',lambda x:1-float(x.mean())))
    summ.to_csv(OUT/'metrics_by_cell.csv',index=False)
    mono=raw[raw.valid].groupby(['arm','seed','candidate_index']).apply(lambda g: g.sort_values('quantile').predicted_log_sigma.is_monotonic_increasing).groupby(['arm','seed']).mean().reset_index(name='monotonicity_fraction')
    summary={'verifier':vm,'targets':manifest['targets'],'metrics':summ.to_dict('records'),'monotonicity':mono.to_dict('records'),'unconditional_reranking':manifest['unconditional_reranking_status']}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'cells':len(summ),'candidates':len(raw),'output':str(OUT)},indent=2))
if __name__=='__main__': main()
