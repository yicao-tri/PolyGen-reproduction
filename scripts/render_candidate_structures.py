#!/usr/bin/env python3
"""Render binary and continuous MD candidate p-SMILES as 2-D structures."""
from pathlib import Path
import argparse
import csv
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

ROOT = Path(__file__).resolve().parents[1]

def configure_plotting(atlas_src=None):
    """Use Plot Atlas when supplied, with a deterministic local fallback."""
    if atlas_src:
        sys.path.insert(0, str(Path(atlas_src).resolve()))
    try:
        from plot_atlas import apply_publication_style, save_figure
        apply_publication_style(8.5)
        return save_figure
    except ImportError:
        plt.rcParams.update({'font.family': 'Arial', 'font.size': 8.5,
                             'axes.linewidth': 1.1, 'svg.fonttype': 'none'})
        def save_figure(fig, path, dpi=300):
            path = Path(path)
            fig.savefig(path, dpi=dpi, bbox_inches='tight')
            fig.savefig(path.with_suffix('.svg'), bbox_inches='tight', metadata={'Date': None})
        return save_figure

def draw_png(mol, path, size=(720, 460)):
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DCairo(*size)
    opts = drawer.drawOptions()
    opts.bondLineWidth = 2.2
    opts.padding = 0.08
    opts.minFontSize = 16
    opts.maxFontSize = 28
    # Preserve endpoint identity while keeping conventional element colors.
    opts.updateAtomPalette({29: (0.72, 0.34, 0.18), 79: (0.84, 0.62, 0.10)})
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    path.write_bytes(drawer.GetDrawingText())

def draw_svg(mol, path, size=(720, 460)):
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(*size)
    opts = drawer.drawOptions()
    opts.bondLineWidth = 2.2
    opts.padding = 0.08
    opts.minFontSize = 16
    opts.maxFontSize = 28
    opts.updateAtomPalette({29: (0.72, 0.34, 0.18), 79: (0.84, 0.62, 0.10)})
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    path.write_text(drawer.GetDrawingText())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidates', type=Path,
                        default=ROOT/'results/publishable-matrix/tables/md_candidates.csv')
    parser.add_argument('--output', type=Path,
                        default=ROOT/'results/publishable-matrix/candidate_structures')
    parser.add_argument('--atlas-src', default=os.environ.get('PLOT_ATLAS_SRC'))
    args = parser.parse_args()
    source, out = args.candidates.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(source.open()))
    by_arm = {a: [r for r in rows if r['arm'] == a] for a in ('binary', 'continuous')}
    overlap = ({r['canonical_p-SMILES'] for r in by_arm['binary']} &
               {r['canonical_p-SMILES'] for r in by_arm['continuous']})
    arm_color = {'binary': '#6F55C5', 'continuous': '#E24A3B'}
    shared_color = '#2E9F6B'
    index_rows = []
    save_figure = configure_plotting(args.atlas_src)

    for arm, arm_rows in by_arm.items():
        idir = out / arm
        idir.mkdir(exist_ok=True)
        fig, axes = plt.subplots(5, 4, figsize=(11.7, 13.2))
        for number, (ax, row) in enumerate(zip(axes.flat, arm_rows), 1):
            smi = row['canonical_p-SMILES']
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                raise ValueError(f'RDKit failed for {arm} candidate {number}: {smi}')
            cid = ('B' if arm == 'binary' else 'C') + f'{number:02d}'
            png = idir / f'{cid}.png'
            svg = idir / f'{cid}.svg'
            draw_png(mol, png)
            draw_svg(mol, svg)
            ax.imshow(np.asarray(Image.open(png)))
            ax.set_xticks([]); ax.set_yticks([])
            is_shared = smi in overlap
            border = shared_color if is_shared else arm_color[arm]
            for spine in ax.spines.values():
                spine.set_visible(True); spine.set_color(border); spine.set_linewidth(2.4 if is_shared else 1.1)
            target = float(row['target_log_sigma'])
            pred = float(row['ensemble_pred_log_sigma'])
            ax.set_title(f"{cid}{'  SHARED' if is_shared else ''}\ntarget {target:.3f} | pred {pred:.3f}",
                         color=border, fontsize=8, pad=4, weight='bold')
            index_rows.append({
                'candidate_id': cid, 'arm': arm, 'shared_between_arms': is_shared,
                'target_log_sigma': row['target_log_sigma'],
                'ensemble_pred_log_sigma': row['ensemble_pred_log_sigma'],
                'canonical_p-SMILES': smi,
                'png': f'{arm}/{cid}.png', 'svg': f'{arm}/{cid}.svg'
            })
        fig.suptitle(f"PolyGen {arm.capitalize()} MD candidates (seed 101)", fontsize=15, y=.995)
        fig.text(.5, .006, 'Green border = canonical p-SMILES also selected by the other arm; Cu/Au denote polymer connection points.',
                 ha='center', fontsize=8, color='#303038')
        fig.subplots_adjust(left=.025, right=.975, top=.95, bottom=.035, hspace=.27, wspace=.08)
        save_figure(fig, out / f'{arm}_20_candidates.png', dpi=300)
        plt.close(fig)

    with (out / 'candidate_structure_index.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(index_rows[0]))
        writer.writeheader(); writer.writerows(index_rows)

    # A compact sheet for the seven shared structures only.
    shared_rows = [r for r in by_arm['binary'] if r['canonical_p-SMILES'] in overlap]
    fig, axes = plt.subplots(2, 4, figsize=(11.7, 5.6))
    for ax in axes.flat: ax.axis('off')
    for number, (ax, row) in enumerate(zip(axes.flat, shared_rows), 1):
        ax.axis('on')
        smi = row['canonical_p-SMILES']; mol = Chem.MolFromSmiles(smi)
        tmp = out / 'binary' / f"B{by_arm['binary'].index(row)+1:02d}.png"
        ax.imshow(np.asarray(Image.open(tmp))); ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_color(shared_color); spine.set_linewidth(2.2)
        ax.set_title(f'S{number:02d}', color=shared_color, weight='bold')
    fig.suptitle('Seven candidates shared by binary and continuous selection', fontsize=14)
    fig.subplots_adjust(left=.025,right=.975,top=.88,bottom=.04,hspace=.25,wspace=.08)
    save_figure(fig, out / 'shared_7_candidates.png', dpi=300)
    plt.close(fig)

if __name__ == '__main__':
    main()
