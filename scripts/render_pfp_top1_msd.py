#!/usr/bin/env python3
"""Render stored top-1 PFP multi-origin MSD diagnostics as an editable SVG."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARMS = (("continuous", "Continuous-value top-1"), ("binary", "Binary top-1"))
SERIES = (("li_msd_A2", "Li+", "#2166AC"), ("tfsi_N_msd_A2", "TFSI− (N atom)", "#B2182B"))


def read_msd(arm: str) -> list[dict[str, float]]:
    path = ROOT / "results/experiment-c/pfp-pilot/production/analysis" / arm / "msd_curve.csv"
    with path.open(newline="") as handle:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> None:
    out_dir = ROOT / "results/experiment-c/pfp-pilot/production/analysis/figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {arm: read_msd(arm) for arm, _ in ARMS}
    ymax = (int(max(row[key] for rows in data.values() for row in rows for key, _, _ in SERIES) / 10) + 1) * 10
    panel_w, panel_h, gap, top, left = 470, 350, 70, 95, 90
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="540" viewBox="0 0 1200 540">', '<rect width="100%" height="100%" fill="white"/>', '<style>text{font-family:Arial,sans-serif;fill:#1a1a1a}.tick{font-size:13px;font-weight:700}.label{font-size:16px}.title{font-size:18px}.small{font-size:12px;fill:#4d4d4d}</style>', '<text x="600" y="35" text-anchor="middle" class="title">PFP top-1 pilot: multi-origin mean-squared displacement</text>']
    for index, (arm, title) in enumerate(ARMS):
        x0 = left + index * (panel_w + gap)
        px = lambda x: x0 + x / 120 * panel_w
        py = lambda y: top + panel_h - y / ymax * panel_h
        out += [f'<text x="{x0-35}" y="{top-24}" font-size="20" font-weight="700">{"AB"[index]}</text>', f'<text x="{x0+panel_w/2}" y="{top-20}" text-anchor="middle" class="title">{title}</text>', f'<rect x="{px(40):.1f}" y="{top}" width="{px(120)-px(40):.1f}" height="{panel_h}" fill="#8c8c8c" opacity="0.10"/>']
        for tick in range(0, ymax + 1, 10):
            y = py(tick); out.append(f'<line x1="{x0}" x2="{x0+panel_w}" y1="{y:.1f}" y2="{y:.1f}" stroke="#d9d9d9" stroke-width="0.8"/>')
            if index == 0: out.append(f'<text x="{x0-10}" y="{y+4:.1f}" text-anchor="end" class="tick">{tick}</text>')
        for tick in range(0, 121, 20):
            x = px(tick); out += [f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top+panel_h}" y2="{top+panel_h+6}" stroke="#222" stroke-width="1.5"/>', f'<text x="{x:.1f}" y="{top+panel_h+26}" text-anchor="middle" class="tick">{tick}</text>']
        out.append(f'<rect x="{x0}" y="{top}" width="{panel_w}" height="{panel_h}" fill="none" stroke="#222" stroke-width="1.8"/>')
        for key, label, color in SERIES:
            points = " ".join(f'{px(r["lag_ps"]):.2f},{py(r[key]):.2f}' for r in data[arm] if r["lag_ps"] <= 120)
            out.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.2"/>')
        for j, (_, label, color) in enumerate(SERIES):
            y = top + 18 + j * 21; out += [f'<line x1="{x0+15}" x2="{x0+39}" y1="{y}" y2="{y}" stroke="{color}" stroke-width="2.5"/>', f'<text x="{x0+46}" y="{y+4}" class="small">{label}</text>']
        out += [f'<text x="{x0+panel_w/2}" y="{top+panel_h+58}" text-anchor="middle" class="label">Lag time (ps)</text>', f'<text x="{x0+panel_w/2}" y="{top+15}" text-anchor="middle" class="small">shaded: slope-diagnostic fit window (40–120 ps)</text>']
    out += ['<text x="25" y="270" text-anchor="middle" class="label" transform="rotate(-90 25 270)">MSD (Å²)</text>', '<text x="600" y="515" text-anchor="middle" class="small">Curves are diagnostics; reported HTP-MD diffusivities use endpoint MSD over the final 160 ps after a 40 ps discard.</text>', '</svg>']
    (out_dir / "pfp_top1_msd.svg").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
