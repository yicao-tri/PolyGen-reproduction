#!/usr/bin/env python3
from pathlib import Path
import sys
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import t

ROOT=Path(__file__).resolve().parents[1]; ATLAS=Path('/Users/yicao/.codex/.chatgpt-projects/g-p-6aa88e35293481918a7b8159df39d546/plot_library'); sys.path.insert(0,str(ATLAS/'src'))
from plot_atlas import apply_publication_style, get_palette, timecourse, forest_effects, save_figure
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
if __name__=='__main__': target_response(); effects()
