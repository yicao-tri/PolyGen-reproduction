#!/usr/bin/env python3
"""Analyze completed gpt-nano generation grid without launching PFP/MD."""
from pathlib import Path
import json, hashlib, platform, subprocess, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
GRID=ROOT/'results/experiment-c/grid'
OUT=GRID/'analysis'

def main():
    OUT.mkdir(parents=True,exist_ok=True); frames=[]; audit=[]
    for root in sorted(GRID.glob('gpt-nano_*')):
        if not root.is_dir() or root.name=='analysis': continue
        config=root.name
        for p in sorted(root.glob('*-seed*/samples.csv')):
            d=pd.read_csv(p); arm=p.parent.name.split('-seed')[0]; seed=int(p.parent.name.split('-seed')[1])
            d['config_id']=config; d['arm']=arm; d['seed']=seed; d['evidence_layer']='new sensitivity evidence'
            d['eligible']=d.valid & d.novel & (d.support>=.35) & (d.uncertainty<.35)
            frames.append(d); audit.append({'config_id':config,'arm':arm,'seed':seed,'source_file':str(p),'raw_n':len(d),'targets':sorted(d.target.unique().tolist())})
    raw=pd.concat(frames,ignore_index=True); raw.to_csv(OUT/'grid_raw_with_identity.csv',index=False); pd.DataFrame(audit).to_csv(OUT/'grid_file_audit.csv',index=False)
    rows=[]
    for (cfg,arm,seed,target),g in raw.groupby(['config_id','arm','seed','target'],sort=True):
        rows.append({'evidence_layer':'new sensitivity evidence','config_id':cfg,'arm':arm,'seed':int(seed),'target':float(target),'raw_n':len(g),'validity':g.valid.mean(),'uniqueness':g.loc[g.valid,'smiles'].nunique()/len(g),'novelty':g.novel.mean(),'similarity_in_support':(g.support>=.35).mean(),'uncertainty_gate_rate':(g.uncertainty<.35).mean(),'strict_hit_rate':g.hit.mean(),'target_mae':g.target_error.mean(),'mean_uncertainty':g.uncertainty.mean()})
    m=pd.DataFrame(rows); m.to_csv(OUT/'grid_arm_seed_target_metrics.csv',index=False)
    armseed=m.groupby(['config_id','arm','seed'],as_index=False).agg(raw_n=('raw_n','sum'),validity=('validity','mean'),uniqueness=('uniqueness','mean'),novelty=('novelty','mean'),strict_hit_rate=('strict_hit_rate','mean'),target_mae=('target_mae','mean'),mean_uncertainty=('mean_uncertainty','mean'))
    armseed.to_csv(OUT/'grid_arm_seed_metrics.csv',index=False)
    paired=armseed.pivot_table(index=['config_id','seed'],columns='arm',values=['strict_hit_rate','target_mae','validity','novelty'])
    paired.columns=['_'.join(x) for x in paired.columns]; paired=paired.reset_index(); paired['delta_hit_continuous_minus_binary']=paired['strict_hit_rate_continuous']-paired['strict_hit_rate_binary']; paired['delta_mae_continuous_minus_binary']=paired['target_mae_continuous']-paired['target_mae_binary']; paired.to_csv(OUT/'grid_paired_contrasts.csv',index=False)
    top=[]
    e=raw[raw.eligible].copy(); e['primary_score']=e.predicted_log_sigma-1.96*e.uncertainty
    for (cfg,arm),g in e.groupby(['config_id','arm']):
        g=g.sort_values(['primary_score','uncertainty','target_error'],ascending=[False,True,True]).drop_duplicates('smiles').head(50).copy(); g['rank']=range(1,len(g)+1); top.append(g)
    pd.concat(top,ignore_index=True).to_csv(OUT/'grid_top50_primary.csv',index=False)
    raw['steps']=raw.config_id.str.extract(r'steps(\d+)')[0].astype(int)
    raw['temperature']=raw.config_id.str.extract(r'temp([0-9.]+)')[0].astype(float)
    sm=raw.groupby(['steps','temperature','arm'],as_index=False).agg(validity=('valid','mean'),novelty=('novel','mean'),strict_hit_rate=('hit','mean'),target_mae=('target_error','mean'))
    sm.to_csv(OUT/'grid_steps_summary.csv',index=False)
    plt.style.use('seaborn-v0_8-whitegrid')
    fig,axs=plt.subplots(1,4,figsize=(16,4),constrained_layout=True)
    for ax,metric,label in zip(axs,['validity','strict_hit_rate','target_mae','novelty'],['Validity','Strict hit rate','Target MAE','Novelty']):
        for arm,color in [('binary','#3366cc'),('continuous','#cc3333')]:
            q=sm[(sm.temperature==1.0)&(sm.arm==arm)].sort_values('steps'); ax.plot(q.steps,q[metric],marker='o',label=arm,color=color)
        ax.set_title(label); ax.set_xlabel('Training steps'); ax.set_xticks(sorted(sm.steps.unique()))
    axs[0].legend(frameon=False); fig.savefig(OUT/'steps_1000_2000_3000_temp1.0.png',dpi=180); plt.close(fig)
    pp=paired.copy(); pp['steps']=pp.config_id.str.extract(r'steps(\d+)')[0].astype(int); pp['temperature']=pp.config_id.str.extract(r'temp([0-9.]+)')[0].astype(float)
    q=pp[pp.temperature==1.0].groupby('steps',as_index=False).agg(delta_hit_mean=('delta_hit_continuous_minus_binary','mean'),delta_hit_sd=('delta_hit_continuous_minus_binary','std'))
    fig,ax=plt.subplots(figsize=(5,4)); ax.errorbar(q.steps,q.delta_hit_mean,yerr=q.delta_hit_sd,marker='o',capsize=4,color='#7a3e9d'); ax.axhline(0,color='black',lw=.8); ax.set(xlabel='Training steps',ylabel='Continuous − binary strict-hit',title='Paired effect at temperature 1.0'); fig.tight_layout(); fig.savefig(OUT/'paired_hit_effect_steps_temp1.0.png',dpi=180); plt.close(fig)
    pareto=pd.DataFrame([{'config_id':cfg,'arm':arm,'objective_x':'predicted_log_sigma','objective_y':y,'status':'available' if y=='novelty' else 'unavailable','note':'diversity/synthesizability/buildability inputs are not emitted by current C1 verifier'} for cfg in sorted(raw.config_id.unique()) for arm in ['binary','continuous'] for y in ['novelty','diversity','synthesizability']]); pareto.to_csv(OUT/'grid_pareto_availability.csv',index=False)
    counts={f'{cfg}__{arm}':int(n) for (cfg,arm),n in raw.groupby(['config_id','arm']).size().items()}
    result={'status':'analysis_complete','configs':sorted(raw.config_id.unique().tolist()),'raw_total':int(len(raw)),'raw_by_config_arm':counts,'top50_rows':int(sum(len(x) for x in top)),'ranking':'valid + novel + support>=0.35 + uncertainty<0.35; descending predicted_log_sigma - 1.96*uncertainty','pareto_note':'novelty available; diversity/synthesizability/buildable yield unavailable from current verifier output','stage_3_pfp_md':'not started; explicit user sign-off required'}
    (OUT/'grid_analysis_summary.json').write_text(json.dumps(result,indent=2,default=str)+'\n'); print(json.dumps(result,indent=2,default=str))
if __name__=='__main__': main()
