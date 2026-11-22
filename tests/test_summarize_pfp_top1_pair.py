import json
import subprocess
import sys
from pathlib import Path


def dump(path, value):
    path.write_text(json.dumps(value))


def analysis(proxy, pfp_log, conductivity, li_diff, tfsi_diff):
    return {
        "status": "succeeded",
        "source": {"trajectory_sha256": "abc"},
        "frames_total": 2001,
        "analysis_ps": 160.0,
        "discard_ps": 40.0,
        "diffusivity": {
            "htpmd_endpoint": {"li_cm2_s": li_diff, "tfsi_cm2_s": tfsi_diff}
        },
        "conductivity": {
            "cluster_nernst_einstein_S_cm": conductivity,
            "nernst_einstein_S_cm": conductivity * 2,
            "cluster_transference_number": 0.4,
        },
        "proxy_comparison": {
            "proxy_log10_S_cm": proxy,
            "pfp_cluster_ne_log10_S_cm": pfp_log,
            "residual_pfp_minus_proxy_log10_S_cm": pfp_log - proxy,
        },
        "quality": {
            "finite_values": True,
            "constant_cell": True,
            "population_ion_count_mean": 20,
            "expected_ion_count": 20,
        },
    }


def test_paired_summary_signs_temperature_and_gates(tmp_path):
    repo = Path(__file__).parents[1]
    inputs = {
        "continuous_analysis": analysis(-4.2, -4.0, 1e-4, 2e-6, 1e-6),
        "binary_analysis": analysis(-4.0, -4.1, 8e-5, 1e-6, 2e-6),
        "continuous_run": {"status": "succeeded"},
        "binary_run": {"status": "succeeded"},
    }
    paths = {}
    for name, value in inputs.items():
        paths[name] = tmp_path / f"{name}.json"
        dump(paths[name], value)
    for arm, temperatures in (("continuous", [300, 350, 356]), ("binary", [300, 352, 354])):
        path = tmp_path / f"{arm}.log"
        path.write_text(
            "Time[ps] Etot[eV] Epot[eV] Ekin[eV] T[K]\n"
            + "\n".join(
                f"{time:.1f} -1 -2 1 {temperature}"
                for time, temperature in zip((0, 40, 200), temperatures)
            )
            + "\n"
        )
        paths[f"{arm}_log"] = path
    output = tmp_path / "paired"
    subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "summarize_pfp_top1_pair.py"),
            "--continuous-analysis",
            str(paths["continuous_analysis"]),
            "--continuous-run",
            str(paths["continuous_run"]),
            "--continuous-log",
            str(paths["continuous_log"]),
            "--binary-analysis",
            str(paths["binary_analysis"]),
            "--binary-run",
            str(paths["binary_run"]),
            "--binary-log",
            str(paths["binary_log"]),
            "--output-dir",
            str(output),
            "--expected-frames",
            "2001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads((output / "paired_summary.json").read_text())
    assert result["status"] == "succeeded"
    assert abs(result["paired_contrast"]["cluster_ne_log10_S_cm"] - 0.1) < 1e-12
    assert abs(result["paired_contrast"]["residual_log10_S_cm"] - 0.3) < 1e-12
    assert result["interpretation"]["higher_pfp_pilot_conductivity_arm"] == "continuous"
    assert result["interpretation"]["proxy_and_pfp_ranking_agree"] is False
    rows = {row["arm"]: row for row in result["rows"]}
    assert rows["continuous"]["technical_gate_pass"] is True
    assert rows["continuous"]["temperature_mean_K"] == 353.0
    assert rows["binary"]["temperature_mean_K"] == 353.0
