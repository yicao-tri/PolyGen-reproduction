#!/usr/bin/env python3
"""Publication figures for the seed-101 PolyGen conditioning matrix.

Uses the user's Plot Atlas primitives and visual grammar. Intervals in the
target-response figure are bootstrap intervals over generated candidates;
they are not between-seed confidence intervals.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from plot_atlas import (apply_publication_style, save_figure, timecourse,
                        grouped_bar, embedding, ridgeline_density, bold_tick_labels)

ARMS=['binary','continuous','linear','multibin','shuffled','unconditional']
LABEL={'binary':'Binary','continuous':'Continuous MLP','linear':'Continuous linear',
       'multibin':'5-bin','shuffled':'Shuffled control','unconditional':'Unconditional'}
COL={'binary':'#6F55C5','continuous':'#E24A3B','linear':'#D95491',
     'multibin':'#2E9F6B','shuffled':'#F0AF24','unconditional':'#7A7A82'}

def save(fig, out, stem):
    fig.tight_layout(); save_figure(fig,out/f'{stem}.png',dpi=300); save_figure(fig,out/f'{stem}.svg'); plt.close(fig)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run',type=Path,required=True); a=ap.parse_args()
    tab=a.run/'tables'; out=a.run/'figures'; out.mkdir(exist_ok=True)
    g=pd.read_csv(tab/'generated_candidates.csv'); q=pd.read_csv(tab/'generation_metrics.csv'); r=pd.read_csv(tab/'target_level_metrics.csv'); e=pd.read_csv(tab/'controllability_endpoints.csv'); emb=pd.read_csv(tab/'structural_embedding.csv')
    apply_publication_style(8)

    # Fig 1 — experiment logic and the binary-resolution limitation.
    fig,ax=plt.subplots(figsize=(7.1,2.55)); ax.axis('off')
    boxes=[(.03,.58,.16,.25,'Same split\nSame rows'),(.25,.58,.16,.25,'Condition encoder\nonly changed'),(.47,.58,.16,.25,'miniGPT\n10k steps'),(.69,.58,.13,.25,'2,500\nsamples'),(.86,.58,.11,.25,'Frozen\nverifiers')]
    for x,y,w,h,t in boxes:
        ax.add_patch(plt.Rectangle((x,y),w,h,facecolor='#EAF5F8',edgecolor='#303038',lw=1)); ax.text(x+w/2,y+h/2,t,ha='center',va='center',weight='bold')
    for x in [.19,.41,.63,.82]: ax.annotate('',(x+.055,.705),(x,.705),arrowprops=dict(arrowstyle='->',lw=1.2,color='#303038'))
    ax.text(.25,.35,'Binary:',weight='bold',color=COL['binary']); ax.text(.34,.35,'all q10–q90 targets map to LOW (q95 threshold)',color='#303038')
    ax.text(.25,.20,'Continuous:',weight='bold',color=COL['continuous']); ax.text(.37,.20,'each target retains its numeric value',color='#303038')
    ax.text(.03,.06,'Final claim requires full-atom MD; surrogate scores are candidate-screening evidence only.',fontsize=7,color='#5B5B62')
    save(fig,out,'figure_1_experiment_design')

    # Fig 2 — requested vs predicted response, with candidate bootstrap CIs.
    rng=np.random.default_rng(101); errors=[]; ys=[]; xs=np.sort(r.target_log_sigma.unique())
    for arm in ARMS:
        means=[]; lo=[]; hi=[]
        for target in xs:
            z=g[(g.arm==arm)&(g.target_log_sigma==target)&g.polymer_validity&g.structural_support].ensemble_pred_log_sigma.dropna().to_numpy()
            b=np.array([rng.choice(z,len(z),replace=True).mean() for _ in range(1000)])
            m=z.mean(); means.append(m); lo.append(m-np.quantile(b,.025)); hi.append(np.quantile(b,.975)-m)
        ys.append(means); errors.append(np.vstack([lo,hi]))
    fig,ax=plt.subplots(figsize=(5.4,4.25)); ax.plot([xs.min(),xs.max()],[xs.min(),xs.max()],ls='--',lw=1,color='#303038',label='Ideal')
    timecourse(ax,xs,ys,[LABEL[x] for x in ARMS],[COL[x] for x in ARMS],errors=errors,error_style='bar',xlabel='Requested log10 conductivity',ylabel='Verifier ensemble mean',legend=True,marker_size=3.5)
    ax.text(.02,.02,'95% bootstrap CI over generated candidates; seed = 101',transform=ax.transAxes,fontsize=6,color='#5B5B62')
    save(fig,out,'figure_2_target_response')

    # Fig 3 — controllability summary.
    ee=e.set_index('arm').loc[ARMS]
    matrix=np.c_[ee.mean_abs_calibration_error,ee.mean_strict_hit_rate,ee.mean_relaxed_hit_rate,ee.monotonic_steps/ee.total_steps]
    fig,ax=plt.subplots(figsize=(7.1,3.55)); grouped_bar(ax,[LABEL[x] for x in ARMS],matrix,['Abs. calibration error','Strict hit ±0.10','Relaxed hit ±0.20','Monotonic fraction'],['#E24A3B','#6F55C5','#31A7C8','#2E9F6B'],ylabel='Metric value')
    ax.tick_params(axis='x',rotation=28); ax.legend(frameon=False,ncol=2,fontsize=6)
    save(fig,out,'figure_3_controllability_metrics')

    # Fig 4 — generation quality averaged over targets.
    qq=q.groupby('arm').mean(numeric_only=True).loc[ARMS]
    cols=['polymer_validity','uniqueness','novelty','synthesizable_sa_lt5','diversity']
    fig,ax=plt.subplots(figsize=(7.1,3.55)); grouped_bar(ax,[LABEL[x] for x in ARMS],qq[cols].to_numpy(),['Polymer validity','Uniqueness','Novelty','SA < 5','Diversity'],['#31A7C8','#6F55C5','#E24A3B','#2E9F6B','#F0AF24'],ylabel='Fraction / mean')
    ax.set_ylim(0,1.05); ax.tick_params(axis='x',rotation=28); ax.legend(frameon=False,ncol=3,fontsize=6)
    save(fig,out,'figure_4_generation_quality')

    # Fig 5 — fixed PCA structural landscape, shown independently per key arm.
    key=['binary','continuous','multibin']; fig,axs=plt.subplots(1,3,figsize=(7.1,2.65),sharex=True,sharey=True)
    tlevels=sorted(emb.target_log_sigma.unique()); colors=['#286B8A','#4296B7','#73B8D1','#E24A3B','#8B1E2D']
    for ax,arm in zip(axs,key):
        d=emb[emb.arm==arm]; groups=pd.Categorical(d.target_log_sigma,categories=tlevels,ordered=True).codes
        embedding(ax,d.pc1,d.pc2,groups,colors,labels=False,point_size=4,alpha=.55); ax.set_title(LABEL[arm]); ax.set_xlabel('PC1'); ax.set_ylabel('PC2')
    handles=[plt.Line2D([0],[0],marker='o',ls='',color=c,label=f'q{p}') for c,p in zip(colors,[10,30,50,70,90])]; fig.legend(handles=handles,loc='upper center',ncol=5,frameon=False)
    save(fig,out,'figure_5_structural_landscape')

    # Fig 6 — response distributions: binary versus continuous.
    xgrid=np.linspace(-4.85,-3.55,350); fig,axs=plt.subplots(1,2,figsize=(7.1,3.4),sharex=True,sharey=True)
    for ax,arm in zip(axs,['binary','continuous']):
        curves=[]
        for t in tlevels:
            z=g[(g.arm==arm)&(g.target_log_sigma==t)&g.polymer_validity&g.structural_support].ensemble_pred_log_sigma.dropna().to_numpy(); den=gaussian_kde(z)(xgrid); curves.append(den/den.max()*.75)
        ridgeline_density(ax,xgrid,curves,[f'q{p}' for p in [10,30,50,70,90]],colors,xlabel='Predicted log10 conductivity',density_label='Relative density'); ax.set_title(LABEL[arm])
    save(fig,out,'figure_6_prediction_distributions')

    # Fig 7 — verifier uncertainty and support.
    metrics=['mean_uncertainty','mean_disagreement']; rr=r.groupby('arm')[metrics].mean().loc[ARMS]
    support=q.groupby('arm').supported_rate.mean().loc[ARMS]
    fig,axs=plt.subplots(1,2,figsize=(7.1,3.2)); grouped_bar(axs[0],[LABEL[x] for x in ARMS],rr.to_numpy(),['RF tree SD','Verifier disagreement'],['#F0AF24','#E24A3B'],ylabel='Mean uncertainty'); grouped_bar(axs[1],[LABEL[x] for x in ARMS],support.to_numpy()[:,None],['Supported (Tanimoto ≥ 0.25)'],['#2E9F6B'],ylabel='Fraction supported')
    for ax in axs: ax.tick_params(axis='x',rotation=32)
    save(fig,out,'figure_7_support_and_uncertainty')

    # Fig 8 — MD handoff status; this intentionally contains no surrogate-as-MD result.
    fig,ax=plt.subplots(figsize=(7.1,2.7)); ax.axis('off')
    stages=[('40 selected\ncandidates','#2E9F6B'),('Build >=150-atom\nlinear chains','#F0AF24'),('PCFF+ + LiTFSI\n1.5 mol kg^-1','#F0AF24'),('5 replicas x 5 ns\nat 353 K','#D9D9DF'),('Cluster Nernst-Einstein\nconductivity','#D9D9DF')]
    for i,(txt,c) in enumerate(stages):
        x=.02+i*.195; ax.add_patch(plt.Rectangle((x,.43),.16,.28,facecolor=c,alpha=.9,edgecolor='#303038',lw=1)); ax.text(x+.08,.57,txt,ha='center',va='center',weight='bold',fontsize=7)
        if i<4: ax.annotate('',(x+.19,.57),(x+.165,.57),arrowprops=dict(arrowstyle='->',lw=1.2,color='#303038'))
    ax.text(.02,.20,'Current status: WAITING FOR SYSTEM BUILD',weight='bold',color='#B07600')
    ax.text(.02,.08,'Public release lacks the publication p-SMILES → PCFF+ builder; no MD conductivity is claimed.',fontsize=7,color='#5B5B62')
    save(fig,out,'figure_8_md_validation_status')

if __name__=='__main__': main()
