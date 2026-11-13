#!/usr/bin/env python3
"""Independent Rice--Mele reference spectrum and result checks.

Only the Python standard library is needed. No WannierNLQG response routine is used.
"""

import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
T, A, AREA, ETA = -1.0, 4.0, 9.37, 0.05
CHARGE = 1.602176634e-19
HBAR_EV = 6.582119569e-16
HBAR_J = 1.054571817e-34
PHASES = {
    "polar": (-0.83, -0.45),
    "reversed": (-0.83, 0.45),
    "ssh": (-0.83, 0.0),
    "ionic": (0.0, -0.45),
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def energy(k, delta, mass):
    q = k * A / 2
    return math.sqrt(T * T * math.cos(q) ** 2 + delta * delta * math.sin(q) ** 2 + mass * mass)


def shift_vector(k, delta, mass):
    """Return the transition shift vector in Angstrom using this reference function's convention."""
    e = energy(k, delta, mass)
    ka = k * A
    t2, d2, m2 = T * T, delta * delta, mass * mass
    numerator = (d2 - t2) * (4 * e * e * math.cos(ka) + (t2 - d2) * math.sin(ka) ** 2)
    denominator = m2 * (d2 - t2) * math.sin(ka) ** 2 + 4 * t2 * d2 * e * e
    return mass * A * T * delta / (2 * e) * (numerator / denominator - 1 / (e * e - m2))


def dipole_squared(k, delta, mass):
    """|r_cv|^2 = |d x d'|^2/(4 E^4) from the two-level projector."""
    q = k * A / 2
    d = (T * math.cos(q), -delta * math.sin(q), mass)
    dp = (-T * A / 2 * math.sin(q), -delta * A / 2 * math.cos(q), 0.0)
    cross = (d[1] * dp[2] - d[2] * dp[1],
             d[2] * dp[0] - d[0] * dp[2],
             d[0] * dp[1] - d[1] * dp[0])
    e = energy(k, delta, mass)
    return sum(x * x for x in cross) / (4 * e ** 4)


def analytic_spectrum(omega, delta, mass, mesh):
    """Brillouin-zone R|r|^2 integral with the declared Gaussian line shape."""
    prefactor = math.pi * (-CHARGE) ** 3 * HBAR_EV / (HBAR_J ** 2 * A * AREA)
    spectrum = [0.0] * len(omega)
    for i in range(mesh):
        k = 2 * math.pi * i / (mesh * A)
        transition = 2 * energy(k, delta, mass)
        weight = shift_vector(k, delta, mass) * dipole_squared(k, delta, mass)
        for j, photon in enumerate(omega):
            x = photon - transition
            if abs(x) < 5 * ETA:
                spectrum[j] += weight * math.exp(-(x / ETA) ** 2) / (math.sqrt(math.pi) * ETA)
    return [prefactor * value / mesh for value in spectrum]


def load_case(profile, case):
    directory = ROOT / "results" / profile / case
    summary = json.loads((directory / "summary.json").read_text())
    require(summary["package_version"] == "1.2.0", f"WRONG_VERSION {case}")
    require(summary["finite_values"], f"NONFINITE_FLAG {case}")
    require(summary["input_sha256"]["RiceMeleModel.jl"] == sha(ROOT / "RiceMeleModel.jl"),
            f"MODEL_HASH {case}")
    require(summary["output_files"] == ["rice_mele_sc_conv.dat"], f"OUTPUT_LIST {case}")
    path = directory / "rice_mele_sc_conv.dat"
    require(summary["output_sha256"][path.name] == sha(path), f"OUTPUT_HASH {case}")
    metadata_path = directory / "metadata.txt"
    metadata = metadata_path.read_text()
    expected_route = "native_real_space" if case.startswith("tb_") else "analytic_k"
    expected_derivative = "ANALYTIC_FOURIER" if case.startswith("tb_") else "automatic"
    require(re.search(r"^model_input_mode\s*=\s*" + expected_route + r"$", metadata, re.M),
            f"ACTUAL_INPUT_ROUTE {case}")
    require(re.search(r"^native_derivative_method\s*=\s*" + expected_derivative + r"$", metadata, re.M),
            f"ACTUAL_DERIVATIVE_ROUTE {case}")
    require(re.search(r"^backend\s*=\s*direct$", metadata, re.M), f"ACTUAL_BACKEND {case}")
    summary["_metadata_sha256"] = sha(metadata_path)
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        values = [float(x) for x in line.split()]
        require(len(values) == 18 and all(math.isfinite(x) for x in values), f"OUTPUT_SHAPE {case}")
        rows.append(values)
    expected_count = 401 if profile == "reference" else 21
    require(len(rows) == expected_count, f"ENERGY_COUNT {case}")
    step = 0.01 if profile == "reference" else 0.2
    require(all(abs(row[0]) < 1e-13 and abs(row[1] - i * step) < 1e-12
                for i, row in enumerate(rows)), f"ENERGY_AXIS {case}")
    return [row[1] for row in rows], [row[2] for row in rows], summary


def write_tsv(name, header, rows):
    path = ROOT / "data" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows)
    return sha(path)


