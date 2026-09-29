"""Render publication figures for the frozen interpolation benchmark."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from publication_plot_style import apply_style, shared_legend, save_publication_figure, response_layout, heatmap_layout

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "results/interpolation"
OUT = IN / "publication"
OUT.mkdir(parents=True, exist_ok=True)
COLORS = {"continuous":"#007C83", "binary":"#D95F02"}
LABELS = {"continuous":"Continuous", "binary":"Binary"}
ORDER = ["continuous", "binary"]
QORDER = [0.50, 0.65, 0.80]
QLABEL = {0.50:"Q50", 0.65:"Q65", 0.80:"Q80"}

def style():
    apply_style()
def sem(x):
    x=pd.Series(x).dropna(); return x.std(ddof=1)/np.sqrt(len(x)) if len(x)>1 else np.nan
def save(fig,name):
    save_publication_figure(fig, OUT, name)
def main():
    style(); raw=pd.read_csv(IN/"candidate_predictions.csv"); m=pd.read_csv(IN/"metrics_by_cell.csv"); s=json.loads((IN/"summary.json").read_text())
    rows=[]
    for (arm,q),g in m.groupby(["arm","quantile"]):
        r={"arm":arm,"quantile":q}
        for c in ["validity","novelty","support_mean","uncertainty_mean","target_mae","strict_hit_rate","failure_rate"]:
            r[c]=g[c].mean(); r[c+"_sem"]=sem(g[c])
        r["target"]=float(raw[raw["quantile"]==q].target.iloc[0]); rows.append(r)
    agg=pd.DataFrame(rows); agg.to_csv(OUT/"interpolation_aggregate_metrics.csv",index=False)
    # Figure 1: direct counterpart to upper-tail Figure 1.
    fig,ax=plt.subplots(1,3,figsize=(7.5,2.45),gridspec_kw={"wspace":0.55}); x=np.arange(3)
    for arm in ORDER:
        a=agg[agg.arm==arm].set_index("quantile").reindex(QORDER)
        ax[0].errorbar(x,a.target_error if False else a.target,alpha=0) # keep identical x semantics
        ax[0].errorbar(x,a.target*0+a.target,alpha=0)
        # RF prediction is recovered from candidate-level rows to avoid losing it in the cell summary.
        p=raw[raw.arm==arm].groupby(["quantile","seed"],as_index=False).predicted_log_sigma.mean().groupby("quantile").predicted_log_sigma.agg(["mean","std","count"]).reindex(QORDER)
        ax[0].errorbar(x,p["mean"],yerr=p["std"]/np.sqrt(p["count"]),color=COLORS[arm],marker="o",lw=1.6,ms=4.5,capsize=2.5,label=LABELS[arm])
        ax[1].errorbar(x,a.target_mae,yerr=a.target_mae_sem,color=COLORS[arm],marker="o",lw=1.6,ms=4.5,capsize=2.5)
        ax[2].errorbar(x,a.validity,yerr=a.validity_sem,color=COLORS[arm],marker="o",lw=1.6,ms=4.5,capsize=2.5)
    targets=[float(agg[agg["quantile"]==q].target.iloc[0]) for q in QORDER]
    ax[0].plot(x,targets,color="#333",lw=1,ls=(0,(1.5,1.5)),marker="x",ms=3.5,label="Requested target")
    ax[0].set_ylabel(r"RF prediction, $\log_{10}\sigma$")
    ax[1].set_ylabel(r"Target MAE, $\Delta\log_{10}\sigma$")
    ax[2].set_ylabel("Validity fraction")
    for a in ax:
        a.set_xticks(x,[QLABEL[q] for q in QORDER]); a.spines["top"].set_visible(False); a.spines["right"].set_visible(False); a.set_xlim(-.2,2.2)
    ax[0].set_ylim(-4.42,-3.95); ax[1].set_ylim(0,.26); ax[2].set_ylim(0,.72)
    for i,t in enumerate(["A  RF response","B  Target error","C  Validity"]): ax[i].set_title(t,loc="left",fontweight="bold")
    handles=[Line2D([0],[0],color=COLORS[a],marker="o",lw=1.6,label=LABELS[a]) for a in ORDER]+[Line2D([0],[0],color="#333",marker="x",lw=1,ls=(0,(1.5,1.5)),label="Requested target")]
    shared_legend(fig, handles, 3)
    response_layout(fig); fig.suptitle("Interpolation prediction benchmark (mean ± SEM across five seeds)",x=.16,y=.98,ha="left",fontsize=12.5,fontweight="bold"); save(fig,"Figure_1_interpolation_response")
    # Figure 2: direct counterpart to upper-tail Figure 2.
    fig,ax=plt.subplots(1,2,figsize=(5.8,2.55),gridspec_kw={"wspace":.55})
    for i,metric in enumerate(["strict_hit_rate","validity"]):
        mat=m.pivot_table(index="arm",columns="quantile",values=metric,aggfunc="mean").reindex(index=ORDER,columns=QORDER); im=ax[i].imshow(mat.to_numpy(),vmin=0,vmax=.7,cmap="YlGnBu",aspect="auto")
        for r in range(mat.shape[0]):
            for c in range(mat.shape[1]): ax[i].text(c,r,f"{mat.iloc[r,c]:.2f}",ha="center",va="center",fontsize=8,color="white" if mat.iloc[r,c]>.38 else "#222")
        ax[i].set_xticks(range(3),[QLABEL[q] for q in QORDER]); ax[i].set_yticks(range(2),[LABELS[a] for a in ORDER]); ax[i].tick_params(length=0); ax[i].spines[:].set_visible(False); ax[i].set_title(("D  Strict-hit rate" if i==0 else "E  Validity"),loc="left",fontweight="bold")
        if i==1: cb=fig.colorbar(im,ax=ax[i],fraction=.06,pad=.04); cb.set_label("Fraction",fontsize=8); cb.ax.tick_params(labelsize=7,length=2)
    heatmap_layout(fig); fig.suptitle("Interpolation output quality across the target grid",x=.22,y=.98,ha="left",fontsize=12.5,fontweight="bold"); save(fig,"Figure_2_interpolation_quality_heatmap")
    # Figure 3: interpolation-specific monotonicity and target-response slope.
    mono=pd.DataFrame(s["monotonicity"]); curves=raw[raw.valid].groupby(["arm","seed","quantile"],as_index=False).predicted_log_sigma.mean()
    fig,ax=plt.subplots(1,2,figsize=(6.4,2.65),gridspec_kw={"wspace":.48})
    for arm in ORDER:
        a=curves[curves.arm==arm].groupby("quantile").predicted_log_sigma.agg(["mean","std","count"]).reindex(QORDER); ax[0].errorbar(x,a["mean"],yerr=a["std"]/np.sqrt(a["count"]),color=COLORS[arm],marker="o",lw=1.7,ms=4.5,capsize=2.5,label=LABELS[arm])
        z=mono[mono.arm==arm]; ax[1].bar(ORDER.index(arm),z.monotonicity_fraction.mean(),yerr=sem(z.monotonicity_fraction),color=COLORS[arm],width=.55,capsize=3)
    ax[0].plot(x,targets,color="#333",lw=1,ls=(0,(1.5,1.5)),marker="x",ms=3.5,label="Requested target"); ax[0].set_xticks(x,[QLABEL[q] for q in QORDER]); ax[0].set_ylabel(r"Mean predicted log$_{10}$ conductivity"); ax[0].set_title("F  Target-response curve",loc="left",fontweight="bold"); ax[0].legend(frameon=False,fontsize=7.5)
    ax[1].set_xticks(range(2),[LABELS[a] for a in ORDER]); ax[1].set_ylabel("Monotonicity fraction"); ax[1].set_ylim(0,1); ax[1].set_title("G  Candidate-wise monotonicity",loc="left",fontweight="bold")
    for a in ax: a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
    fig.subplots_adjust(top=.74,bottom=.20,left=.16,right=.97); fig.suptitle("Interpolation-specific controllability diagnostics",x=.16,y=.98,ha="left",fontsize=12.5,fontweight="bold"); save(fig,"Figure_3_interpolation_controllability")
    (OUT/"FIGURE_CAPTIONS.md").write_text("""# Interpolation publication figures\n\n**Figure 1 | Interpolation response under matched target requests.** Direct counterpart to the upper-tail response figure. (A) Frozen RF predictions follow the requested Q50–Q80 curve for both arms. (B) Target MAE remains lower than the upper-tail benchmark because all requests lie within the generator/verifier training support. (C) Validity is retained across the internal target grid. Points and error bars are means ± SEM across five matched seeds.\n\n**Figure 2 | Interpolation output quality.** Heatmaps show strict-hit rate and validity by arm and requested quantile. Unlike the upper-tail figure, no unsupported-cell masking is required: all six arm-by-target cells have generated candidates.\n\n**Figure 3 | Interpolation-specific controllability.** (F) Mean achieved RF response versus requested target, with the identity target curve shown for reference. (G) Candidate-wise monotonicity is the fraction of valid seed-by-candidate trajectories that are non-decreasing from Q50 to Q65 to Q80. This diagnostic is specific to interpolation and should not be interpreted as physical monotonicity without MD.\n""")
if __name__=="__main__": main()
