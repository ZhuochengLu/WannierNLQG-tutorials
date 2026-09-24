#!/usr/bin/env python3
"""Export the receipt-verified Fe VASP path as a small, portable band table."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EF = 5.7156290716733436
EXPECTED = {
    "POSCAR": "0706c1b1c7630dc2f92e886e49ef07c124c00748051f17e85de513e30d286071",
    "KPOINTS": "40d272fe7e9c7d6df1a33896a5d5dea316eb741e249a3da421248ceaf2ec42c8",
    "EIGENVAL": "7e21132de34b59445847ed2c2f5d485daab72c2f54ead42b43cc3c9c48e72b4a",
    "SCF_EIGENVAL": "f37745c1515dbe7156ab05bd7ef424d5a60817656b7981d67c865f974c5a8aa6",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_eigenval(path):
    lines = path.read_text().splitlines()
    fields = [int(x) for x in lines[5].split()]
    nk, nb = fields[1:3]
    kpoints, energies = [], []
    cursor = 6
    for _ in range(nk):
        while not lines[cursor].strip():
            cursor += 1
        kpoints.append([float(x) for x in lines[cursor].split()[:3]])
        cursor += 1
        row = []
        for _ in range(nb):
            row.append(float(lines[cursor].split()[1]))
            cursor += 1
        energies.append(row)
    return np.asarray(kpoints), np.asarray(energies)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path-root", type=Path, required=True)
    parser.add_argument("--scf-root", type=Path, required=True)
    parser.add_argument("--poscar", type=Path, required=True)
    args = parser.parse_args()
    path_root, scf_root = args.path_root, args.scf_root
    inputs = {
        "POSCAR": args.poscar,
        "KPOINTS": path_root / "KPOINTS",
        "EIGENVAL": path_root / "EIGENVAL",
        "SCF_EIGENVAL": scf_root / "EIGENVAL",
    }
    actual = {name: digest(path) for name, path in inputs.items()}
    assert actual == EXPECTED, "VASP band source identity mismatch"
    k_eig, energies = read_eigenval(inputs["EIGENVAL"])
    k_path = np.loadtxt(inputs["KPOINTS"], skiprows=3, usecols=(0, 1, 2))
    assert k_eig.shape == k_path.shape == (801, 3)
    assert energies.shape == (801, 64)
    k_error = float(np.max(np.abs(k_eig - k_path)))
    assert k_error <= 5e-7, k_error
    poscar = args.poscar.read_text().splitlines()
    lattice = float(poscar[1]) * np.array([[float(x) for x in poscar[i].split()] for i in range(2, 5)])
    reciprocal = 2 * np.pi * np.linalg.inv(lattice).T
    distance = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(k_path, axis=0) @ reciprocal, axis=1))]
    scf_k, scf_e = read_eigenval(inputs["SCF_EIGENVAL"])
    gamma = int(np.argmin(np.linalg.norm(scf_k, axis=1)))
    mask = np.abs(scf_e[gamma] - EF) <= 8.0
    gamma_error = float(np.max(np.abs(energies[0, mask] - scf_e[gamma, mask])))
    assert gamma_error <= 0.005, gamma_error
    assert np.isfinite(energies).all()

    out_dir = ROOT / "Materials/Fe/vasp_SOC/bands"
    out_dir.mkdir(parents=True, exist_ok=True)
    table = out_dir / "Fe_vasp_path_absolute.dat"
    receipt = out_dir / "Fe_vasp_path_receipt.json"
    assert not table.exists() and not receipt.exists(), "refusing to overwrite VASP band export"
    np.savetxt(table, np.column_stack((distance, energies)), fmt="%.14e",
               header="distance_A^-1 " + " ".join(f"band_{i}_absolute_eV" for i in range(1, 65)))
    payload = {
        "schema": "wanniernlqg-tutorials.fe-vasp-path-bands",
        "schema_version": "1.0",
        "source": "validated fixed-charge LMAXMIX=4 path attempt04; VASP not rerun",
        "scf_fermi_energy_ev": EF,
        "path": "Gamma-H-P-N-Gamma",
        "shape": [801, 64],
        "fractional_kpoint_max_abs_difference": k_error,
        "gamma_near_fermi_max_abs_ev": gamma_error,
        "gamma_gate_threshold_ev": 0.005,
        "input_sha256": actual,
        "table_sha256": digest(table),
        "qualification": "DIAGNOSTIC_ONLY",
    }
    receipt.write_text(json.dumps(payload, indent=2) + "\n")
    print("FE_VASP_BANDS_OK rows=801 bands=64 gamma_max_abs_ev=" + str(gamma_error))


if __name__ == "__main__":
    main()
