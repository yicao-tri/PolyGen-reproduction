#!/usr/bin/env python3
"""Render a Nature-style Layer 1/2 generation-grid figure from real outputs."""
from pathlib import Path
import json
import html
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from scipy.stats import gaussian_kde
from rdkit import Chem
from rdkit.Chem import Draw

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'results/experiment-c/grid/analysis'
OUT=ROOT/'results/experiment-c/grid/figures'
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'Arial','font.size':8.5,'axes.linewidth':0.8,'xtick.major.width':0.8,'ytick.major.width':0.8,'pdf.fonttype':42,'ps.fonttype':42})
COL={'binary':'#2166AC','continuous':'#D6604D'}
CFG_ORDER=['gpt-nano_steps1000_temp0.8','gpt-nano_steps1000_temp1.0','gpt-nano_steps1000_temp1.2','gpt-nano_steps2000_temp0.8','gpt-nano_steps2000_temp1.0','gpt-nano_steps2000_temp1.2']
LABEL={c:c.replace('gpt-nano_steps','').replace('_temp','; T=') for c in CFG_ORDER}

def panel_a(ax,m):
    # paired configuration means; z is strict-hit rate
    x=[]; y=[]; z=[]; c=[]
    for cfg in CFG_ORDER:
        steps=int(cfg.split('steps')[1].split('_')[0]); temp=float(cfg.split('temp')[1])
        for arm in ['binary','continuous']:
            g=m[(m.config_id==cfg)&(m.arm==arm)]
            x.append(temp); y.append(steps/1000); z.append(g.strict_hit_rate.mean()); c.append(COL[arm])
    ax.scatter(x,y,z,c=c,s=42,depthshade=False,edgecolors='white',linewidths=.35)
    ax.set_xlabel('Sampling temperature'); ax.set_ylabel('Training steps (×1000)'); ax.set_zlabel('Strict-hit rate')
    ax.set_xticks([.8,1.0,1.2]); ax.set_yticks([1,2]); ax.set_zlim(0,1)
    ax.view_init(elev=23,azim=-58); ax.set_title('Grid response',loc='left',fontweight='bold',pad=2)
    ax.legend(handles=[Line2D([0],[0],marker='o',color='w',label='Binary',markerfacecolor=COL['binary'],markersize=6),Line2D([0],[0],marker='o',color='w',label='Continuous',markerfacecolor=COL['continuous'],markersize=6)],frameon=False,loc='upper left',bbox_to_anchor=(0.02,.96))

def panel_b(ax,m):
    # aggregate across configs and seeds, preserving config-level descriptive unit
    metrics=[('strict_hit_rate','Strict hit'),('validity','Validity'),('novelty','Novelty'),('uniqueness','Uniqueness')]
    cfg=m.groupby(['config_id','arm'],as_index=False)[[x[0] for x in metrics]].mean()
    means=cfg.groupby('arm')[[x[0] for x in metrics]].mean().reindex(['binary','continuous'])
    sem=cfg.groupby('arm')[[x[0] for x in metrics]].std(ddof=1).reindex(['binary','continuous'])/np.sqrt(len(CFG_ORDER))
    xx=np.arange(len(metrics)); w=.34
    for i,arm in enumerate(['binary','continuous']): ax.bar(xx+(i-.5)*w,means.loc[arm].values,w,yerr=sem.loc[arm].values,color=COL[arm],alpha=.9,label=arm.capitalize(),capsize=2,error_kw={'lw':.7})
    ax.set_xticks(xx, [x[1] for x in metrics]); ax.set_ylim(0,1); ax.set_ylabel('Proportion'); ax.set_title('Generation quality',loc='left',fontweight='bold'); ax.legend(frameon=False,ncol=2)

def structure_row(top, raw, cfg, arm, target):
    """Return a primary candidate, or an explicit audit fallback when a cell has none."""
    g=top[(top.config_id==cfg)&(top.arm==arm)&(top.target==target)].sort_values(['rank','uncertainty']).head(1)
    if len(g):
        return g.iloc[0], f'primary rank {int(g.iloc[0]["rank"])}'
    g=raw[(raw.config_id==cfg)&(raw.arm==arm)&(raw.target==target)&(raw.valid==True)&(raw.novel==True)].copy()
    g=g[np.isfinite(g.predicted_log_sigma)&np.isfinite(g.target_error)]
    if not len(g):
        return None, 'no valid/novel fallback'
    g['distance_to_target']=g.target_error.abs()
    row=g.sort_values(['distance_to_target','uncertainty'],na_position='last').iloc[0]
    return row, 'fallback audit'

