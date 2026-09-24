#!/usr/bin/env python3
from pathlib import Path
import sys
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import t

ROOT=Path(__file__).resolve().parents[1]; ATLAS=Path('/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library'); sys.path.insert(0,str(ATLAS/'src'))
from plot_atlas import apply_publication_style, bar_with_points, get_palette, timecourse, forest_effects, save_figure
OUT=ROOT/'results/experiment-c/figures'; OUT.mkdir(parents=True,exist_ok=True)
def save(fig,name):
  for ext in ('png','svg'): save_figure(fig,OUT/f'{name}.{ext}')
  plt.close(fig)
def target_response():
  d=pd.read_csv(ROOT/'results/experiment-c/c1b/metrics.csv'); g=d.groupby(['arm','target']).predicted_mean.agg(['mean','sem']).reset_index(); pal=get_palette('isotope_sites')['categorical']; apply_publication_style(10)
  fig,ax=plt.subplots(figsize=(5.5,4.4)); xs=[]; ys=[]; es=[]; labels=[]
  for arm in ('binary','continuous'):
    q=g[g.arm==arm].sort_values('target'); xs.append(q.target); ys.append(q['mean']); es.append(q['sem']); labels.append(arm.capitalize())
  timecourse(ax,xs[0],ys,labels,pal[:2],errors=es,xlabel='Requested log$_{10}$ conductivity',ylabel='Frozen-verifier prediction',legend=True)
  lo=min(xs[0]); hi=max(xs[0]); ax.plot([lo,hi],[lo,hi],ls=(0,(3,2)),color='#333333',lw=1); fig.tight_layout(); save(fig,'c1b_target_response')
def effects():
  c1=pd.read_csv(ROOT/'results/experiment-c/c1/paired_primary.csv').iloc[:,1].to_numpy(); c1b=pd.read_csv(ROOT/'results/experiment-c/c1b/paired.csv').iloc[:,1].to_numpy(); c2=pd.read_csv(ROOT/'results/experiment-c/c2/paired.csv'); arrays=[c1,c1b,c2.knn_minus_random.to_numpy(),c2.optimization_minus_random.to_numpy()]; means=[]; lows=[]; highs=[]
  for a in arrays:
    m=a.mean(); h=t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)); means.append(m); lows.append(m-h); highs.append(m+h)
  apply_publication_style(10); pal=get_palette('isotope_sites')['categorical']; fig,ax=plt.subplots(figsize=(6.2,4.2)); forest_effects(ax,['C1 continuous − binary','C1b continuous − binary','C2 kNN − random','C2 optimization − random'],[means],[lows],[highs],['Paired mean ± 95% t interval'],[pal[0]],xlabel='Difference in strict target-hit rate',legend=False); fig.tight_layout(); save(fig,'paired_hit_rate_effects')
def c1_candidate_comparison():
  publication=ROOT/'results/experiment-c/publication/c1_five_seed_arm_target_metrics.csv'
  d=pd.read_csv(publication if publication.exists() else ROOT/'results/experiment-c/c1/arm_seed_target_metrics.csv')
  per=d.groupby(['arm','seed']).agg(hit_rate=('hit_rate','mean'),validity=('validity','mean'),target_mae=('target_mae','mean')).reset_index()
  apply_publication_style(9); pal=get_palette('isotope_sites')['categorical']; colors=[pal[0],pal[1]]
  fig,axs=plt.subplots(1,3,figsize=(7.2,2.8))
  for ax,(metric,label) in zip(axs,[('hit_rate','Strict target-hit rate'),('validity','Validity'),('target_mae','Target MAE (lower is better)')]):
    vals=[per[per.arm==arm].sort_values('seed')[metric].to_numpy() for arm in ('binary','continuous')]
    means=[v.mean() for v in vals]; errors=[v.std(ddof=1)/np.sqrt(len(v)) for v in vals]
    bar_with_points(ax,['Binary','Continuous'],means,errors,colors,points=vals,ylabel=label)
    # Paired lines make the seed-level comparison explicit.
    for left,right in zip(vals[0],vals[1]): ax.plot([0,1],[left,right],color='#777777',lw=.7,alpha=.55,zorder=1)
  nseed=d.seed.nunique(); fig.suptitle('C1 paired-seed generator comparison',fontsize=11,weight='bold')
  fig.text(.5,.01,f'Bars: mean ± SEM; open points and connecting lines: the same {nseed} training/generation seeds.',ha='center',fontsize=6.5,color='#55555F')
  fig.tight_layout(rect=(0,.06,1,.94)); save(fig,'c1_candidate_comparison')
