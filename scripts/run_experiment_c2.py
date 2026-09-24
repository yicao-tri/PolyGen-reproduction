#!/usr/bin/env python3
"""Compare conditional formulation generation with enumeration and optimization."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
import run_complete_system_e2e as b
OUT=ROOT/'results/experiment-c/c2'

def fit_ensemble(train,seed,n=20):
    rng=np.random.default_rng(seed); groups=train.formulation_group.unique(); models=[]
    for _ in range(n):
        sampled=rng.choice(groups,len(groups),replace=True); idx=np.concatenate([np.flatnonzero(train.formulation_group.to_numpy()==g) for g in sampled]); models.append(b.estimator().fit(b.features(train.iloc[idx]),train.iloc[idx].log10_conductivity))
    return models
def predict(models,frame):
    p=np.stack([m.predict(b.features(frame)) for m in models]); return p.mean(0),p.std(0,ddof=1)
def rf_features(frame, salts):
    x=pd.DataFrame({'molality':frame.molality.astype(float),'temperature_K':frame.temperature_K.astype(float)})
    for salt in salts: x['salt_'+salt]=(frame.salt_shortname.astype(str)==salt).astype(float)
    return x
def fit_verifier(train,seed):
    salts=sorted(train.salt_shortname.unique()); model=RandomForestRegressor(n_estimators=300,min_samples_leaf=2,max_features=.8,n_jobs=-1,random_state=seed); model.fit(rf_features(train,salts),train.log10_conductivity); return model,salts
def verify(model,salts,frame):
    x=rf_features(frame,salts); trees=np.stack([t.predict(x) for t in model.estimators_]); return trees.mean(0),trees.std(0,ddof=1)
def grid(train,temp):
    rows=[]
    for salt,g in train.groupby('salt_shortname'):
        if g.molality.nunique()<2: continue
        for m in np.linspace(g.molality.min(),g.molality.max(),25): rows.append({'salt_shortname':salt,'molality':m,'temperature_K':temp})
    return pd.DataFrame(rows)
def main():
    data,_=b.load_and_audit(b.DEFAULT_INPUT); allrows=[]; diagnostics=[]
    for seed in (17,42,907):
        split=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=seed); tr,te=next(split.split(data,groups=data.formulation_group)); train=data.iloc[tr].reset_index(drop=True); test=data.iloc[te].reset_index(drop=True)
        models=fit_ensemble(train,seed); verifier,salts=fit_verifier(train,seed+1000); pm,_=verify(verifier,salts,test); diagnostics.append({'seed':seed,'test_groups':test.formulation_group.nunique(),'independent_verifier_test_rmse':float(mean_squared_error(test.log10_conductivity,pm)**.5)})
        rng=np.random.default_rng(seed); train_cond=train[['salt_shortname','molality','temperature_K','log10_conductivity']].copy()
        scale_y=train_cond.log10_conductivity.std(); scale_t=train_cond.temperature_K.std()
        for temp in (303.15,343.15,363.15):
            candidates=grid(train,temp); mean,sd=predict(models,candidates); candidates['pred']=mean; candidates['sd']=sd
            targets=np.quantile(mean,[.25,.5,.75])
            for target in targets:
                for method in ('random','conditional_knn','forward_optimization'):
                    if method=='random': chosen=candidates.iloc[rng.choice(len(candidates),100,replace=True)].copy()
                    elif method=='forward_optimization':
                        order=np.argsort(np.abs(mean-target)+1.0*sd); chosen=candidates.iloc[np.resize(order[:25],100)].copy()
                    else:
                        dist=np.sqrt(((train_cond.log10_conductivity-target)/scale_y)**2+((train_cond.temperature_K-temp)/scale_t)**2); pool=train_cond.iloc[np.argsort(dist)[:50]]; sampled=pool.iloc[rng.choice(len(pool),100,replace=True)]; chosen=sampled[['salt_shortname','molality']].copy(); chosen['temperature_K']=temp
                    pred,unc=verify(verifier,salts,chosen); hits=(np.abs(pred-target)<.25)&(unc<.35)
                    for (_,spec),p,u,h in zip(chosen.iterrows(),pred,unc,hits): allrows.append({'seed':seed,'temperature_K':temp,'target':target,'method':method,'salt_shortname':spec.salt_shortname,'molality':float(spec.molality),'predicted':p,'uncertainty':u,'hit':bool(h)})
    raw=pd.DataFrame(allrows); OUT.mkdir(parents=True,exist_ok=True); raw.to_csv(OUT/'samples.csv',index=False)
    metrics=raw.groupby(['seed','method','temperature_K','target']).agg(hit_rate=('hit','mean'),target_mae=('predicted',lambda x:float(np.mean(np.abs(x-x.name if False else 0))))).reset_index()
    # Recompute MAE without relying on group-name internals.
    metrics=raw.assign(error=(raw.predicted-raw.target).abs()).groupby(['seed','method','temperature_K','target']).agg(hit_rate=('hit','mean'),target_mae=('error','mean'),mean_uncertainty=('uncertainty','mean')).reset_index(); metrics.to_csv(OUT/'metrics.csv',index=False)
    seedm=metrics.groupby(['seed','method']).hit_rate.mean().unstack(); paired=pd.DataFrame({'seed':seedm.index,'knn_minus_random':seedm.conditional_knn-seedm.random,'optimization_minus_random':seedm.forward_optimization-seedm.random}); paired.to_csv(OUT/'paired.csv',index=False)
    result={'diagnostics':diagnostics,'mean_hit_rate':metrics.groupby('method').hit_rate.mean().to_dict(),'mean_paired_delta':paired.drop(columns='seed').mean().to_dict(),'paired':paired.to_dict('records')}; (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
if __name__=='__main__':main()
