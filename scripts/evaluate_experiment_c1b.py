#!/usr/bin/env python3
"""Support-aware evaluation of frozen C1 checkpoints."""
import json, random
from pathlib import Path
import numpy as np, pandas as pd, torch
from rdkit import DataStructs
import run_experiment_c1 as c1

OUT=c1.ROOT/'results/experiment-c/c1b'
def main():
    train,test=c1.prepare(); verifier,train_fp,vm=c1.verifier(train,test)
    tokenizer=c1.SmilesTokenizer(vocab_file=str(c1.REPO/'minGPT/vocab.txt'))
    targets=tuple(float(x) for x in train.log_sigma.quantile([.1,.5,.9]))
    train_smiles=set(train.mol_smiles); rows=[]
    for seed in (17,42,907):
      for arm in ('binary','continuous'):
        random.seed(seed+10000); np.random.seed(seed+10000); torch.manual_seed(seed+10000)
        cfg=c1.GPT.get_default_config(); cfg.model_type='gpt-nano'; cfg.vocab_size=tokenizer.vocab_size; cfg.block_size=c1.BLOCK
        model=c1.SoftConditionGPT(cfg,arm,float(train.log_sigma.mean()),float(train.log_sigma.std()))
        model.load_state_dict(torch.load(c1.ROOT/f'results/experiment-c/c1/{arm}-seed{seed}/final.pt',map_location='cpu')); model.eval()
        for target in targets:
          toks=model.generate(torch.full((100,),target),100)
          for i,t in enumerate(toks):
            s=c1.decode(tokenizer,t); f=c1.fp(s) if s else None; valid=f is not None and s.count('[Cu]')==1 and s.count('[Au]')==1
            if valid:
              a=c1.arr(f).reshape(1,-1); tree=np.array([q.predict(a)[0] for q in verifier.estimators_]); pred=float(tree.mean()); unc=float(tree.std(ddof=1)); support=max(DataStructs.TanimotoSimilarity(f,z) for z in train_fp); novel=s not in train_smiles
            else: pred=unc=support=np.nan; novel=False
            hit=bool(valid and novel and support>=.35 and unc<.35 and abs(pred-target)<.5)
            rows.append(dict(arm=arm,seed=seed,target=target,index=i,smiles=s,valid=valid,novel=novel,predicted_log_sigma=pred,uncertainty=unc,support=support,target_error=abs(pred-target) if valid else np.nan,hit=hit))
    OUT.mkdir(parents=True,exist_ok=True); raw=pd.DataFrame(rows); raw.to_csv(OUT/'samples.csv',index=False)
    m=raw.groupby(['arm','seed','target']).agg(validity=('valid','mean'),hit_rate=('hit','mean'),predicted_mean=('predicted_log_sigma','mean'),target_mae=('target_error','mean')).reset_index(); m.to_csv(OUT/'metrics.csv',index=False)
    armseed=m.groupby(['arm','seed']).agg(hit_rate=('hit_rate','mean'),target_mae=('target_mae','mean')).reset_index(); w=armseed.pivot(index='seed',columns='arm',values='hit_rate'); paired=pd.DataFrame({'seed':w.index,'delta_hit_continuous_minus_binary':w.continuous-w.binary}); paired.to_csv(OUT/'paired.csv',index=False)
    means=m.groupby(['arm','target']).predicted_mean.mean().reset_index(); corrs={a:float(g.target.corr(g.predicted_mean)) for a,g in means.groupby('arm')}
    result={'targets':targets,'verifier':vm,'paired_mean_delta_hit':float(paired.delta_hit_continuous_minus_binary.mean()),'paired':paired.to_dict('records'),'target_prediction_correlations':corrs,'metrics':m.to_dict('records')}; (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
if __name__=='__main__':main()