def panel_c(ax,top,raw):
    ax.axis('off'); ax.set_title('Frozen primary-ranked candidates',loc='left',fontweight='bold')
    # Baseline-only structural audit: three target columns, two paired arms.
    cfg='gpt-nano_steps1000_temp1.0'; targets=[-5.0,-4.0,-3.0]
    xs=np.linspace(.19,.81,3); ys={'binary':.66,'continuous':.25}
    for i,target in enumerate(targets):
        ax.text(xs[i],.94,f'target {target:.1f}',ha='center',va='top',fontsize=8,fontweight='bold')
        for arm in ['binary','continuous']:
            row,label=structure_row(top,raw,cfg,arm,target)
            if row is not None:
                mol=Chem.MolFromSmiles(str(row.smiles).replace('[Cu]','[*]').replace('[Au]','[*]'))
                if mol:
                    img=Draw.MolToImage(mol,size=(210,105),transparent=True)
                    ax.imshow(img,extent=(xs[i]-.12,xs[i]+.12,ys[arm]-.09,ys[arm]+.09),aspect='auto')
                ax.text(xs[i],ys[arm]-.12,f'{arm.capitalize()} | {label}',ha='center',va='top',fontsize=7,color=COL[arm])
    ax.add_patch(Rectangle((.02,.48),.96,.40,fill=False,ec=COL['binary'],lw=1.3)); ax.add_patch(Rectangle((.02,.06),.96,.40,fill=False,ec=COL['continuous'],lw=1.3))
    ax.text(.5,.49,'Binary',ha='center',va='bottom',fontsize=9,fontweight='bold',color=COL['binary']); ax.text(.5,.07,'Continuous',ha='center',va='bottom',fontsize=9,fontweight='bold',color=COL['continuous'])

def panel_c_standalone(top,raw):
    """Render structures in real subplots; avoids extent/transparent-layer clipping."""
    cfg='gpt-nano_steps1000_temp1.0'; targets=[-5.0,-4.0,-3.0]
    fig,axes=plt.subplots(2,3,figsize=(8.2,4.5),facecolor='white')
    for r,arm in enumerate(['binary','continuous']):
        for c,target in enumerate(targets):
            ax=axes[r,c]; ax.set_facecolor('white'); ax.axis('off')
            row,label=structure_row(top,raw,cfg,arm,target)
            ax.set_title(f'{arm.capitalize()}  |  target {target:.1f}',fontsize=9,fontweight='bold',color=COL[arm],pad=8)
            if row is not None:
                mol=Chem.MolFromSmiles(str(row.smiles).replace('[Cu]','[*]').replace('[Au]','[*]'))
                if mol:
                    img=Draw.MolToImage(mol,size=(420,220),transparent=False,bgColor='white')
                    ax.imshow(img,interpolation='nearest')
                    ax.set_xlim(0,img.width); ax.set_ylim(img.height,0); ax.axis('off')
                ax.text(.5,-.04,label,transform=ax.transAxes,ha='center',va='top',fontsize=7,color='#444')
    fig.suptitle('Representative candidates from the frozen baseline ranking',fontsize=11,fontweight='bold',y=.995)
    fig.tight_layout(rect=[0,.02,1,.96],w_pad=1.2,h_pad=1.2)
    return fig

def panel_c_vector_svg(top, raw, path):
    """Write panel C as a true SVG; molecule artwork is RDKit SVG paths, not PNG."""
    W, H = 1040, 580
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<style>text{font-family:Arial,Helvetica,sans-serif} .label{font-size:18px;font-weight:700} .meta{font-size:14px;fill:#444}</style>',
             '<text x="20" y="30" class="label">Representative candidates from the frozen baseline ranking</text>']
    cfg='gpt-nano_steps1000_temp1.0'; targets=[-5.0,-4.0,-3.0]
    colors={'binary':COL['binary'],'continuous':COL['continuous']}
    for r,arm in enumerate(['binary','continuous']):
        y0=55+r*255
        parts.append(f'<rect x="12" y="{y0}" width="1016" height="238" fill="none" stroke="{colors[arm]}" stroke-width="2"/>')
        parts.append(f'<text x="520" y="{y0+228}" text-anchor="middle" class="label" fill="{colors[arm]}">{arm.capitalize()}</text>')
        for c,target in enumerate(targets):
            x0=30+c*335
            parts.append(f'<text x="{x0+145}" y="{y0+25}" text-anchor="middle" class="label" fill="{colors[arm]}">{arm.capitalize()} | target {target:.1f}</text>')
            row,label=structure_row(top,raw,cfg,arm,target)
            if row is None: continue
            mol=Chem.MolFromSmiles(str(row.smiles).replace('[Cu]','[*]').replace('[Au]','[*]'))
            if mol:
                drawer=Draw.MolDraw2DSVG(300,170)
                drawer.DrawMolecule(mol)
                drawer.FinishDrawing()
                inner=drawer.GetDrawingText()
                inner=re.sub(r'^.*?<svg[^>]*>', '', inner, flags=re.S)
                inner=re.sub(r'</svg>.*$', '', inner, flags=re.S)
                parts.append(f'<g transform="translate({x0+10},{y0+35})">{inner}</g>')
            parts.append(f'<text x="{x0+145}" y="{y0+215}" text-anchor="middle" class="meta">{html.escape(label)}</text>')
    parts.append('</svg>')
    Path(path).write_text('\n'.join(parts), encoding='utf-8')