def max_fraction(left, right, scale):
    return max(abs(a - b) for a, b in zip(left, right)) / scale


def peak_position(omega, sigma, low, high):
    candidates = [i for i, x in enumerate(omega) if low <= x <= high]
    return omega[max(candidates, key=lambda i: abs(sigma[i]))]


def validate(profile):
    require(profile in ("smoke", "reference"), "BAD_PROFILE")
    curves = {}
    summaries = {}
    for phase in PHASES:
        for route in ("tb", "analytic"):
            name = f"{route}_{phase}"
            omega, sigma, summary = load_case(profile, name)
            curves[name] = sigma
            summaries[name] = summary
    scale = max(abs(x) for x in curves["tb_polar"])
    require(scale > 1e-8, "POLAR_RESPONSE_MISSING")
    omega = load_case(profile, "tb_polar")[0]
    checks = {"profile": profile, "package_version": "1.2.0", "polar_peak_A_per_V2": scale,
              "actual_route_metadata_sha256": {name: value["_metadata_sha256"]
                                                 for name, value in summaries.items()},
              "tolerances_fraction_of_polar_peak": {"route": 0.001, "analytic": 0.02,
                                                    "reversal": 0.001, "inversion": 0.0001,
                                                    "mesh": 0.005}}
    if profile == "reference":
        routes = {phase: max_fraction(curves[f"tb_{phase}"], curves[f"analytic_{phase}"], scale)
                  for phase in PHASES}
        require(max(routes.values()) < 0.001, f"ROUTE_MISMATCH {routes}")
        reversal = max(abs(x + y) for x, y in zip(curves["tb_polar"], curves["tb_reversed"])) / scale
        require(reversal < 0.001, f"POLARIZATION_REVERSAL {reversal}")
        zeros = {phase: max(abs(x) for x in curves[f"tb_{phase}"]) / scale
                 for phase in ("ssh", "ionic")}
        require(max(zeros.values()) < 0.0001, f"INVERSION_RESPONSE {zeros}")
        analytical = {}
        discrepancies = {}
        peaks = {}
        for phase in ("polar", "reversed"):
            delta, mass = PHASES[phase]
            expected = analytic_spectrum(omega, delta, mass, 801)
            analytical[phase] = expected
            discrepancies[phase] = max_fraction(curves[f"tb_{phase}"], expected, scale)
            require(discrepancies[phase] < 0.02, f"ANALYTIC_SPECTRUM {phase} {discrepancies[phase]}")
            peaks[phase] = {}
            for label, low, high in (("low", 1.85, 2.02), ("high", 2.08, 2.25)):
                got = peak_position(omega, curves[f"tb_{phase}"], low, high)
                exact = peak_position(omega, expected, low, high)
                require(abs(got - exact) <= 0.02, f"PEAK_POSITION {phase} {label}")
                peaks[phase][label] = {"computed_eV": got, "analytic_eV": exact}
        _, coarse, _ = load_case(profile, "tb_polar_n401")
        _, fine, _ = load_case(profile, "tb_polar_n1601")
        mesh_difference = max_fraction(curves["tb_polar"], fine, scale)
        require(mesh_difference < 0.005, f"MESH_NOT_CONVERGED {mesh_difference}")
        curves_hash = write_tsv("shift_current_curves.tsv",
                                ["photon_eV"] + [f"sigma_xxx_{name}_A_per_V2" for name in curves] +
                                ["sigma_xxx_eq21_polar_A_per_V2", "sigma_xxx_eq21_reversed_A_per_V2"],
                                [[omega[i]] + [curves[name][i] for name in curves] +
                                 [analytical["polar"][i], analytical["reversed"][i]]
                                 for i in range(len(omega))])
        convergence_hash = write_tsv("convergence.tsv",
                                     ["photon_eV", "sigma_n401", "sigma_n801", "sigma_n1601"],
                                     [[omega[i], coarse[i], curves["tb_polar"][i], fine[i]]
                                      for i in range(len(omega))])
        checks.update(route_max_fraction=routes, reversal_max_fraction=reversal,
                      inversion_max_fraction=zeros, analytic_max_fraction=discrepancies,
                      peak_positions=peaks, mesh_801_1601_max_fraction=mesh_difference,
                      mesh_401_801_max_fraction=max_fraction(coarse, curves["tb_polar"], scale),
                      analytic_bandgap_eV=2 * math.sqrt(0.83 ** 2 + 0.45 ** 2),
                      analytic_transition_upper_eV=2 * math.sqrt(T * T + 0.45 ** 2),
                      shift_current_curves_sha256=curves_hash,
                      convergence_sha256=convergence_hash)
    output = ROOT / "data" / f"{profile}_spectrum.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n")
    print(f"RICE_MELE_SPECTRUM_OK profile={profile} output={output.relative_to(ROOT)}")


if __name__ == "__main__":
    validate(sys.argv[1] if len(sys.argv) > 1 else "reference")
