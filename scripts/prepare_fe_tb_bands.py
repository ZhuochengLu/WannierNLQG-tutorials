#!/usr/bin/env python3
"""Bind a newly computed Fe TB path to the verified VASP path and plot contract."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Materials/Fe/vasp_SOC/bands"
EF = 5.7156290716733436


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-bands", type=Path, required=True)
    parser.add_argument("--tb", type=Path, default=ROOT / "Materials/Fe/vasp_SOC/Fe_tb.dat")
    args = parser.parse_args()
    source = args.new_bands
    text = source.read_text().splitlines()[:5]
    match = re.search(r"energy_reference_E_ref_eV\s*=\s*([-+0-9.eE]+)", "\n".join(text))
    assert match and abs(float(match.group(1)) - EF) < 1e-9, "TB path uses a different energy reference"
    new = np.loadtxt(source)
    vasp = np.loadtxt(DATA / "Fe_vasp_path_absolute.dat")
    assert new.shape == (801, 22) and vasp.shape == (801, 65)
    assert np.isfinite(new).all()
    kpoints_file = DATA / "KPOINTS_path_lmaxmix4"
    kpoints = np.loadtxt(kpoints_file, skiprows=3, usecols=(0, 1, 2))
    k_error = float(np.max(np.abs(new[:, 1:4] - kpoints)))
    distance_error = float(np.max(np.abs(new[:, 0] - vasp[:, 0])))
    assert k_error <= 5e-7 and distance_error <= 5e-6, (k_error, distance_error)
    output = DATA / "Fe_tb_path_absolute.dat"
    receipt = DATA / "Fe_tb_path_receipt.json"
    manifest_file = DATA / "Fe_vasp_tb_bands.comparison.json"
    assert not any(path.exists() for path in (output, receipt, manifest_file)), "refusing to overwrite TB band artifacts"
    np.savetxt(output, np.column_stack((vasp[:, 0], new[:, 4:] + EF)), fmt="%.14e",
               header="distance_A^-1 " + " ".join(f"tb_band_{i}_absolute_eV" for i in range(1, 19)))
    summary = {
        "schema": "wanniernlqg-tutorials.fe-tb-path-bands",
        "schema_version": "1.0",
        "qualification": "DIAGNOSTIC_ONLY",
        "scf_fermi_energy_ev": EF,
        "source_bands_sha256": digest(source),
        "tb_sha256": digest(args.tb),
        "vasp_table_sha256": digest(DATA / "Fe_vasp_path_absolute.dat"),
        "fractional_kpoint_max_abs_difference": k_error,
        "distance_max_abs_difference_A_inverse": distance_error,
        "table_sha256": digest(output),
        "shape": [801, 18],
    }
    receipt.write_text(json.dumps(summary, indent=2) + "\n")
    ticks = [float(vasp[index, 0]) for index in (0, 200, 400, 600, 800)]
    manifest = {
        "output": {
            "stem": "../../../../examples/11_fe_oam_and_linear_response/figures/Fe_vasp_tb_path_comparison",
            "dpi": 600,
            "formats": ["png", "pdf"],
        },
        "comparison": {
            "purpose": "diagnostic",
            "title": "Fe SOC: DFT and 18-WF TB bands",
            "energy_reference": {"value_ev": EF, "label": "verified SOC SCF Fermi energy"},
            "degeneracy_tolerance_ev": 0.01,
            "reference": {
                "id": "fe_vasp",
                "label": "VASP SOC",
                "data": "Fe_vasp_path_absolute.dat",
                "x_column": 0,
                "energy_columns": {"start": 1, "stop": 65},
                "fitted_band_indices": {"start": 0, "stop": 64},
                "display_band_indices": "all",
            },
            "models": [{
                "id": "fe_tb",
                "label": "Fe 18-WF TB",
                "data": output.name,
                "x_column": 0,
                "energy_columns": {"start": 1, "stop": 19},
                "usable_for_bands": False,
                "qualification_label": "Physics HOLD",
                "matching": {"mode": "automatic"},
            }],
            "metric_windows": [
                {"id": "near_fermi", "label": "within 1 eV of Fermi energy", "min_ev": -1.0, "max_ev": 1.0},
                {"id": "display", "label": "display window", "min_ev": -8.0, "max_ev": 8.0},
            ],
            "error_window_id": "near_fermi",
            "xticks": ticks,
            "xticklabels": ["\\textGamma", "\\textnormal{H}", "\\textnormal{P}", "\\textnormal{N}", "\\textGamma"],
            "ylim": [-8.0, 8.0],
        },
    }
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
    print("FE_TB_BANDS_OK rows=801 bands=18 k_max_abs=" + str(k_error))


if __name__ == "__main__":
    main()