def c1_five_seed_publication():
  pub=ROOT/'results/experiment-c/publication'
  d=pd.read_csv(pub/'c1_five_seed_arm_target_metrics.csv')
  paired=pd.read_csv(pub/'c1_five_seed_paired_effects.csv')
  effects_df=pd.read_csv(pub/'c1_five_seed_effect_summary.csv').set_index('metric')
  apply_publication_style(9); pal=get_palette('isotope_sites')['categorical']; colors={'binary':pal[0],'continuous':pal[1]}
  fig,axs=plt.subplots(1,3,figsize=(7.2,2.65))

  # A: requested target versus verifier response, with seed-level uncertainty.
  ax=axs[0]
  for arm,label in [('binary','Binary'),('continuous','Continuous')]:
    g=d[d.arm==arm].groupby('target').mean(numeric_only=True).reset_index()
    sem=d[d.arm==arm].groupby('target').mean_prediction.sem().to_numpy()
    ax.errorbar(g.target,g.mean_prediction,yerr=sem,marker='o',lw=1.5,capsize=2.5,color=colors[arm],label=label)
  ax.plot([-5,-3],[-5,-3],ls='--',lw=.8,color='#8A8A94')
  ax.set(xlabel='Requested log conductivity',ylabel='Verifier prediction',xticks=[-5,-4,-3])
  ax.legend(frameon=False,fontsize=7)
  ax.text(.03,.96,'A',transform=ax.transAxes,va='top',weight='bold')

  # B: primary paired effect. Each point is one independent training/generation seed.
  ax=axs[1]
  for _,row in paired.sort_values('seed').iterrows():
    ax.plot([0,1],[row.binary_hit_rate,row.continuous_hit_rate],color='#888892',lw=.8,alpha=.8,zorder=1)
    ax.scatter([0,1],[row.binary_hit_rate,row.continuous_hit_rate],s=22,facecolors='white',edgecolors=[colors['binary'],colors['continuous']],lw=1.2,zorder=2)
  ax.set(xticks=[0,1],xticklabels=['Binary','Continuous'],ylabel='Strict target-hit rate',xlim=(-.35,1.35))
  ax.text(.03,.96,'B',transform=ax.transAxes,va='top',weight='bold')

  # C: effect estimates expose the benefit/tradeoff rather than reporting hit rate alone.
  ax=axs[2]
  rows=['hit_rate','target_mae','validity','novelty']; labels=['Hit rate','Target MAE','Validity','Novelty']
  y=np.arange(len(rows))[::-1]
  means=np.array([effects_df.loc[r,'mean'] for r in rows])
  low=np.array([effects_df.loc[r,'ci95_low'] for r in rows]); high=np.array([effects_df.loc[r,'ci95_high'] for r in rows])
  for yi,m,lo,hi,r in zip(y,means,low,high,rows):
    c=colors['continuous'] if (r=='hit_rate' and m>0) or (r=='target_mae' and m<0) else '#A65A4A'
    ax.errorbar(m,yi,xerr=[[m-lo],[hi-m]],fmt='o',ms=4,capsize=2.5,color=c,lw=1.2)
  ax.axvline(0,color='#777780',lw=.8,ls='--'); ax.set(yticks=y,yticklabels=labels,xlabel='Continuous − binary')
  ax.text(.03,.96,'C',transform=ax.transAxes,va='top',weight='bold')
  fig.suptitle('Continuous conditioning improves target adherence with a validity tradeoff',fontsize=10.5,weight='bold')
  fig.text(.5,.005,'Means across five paired seeds; error bars in A are SEM and in C are 95% t intervals.',ha='center',fontsize=6.5,color='#55555F')
  fig.tight_layout(rect=(0,.07,1,.93)); save(fig,'c1_five_seed_publication')

  # A compact seed-level effect figure for the main text or supplement.
  e=effects_df.loc['hit_rate']; delta=paired.delta_hit_rate.to_numpy()
  fig,ax=plt.subplots(figsize=(4.6,3.2)); ax.axhline(0,color='#777780',lw=.8,ls='--')
  ax.scatter(np.arange(len(delta)),delta,s=34,facecolors='white',edgecolors=colors['continuous'],lw=1.3,zorder=2)
  ax.errorbar(len(delta)+.35,e['mean'],yerr=[[e['mean']-e['ci95_low']],[e['ci95_high']-e['mean']]],fmt='o',color=colors['continuous'],capsize=3,lw=1.4)
  ax.set(xticks=[0,1,2,3,4,5.35],xticklabels=[str(x) for x in paired.seed]+['Mean'],ylabel='Δ strict target-hit rate',xlabel='Paired training/generation seed',ylim=(-.0015,.0365))
  ax.set_title('All 5/5 seeds favor continuous conditioning',fontsize=9,weight='bold',pad=8)
  fig.tight_layout(); save(fig,'c1_five_seed_primary_effect')
if __name__=='__main__': target_response(); effects(); c1_candidate_comparison(); c1_five_seed_publication()