def panel_d(ax,raw,train):
    trainlog=np.log10(train.conductivity.astype(float)); ax.hist(trainlog,bins=24,density=True,color='#D9E6A5',alpha=.55,edgecolor='#556B2F',lw=.5,label='Training set')
    for arm in ['binary','continuous']:
        vals=raw.loc[raw.arm==arm,'predicted_log_sigma'].dropna().values
        vals=vals[np.isfinite(vals)]
        if len(vals)>2:
            xx=np.linspace(min(trainlog.min(),vals.min())-.2,max(trainlog.max(),vals.max())+.2,300); yy=gaussian_kde(vals)(xx); ax.plot(xx,yy,color=COL[arm],lw=1.6,label=arm.capitalize())
    ax.set_xlabel('Verifier-predicted log₁₀ conductivity (S cm⁻¹)'); ax.set_ylabel('Density'); ax.set_title('Property distributions',loc='left',fontweight='bold'); ax.legend(frameon=False)

def main():
    raw=pd.read_csv(DATA/'grid_raw_with_identity.csv'); m=pd.read_csv(DATA/'grid_arm_seed_metrics.csv'); top=pd.read_csv(DATA/'grid_top50_primary.csv'); train=pd.read_csv(ROOT/'inputs/release-data/htpmd-trainset.csv')
    # Standalone publication panels. Each panel owns its own axes, legend, and export.
    f=plt.figure(figsize=(5.5,4.6)); a=f.add_subplot(111,projection='3d'); panel_a(a,m); f.subplots_adjust(left=.02,right=.98,bottom=.04,top=.94); f.savefig(OUT/'panel_a_grid_response.pdf',bbox_inches='tight'); f.savefig(OUT/'panel_a_grid_response.svg',bbox_inches='tight'); plt.close(f)
    f, a=plt.subplots(figsize=(5.8,3.9)); panel_b(a,m); f.tight_layout(pad=1.0); f.savefig(OUT/'panel_b_quality_metrics.pdf',bbox_inches='tight'); f.savefig(OUT/'panel_b_quality_metrics.svg',bbox_inches='tight'); plt.close(f)
    f=panel_c_standalone(top,raw); f.savefig(OUT/'panel_c_representative_structures.pdf',bbox_inches='tight'); plt.close(f)
    panel_c_vector_svg(top,raw, OUT/'panel_c_representative_structures.svg')
    f, a=plt.subplots(figsize=(5.8,3.9)); panel_d(a,raw,train); f.tight_layout(pad=1.0); f.savefig(OUT/'panel_d_property_distributions.pdf',bbox_inches='tight'); f.savefig(OUT/'panel_d_property_distributions.svg',bbox_inches='tight'); plt.close(f)
    fig=plt.figure(figsize=(11.2,8.2),facecolor='white'); gs=fig.add_gridspec(2,2,wspace=.22,hspace=.28)
    axa=fig.add_subplot(gs[0,0],projection='3d'); panel_a(axa,m)
    panel_b(fig.add_subplot(gs[0,1]),m)
    panel_c(fig.add_subplot(gs[1,0]),top,raw)
    panel_d(fig.add_subplot(gs[1,1]),raw,train)
    for ax,label in zip(fig.axes,['a','b','c','d']):
        if hasattr(ax,'text2D'): ax.text2D(-.08,1.04,label,transform=ax.transAxes,fontsize=13,fontweight='bold',va='top')
        else: ax.text(-.08,1.04,label,transform=ax.transAxes,fontsize=13,fontweight='bold',va='top')
    fig.savefig(OUT/'polygen_generation_grid_main.png',dpi=600,bbox_inches='tight'); fig.savefig(OUT/'polygen_generation_grid_main.pdf',bbox_inches='tight'); fig.savefig(OUT/'polygen_generation_grid_main.svg',bbox_inches='tight'); plt.close(fig)
    print(OUT/'polygen_generation_grid_main.png')
if __name__=='__main__': main()
