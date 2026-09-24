#!/usr/bin/env python3
"""Check a new Fe TB path against the published VASP path and prepare plots."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MATERIAL = ROOT / "Materials/Fe/vasp_SOC"
REFERENCE = MATERIAL / "bands/Fe_vasp_path_absolute.dat"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def lattice(path):
    lines = path.read_text().splitlines()
    scale = float(lines[1].split()[0])
    if scale <= 0:
        raise ValueError("POSCAR must have one positive scale")
    return scale * np.array([[float(x) for x in line.split()[:3]] for line in lines[2:5]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path, help="same-run VASP source directory")
    parser.add_argument("output_dir", type=Path, help="output from wannierize_fe.jl")
    args = parser.parse_args()
    workdir, output = args.workdir.resolve(), args.output_dir.resolve()
    selected = json.loads((output / "selected_model.json").read_text())
    bands = json.loads((output / "bands_result.json").read_text())
    reference = json.loads((MATERIAL / "bands/Fe_vasp_path_receipt.json").read_text())
    raw_bands = Path(bands["table_path"])
    require(raw_bands.resolve().is_relative_to(output), "TB bands must come from this run")
    require(digest(raw_bands) == bands["table_sha256"], "TB band table hash changed")
    require(bands["tb_sha256"] == selected["artifacts"]["wannier90_tb"]["sha256"],
            "Band run used a different TB")
    require(digest(REFERENCE) == reference["table_sha256"], "Published VASP table hash changed")
    require(bands["reference_table_sha256"] == reference["table_sha256"],
            "Band run used a different VASP reference")
    for name, expected in selected["input_sha256"].items():
        require(digest(workdir / name) == expected, f"source input changed: {name}")
    require(digest(workdir / "POSCAR") == reference["input_sha256"]["POSCAR"],
            "Fe source POSCAR differs from the published path source")
    lattice_error = float(np.max(np.abs(lattice(workdir / "POSCAR") - lattice(MATERIAL / "POSCAR"))))
    require(lattice_error <= 1e-10, f"different Fe lattice: {lattice_error} angstrom")

    outcar_fermi = re.findall(r"E-fermi\s*:\s*([-+0-9.]+)", (workdir / "OUTCAR").read_text())
    require(outcar_fermi, "SCF Fermi energy missing from OUTCAR")
    fermi = float(reference["scf_fermi_energy_ev"])
    require(abs(float(outcar_fermi[-1]) - fermi) <= 5e-4, "SCF energy reference differs")
    require(abs(float(bands["energy_reference_ev"]) - fermi) <= 1e-12,
            "TB band energy reference differs")

    tb = np.loadtxt(raw_bands)
    dft = np.loadtxt(REFERENCE)
    path = np.loadtxt(MATERIAL / "bands/KPOINTS_path_lmaxmix4", skiprows=3, usecols=(0, 1, 2))
    require(tb.shape == (801, 22) and dft.shape == (801, 65) and path.shape == (801, 3),
            "Expected 801 points, 18 TB bands, and 64 VASP bands")
    require(np.isfinite(tb).all() and np.isfinite(dft).all(), "Nonfinite band energy")
    k_error = float(np.max(np.abs(tb[:, 1:4] - path)))
    distance_error = float(np.max(np.abs(tb[:, 0] - dft[:, 0])))
    require(k_error <= 5e-7 and distance_error <= 5e-6,
            f"TB and VASP paths differ: {k_error}, {distance_error}")
    kpath = output / "bands/bands/Fe_kpath.json"
    require(kpath.is_file(), "Band task did not publish its path sidecar")
    path_payload = json.loads(kpath.read_text())
    require(path_payload["schema"] == "wanniernlqg.kpath", "Unexpected KPath sidecar schema")
    require([node["point_index_one_based"] for node in path_payload["node_chain"]] ==
            [1, 201, 401, 601, 801], "Wrong KPath node positions")

    # A descriptive energy-set distance; many TB bands may select the same
    # VASP band, so this is deliberately not a band matching or quality gate.
    tb_absolute = tb[:, 4:] + fermi
    nearest_vasp = np.min(np.abs(tb_absolute[:, :, None] - dft[:, None, 1:]), axis=2)
    energy_set_error = {}
    for label, half_width in (("near_fermi", 1.0), ("display", 8.0)):
        values = nearest_vasp[np.abs(tb_absolute - fermi) <= half_width]
        energy_set_error[label] = {
            "tb_value_count": int(values.size),
            "mean_abs_ev": float(np.mean(values)) if values.size else None,
            "rms_ev": float(np.sqrt(np.mean(values**2))) if values.size else None,
            "max_abs_ev": float(np.max(values)) if values.size else None,
        }

    # The two path calculators differ at sub-micro-A^-1 precision. After
    # auditing their coordinates and distances, share the TB x grid for the
    # strict plotting parser. Reference energies are copied without a shift.
    aligned_reference = output / "Fe_vasp_aligned_path_absolute.dat"
    table = output / "Fe_new_tb_path_absolute.dat"
    visualization_path = output / "Fe_visualization_path.json"
    for target in (aligned_reference, table, visualization_path,
                   output / "band_plot.json", output / "comparison_result.json"):
        require(not target.exists(), f"refusing to replace {target.name}")
    np.savetxt(aligned_reference, np.column_stack((tb[:, 0], dft[:, 1:])),
               fmt="%.14e", header="distance_A^-1 " + " ".join(
                   f"vasp_band_{i}_absolute_eV" for i in range(1, 65)))

    # The Band task writes E-E_ref. Put the new TB on the VASP absolute scale;
    # this is the same declared SCF reference, not a fitted alignment.
    np.savetxt(table, np.column_stack((tb[:, 0], tb_absolute)),
               fmt="%.14e", header="distance_A^-1 " + " ".join(
                   f"tb_band_{i}_absolute_eV" for i in range(1, 19)))

    visualization_path.write_text(json.dumps({
        "schema": "wanniernlqg.visualization-band-path", "schema_version": "1.0",
        "distance_unit": "A^-1", "energy_unit": "eV",
        "kpoint_coordinate_convention": "fractional_crystal",
        "fractional_kpoints": tb[:, 1:4].tolist(),
        "distances_A_inverse": tb[:, 0].tolist(),
        "energy_reference_ev": fermi,
        "nodes": [{"index_zero_based": i, "label": label} for i, label in
                  zip((0, 200, 400, 600, 800), ("Γ", "H", "P", "N", "Γ"))],
    }, indent=2) + "\n")
    common = {
        "energy_unit": "ev", "energy_convention": "absolute",
        "path": str(visualization_path), "x_column": 0,
    }
    config = {
        "mode": "compare", "comparison_audit": "display_only",
        "energy_window": [-8.0, 8.0],
        "title": "Fe SOC: diagnostic bands (Physics HOLD)",
        "reference": dict(common, type="table", id="fe_vasp", label="VASP SOC",
                          data=str(aligned_reference), energy_columns={"start": 1, "stop": 65}),
        "models": [dict(common, type="table", id="new_fe_tb", label="New 18-WF TB (diagnostic)",
                        data=str(table), energy_columns={"start": 1, "stop": 19})],
        "output": {"stem": str(output / "Fe_new_tb_vs_vasp"), "formats": ["png"]},
    }
    (output / "band_plot.json").write_text(json.dumps(config, indent=2) + "\n")
    summary = {
        "schema": "wanniernlqg-tutorials.fe-wannierization-comparison",
        "schema_version": "1.0", "qualification": "DIAGNOSTIC_ONLY",
        "solver_status": selected["status"], "selected_attempt": selected["selected_attempt"],
        "profile": selected["profile"], "source_manifest_sha256": selected["source_manifest_sha256"],
        "source_input_sha256": selected["input_sha256"],
        "tb_sha256": bands["tb_sha256"],
        "tb_band_sha256": bands["table_sha256"],
        "vasp_band_sha256": reference["table_sha256"],
        "aligned_vasp_band_sha256": digest(aligned_reference),
        "comparison_table_sha256": digest(table),
        "path_point_count": 801, "tb_band_count": 18, "vasp_band_count": 64,
        "lattice_max_abs_angstrom": lattice_error,
        "fractional_kpoint_max_abs": k_error,
        "distance_max_abs_A_inverse": distance_error,
        "common_energy_reference_ev": fermi,
        "nearest_vasp_energy_set_error_ev": energy_set_error,
        "comparison_scope": "energy-set display only; no wavefunction matching or material pass",
    }
    (output / "comparison_result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"FE_BAND_COMPARISON_READY k_max_abs={k_error} distance_max_abs={distance_error}")


if __name__ == "__main__":
    main()
