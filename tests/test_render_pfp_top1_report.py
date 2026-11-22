import json
import subprocess
import sys
from pathlib import Path


def dump(path, value):
    path.write_text(json.dumps(value))


def test_render_report_from_validated_machine_results(tmp_path):
    repo = Path(__file__).parents[1]
    contract = {
        "candidates": [
            {"arm": "continuous", "canonical_smiles": "[*]CO[*]"},
            {"arm": "binary", "canonical_smiles": "[*]CC[*]"},
        ]
    }
    row_common = {
        "trajectory_sha256": "abc",
        "frames_total": 2001,
        "analysis_ps": 160.0,
        "temperature_mean_K": 353.0,
        "li_diffusivity_cm2_s": 1e-6,
        "tfsi_diffusivity_cm2_s": 2e-6,
        "cluster_ne_conductivity_S_cm": 1e-4,
        "ne_conductivity_S_cm": 2e-4,
        "transference_number_cluster": 0.4,
        "technical_gate_pass": True,
        "scientific_convergence_status": "NON_CONVERGED_SMOKE_ONLY",
    }
    paired = {
        "status": "succeeded",
        "rows": [
            {
                **row_common,
                "arm": "continuous",
                "cluster_ne_log10_S_cm": -4.0,
                "proxy_log10_S_cm": -4.2,
                "residual_pfp_minus_proxy_log10_S_cm": 0.2,
            },
            {
                **row_common,
                "arm": "binary",
                "cluster_ne_log10_S_cm": -4.1,
                "proxy_log10_S_cm": -4.0,
                "residual_pfp_minus_proxy_log10_S_cm": -0.1,
            },
        ],
        "paired_contrast": {
            "cluster_ne_log10_S_cm": 0.1,
            "cluster_ne_conductivity_S_cm": 0.0,
            "li_diffusivity_cm2_s": 0.0,
            "tfsi_diffusivity_cm2_s": 0.0,
            "proxy_log10_S_cm": -0.2,
            "residual_log10_S_cm": 0.3,
        },
        "interpretation": {
            "higher_pfp_pilot_conductivity_arm": "continuous",
            "proxy_and_pfp_ranking_agree": False,
        },
    }
    analysis = {
        "convergence_diagnostic": [
            {
                "analysis_duration_ps": duration,
                "cluster_ne_log10_S_cm": -4.0 + duration / 1000.0,
            }
            for duration in (20.0, 40.0, 80.0, 120.0, 160.0)
        ],
        "diffusivity": {
            "system_com_drift_diagnostic": {
                "system_com_displacement_A": 0.01,
                "li_cm2_s": 9.9e-7,
            },
            "multi_origin_slope_diagnostic": {
                "li": {"r_squared": 0.95},
                "tfsi_N": {"r_squared": 0.90},
            },
        }
    }
    validation = {"status": "passed", "checks_passed": 29, "checks_total": 29}
    paths = {}
    for name, value in (
        ("contract", contract),
        ("paired", paired),
        ("continuous", analysis),
        ("binary", analysis),
        ("validation", validation),
    ):
        paths[name] = tmp_path / f"{name}.json"
        dump(paths[name], value)
    output = tmp_path / "report.md"
    subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "render_pfp_top1_report.py"),
            "--contract",
            str(paths["contract"]),
            "--paired",
            str(paths["paired"]),
            "--continuous-analysis",
            str(paths["continuous"]),
            "--binary-analysis",
            str(paths["binary"]),
            "--validation",
            str(paths["validation"]),
            "--output",
            str(output),
        ],
        check=True,
    )
    rendered = output.read_text()
    assert "29/29" in rendered
    assert "continuous − binary PFP log10 conductivity：+0.100000" in rendered
    assert "NON_CONVERGED_SMOKE_ONLY" in rendered
    assert "`[*]CO[*]`" in rendered
