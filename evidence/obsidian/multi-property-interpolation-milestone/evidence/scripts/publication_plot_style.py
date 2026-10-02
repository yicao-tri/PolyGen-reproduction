"""Shared publication plotting grammar for interpolation and upper-tail figures."""
from pathlib import Path
import matplotlib.pyplot as plt

COLORS = {
    "continuous": "#007C83",
    "binary": "#D95F02",
    "unconditional_reranking": "#6B6B6B",
    "requested": "#333333",
}

def apply_style():
    """Apply the shared large-type, no-grid publication style."""
    plt.rcParams.update({
        "font.family": "Arial", "font.size": 11,
        "axes.labelsize": 14, "axes.titlesize": 12,
        "axes.linewidth": 1.1,
        "xtick.labelsize": 12.5, "ytick.labelsize": 12.5,
        "xtick.major.width": 1.0, "ytick.major.width": 1.0,
        "xtick.major.size": 4, "ytick.major.size": 4,
        "svg.fonttype": "none", "pdf.fonttype": 42,
        "savefig.dpi": 300,
    })

def save_publication_figure(fig, out_dir, stem):
    """Export the same figure in raster and editable vector formats."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(out_dir / f"{stem}.{ext}", dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

def shared_legend(fig, handles, ncol):
    """Place a shared legend safely between the suptitle and panel row."""
    return fig.legend(handles=handles, frameon=False, fontsize=9.3,
        loc="upper center", bbox_to_anchor=(0.5, 0.935), ncol=ncol,
        handlelength=2.4, columnspacing=0.9)

def response_layout(fig):
    """Layout for three-panel response figures with enlarged typography."""
    fig.subplots_adjust(top=0.62, bottom=0.25, left=0.24, right=0.97)

def heatmap_layout(fig):
    fig.subplots_adjust(top=0.68, bottom=0.22, left=0.22, right=0.89)
