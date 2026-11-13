#!/usr/bin/env python3
"""Render the Haldane phase diagram, bands, Hall curves, and convergence."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
import os, sys
_CHAPTER = Path(__file__).resolve().parent
sys.path.insert(0, str(_CHAPTER))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.ticker import FormatStrFormatter


ROOT = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(ROOT))
DATA = Path(os.environ.get("WANNIERNLQG_PLOT_DATA", str(ROOT / "data")))
FIGURES = Path(os.environ.get("WANNIERNLQG_FIGURE_OUTPUT", str(ROOT / "figures")))
PHASES = ("topological", "trivial", "reversed")
COLORS = {"topological": "#2166ac", "trivial": "#555555", "reversed": "#b2182b"}
T1, T2 = -1.0, 0.15
PARAMETERS = {
    "topological": (0.2, np.pi / 2, 1),
    "trivial": (1.0, np.pi / 2, 0),
    "reversed": (0.2, -np.pi / 2, -1),
}
LATTICE_2D = np.array([[1.0, 0.0], [0.5, np.sqrt(3) / 2]])
RECIPROCAL_2D = 2 * np.pi * np.linalg.inv(LATTICE_2D).T
BAND_VERTICES = np.array([[0.0, 0.0], [1 / 3, 2 / 3], [0.5, 0.5],
                          [2 / 3, 1 / 3], [0.0, 0.0]])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_render_environment():
    findfont(FontProperties(family="Times New Roman"), fallback_to_default=False)
    if shutil.which("pdflatex") is None or shutil.which("kpsewhich") is None:
        raise RuntimeError("pdflatex and kpsewhich are required to render these figures")
    for package in ("newtxtext.sty", "newtxmath.sty", "bm.sty", "textgreek.sty"):
        found = subprocess.run(["kpsewhich", package], capture_output=True, text=True, check=True)
        if not found.stdout.strip():
            raise RuntimeError(f"missing TeX package: {package}")
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman"],
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage{newtxtext,newtxmath,bm,textgreek}",
        "font.size": 12,
        "axes.linewidth": 1.1,
        "axes.labelsize": 14,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 10,
        "savefig.facecolor": "white",
    })


def finish(fig, stem):
    fig.tight_layout(pad=0.8)
    FIGURES.mkdir(exist_ok=True)
    files = []
    for suffix in ("png", "pdf"):
        path = FIGURES / f"{stem}.{suffix}"
        fig.savefig(path, dpi=600, bbox_inches="tight", facecolor="white")
        files.append(path)
    plt.close(fig)
    return files


def check_model_identity():
    """The plotted parameterization must match the checked tutorial model."""
    reference = json.loads((DATA / "reference.json").read_text())
    model = ROOT.parents[1] / "models" / 'haldane/HaldaneModel.jl'
    if digest(model) != reference["model_source_sha256"]:
        raise RuntimeError("HaldaneModel.jl differs from the checked reference")
    if not np.isclose(reference["critical_mass_ev"], 3 * np.sqrt(3) * T2):
        raise RuntimeError("phase-boundary parameter differs from the checked reference")


def plot_phase_diagram():
    phi = np.linspace(-np.pi, np.pi, 1201)
    boundary = 3 * np.sqrt(3) * np.sin(phi)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.fill_between(phi, -7, -np.abs(boundary), color="#dedede")
    ax.fill_between(phi, np.abs(boundary), 7, color="#dedede")
    ax.fill_between(phi, -np.abs(boundary), np.abs(boundary),
                    where=boundary > 0, color="#bad3e7")
    ax.fill_between(phi, -np.abs(boundary), np.abs(boundary),
                    where=boundary < 0, color="#e6b4b8")
    ax.plot(phi, boundary, color="#252525", lw=1.35)
    ax.plot(phi, -boundary, color="#252525", lw=1.35)
    markers = {"topological": "o", "trivial": "s", "reversed": "D"}
    names = {"topological": "topological", "trivial": "trivial", "reversed": "reversed"}
    for phase in PHASES:
        mass, angle, chern = PARAMETERS[phase]
        expected = int(np.sign(np.sin(angle))) if abs(mass) < 3 * np.sqrt(3) * T2 * abs(np.sin(angle)) else 0
        assert chern == expected
        ax.plot(angle, mass / T2, marker=markers[phase], ms=9, ls="none",
                markerfacecolor="white", markeredgecolor="#111111", markeredgewidth=1.4,
                label=(rf"{names[phase]}: $C=+1$" if chern > 0 else
                       rf"{names[phase]}: $C=\textnormal{{-1}}$" if chern < 0 else
                       "trivial: $C=0$"))
    cmap = ListedColormap(["#e6b4b8", "#dedede", "#bad3e7"])
    norm = BoundaryNorm([-1.5, -0.5, 0.5, 1.5], cmap.N)
    colorbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                            ticks=[-1, 0, 1], pad=0.025, fraction=0.055)
    colorbar.set_ticklabels((r"\textnormal{-1}", "0", "1"))
    colorbar.set_label(r"Occupied-band Chern number $C$")
    ax.set(xlabel=r"Complex hopping phase $\phi$", ylabel=r"Sublattice mass $M/t_2$",
           xlim=(-np.pi, np.pi), ylim=(-7, 7))
    ax.set_xticks((-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi),
                  (r"$\textnormal{-}\pi$", r"$\textnormal{-}\pi/2$",
                   "0", r"$\pi/2$", r"$\pi$"))
    ax.set_yticks((-6, -4, -2, 0, 2, 4, 6),
                  (r"\textnormal{-6}", r"\textnormal{-4}", r"\textnormal{-2}",
                   "0", "2", "4", "6"))
    ax.tick_params(direction="in", top=True, right=True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3,
              frameon=True)
    return finish(fig, "haldane_phase_diagram")


def analytic_eigenvalues(reduced_k, mass, phi):
    """Same closed-form two-band Hamiltonian as HaldaneModel.analytic_hamiltonian."""
    u, v = 2 * np.pi * reduced_k
    off_diagonal = T1 * (1 + np.exp(-1j * u) + np.exp(-1j * v))
    aa_sum = np.cos(u - phi) + np.cos(v - u - phi) + np.cos(-v - phi)
    bb_sum = np.cos(u + phi) + np.cos(v - u + phi) + np.cos(-v + phi)
    aa, bb = -mass + 2 * T2 * aa_sum, mass + 2 * T2 * bb_sum
    return np.linalg.eigvalsh([[aa, off_diagonal], [np.conj(off_diagonal), bb]])


def build_band_table():
    """Write raw bands along a path containing both inequivalent valleys."""
    reduced = np.vstack([
        np.linspace(start, stop, 101, endpoint=False)
        for start, stop in zip(BAND_VERTICES[:-1], BAND_VERTICES[1:])
    ] + [BAND_VERTICES[-1:]])
    cartesian = reduced @ RECIPROCAL_2D
    distance = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(cartesian, axis=0), axis=1))]
    vertex_distance = distance[[0, 101, 202, 303, 404]]
    columns = [distance]
    valley_gaps = {}
    for phase in PHASES:
        mass, phi, _ = PARAMETERS[phase]
        energies = np.array([analytic_eigenvalues(k, mass, phi) for k in reduced])
        assert energies.shape == (405, 2) and np.isfinite(energies).all()
        gaps = [float(np.ptp(energies[index])) for index in (101, 303)]
        expected_gaps = sorted(2 * abs(mass + sign * 3 * np.sqrt(3) * T2 * np.sin(phi))
                               for sign in (-1, 1))
        assert np.allclose(sorted(gaps), expected_gaps, atol=1e-12)
        valley_gaps[phase] = {"K": gaps[0], "K_prime": gaps[1]}
        columns.extend((energies[:, 0], energies[:, 1]))
    table = np.column_stack(columns)
    path = DATA / "bands_gamma_k_m_kprime_gamma.tsv"
    np.savetxt(path, table, fmt="%.12e", delimiter="\t",
               header="distance_1_per_angstrom topological_valence_eV topological_conduction_eV "
                      "trivial_valence_eV trivial_conduction_eV reversed_valence_eV "
                      "reversed_conduction_eV")
    critical = 3 * np.sqrt(3) * T2
    assert np.ptp(analytic_eigenvalues(BAND_VERTICES[1], critical, np.pi / 2)) < 1e-10
    return path, vertex_distance, valley_gaps


def plot_bands(table_path, vertex_distance):
    table = np.loadtxt(table_path)
    assert table.shape == (405, 7) and np.isfinite(table).all()
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.8), sharex=True, sharey=True)
    titles = {"topological": r"Topological ($C=+1$)",
              "trivial": r"Trivial ($C=0$)",
              "reversed": r"Reversed phase ($C=\textnormal{-1}$)"}
    for index, (phase, ax) in enumerate(zip(PHASES, axes)):
        mass, phi, _ = PARAMETERS[phase]
        for band in (0, 1):
            ax.plot(table[:, 0], table[:, 1 + 2 * index + band],
                    color=COLORS[phase], lw=1.6)
        for x in vertex_distance[1:-1]:
            ax.axvline(x, color="#c8c8c8", lw=0.8, zorder=0)
        ax.axhline(0, color="#555555", lw=0.9, ls=(0, (4, 3)), zorder=0)
        ax.set(title=titles[phase], xlim=(0, vertex_distance[-1]), ylim=(-3.6, 3.6))
        ax.set_xticks(vertex_distance,
                      (r"\textGamma", r"\textnormal{K}", r"\textnormal{M}",
                       r"$\mathrm{K}^{\prime}$", r"\textGamma"))
        phase_sign = "+" if phi > 0 else r"\textnormal{-}"
        ax.text(0.5, 0.96,
                rf"$M={mass:.1f}\,\mathrm{{eV}},\ \phi={phase_sign}\pi/2$",
                transform=ax.transAxes, ha="center", va="top", fontsize=10)
        ax.tick_params(direction="in", top=True, right=True)
    axes[0].set_ylabel(r"Band energy $E$ (eV)")
    axes[0].set_yticks((-3, -2, -1, 0, 1, 2, 3),
                       (r"\textnormal{-3}", r"\textnormal{-2}", r"\textnormal{-1}",
                        "0", "1", "2", "3"))
    return finish(fig, "haldane_bands")


def plot_hall():
    table = np.loadtxt(DATA / "hall_curves.tsv", comments="#")
    assert table.shape == (121, 7) and np.isfinite(table).all()
    assert abs(table[60, 0]) < 1e-14
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for index, phase in enumerate(PHASES):
        tb = table[:, 1 + 2 * index]
        analytic = table[:, 2 + 2 * index]
        ax.plot(table[:, 0], tb, color=COLORS[phase], lw=2.2, alpha=0.55,
                label=f"{phase}, real space TB")
        ax.plot(table[:, 0], analytic, color=COLORS[phase], lw=1.2,
                ls=(0, (5, 3)),
                label=f"{phase}, analytic $H(\\mathbf{{k}})$")
    for level in (-1, 0, 1):
        ax.axhline(level, color="#bbbbbb", lw=0.6, zorder=0)
    ax.set(xlabel=r"Chemical potential $\mu$ (eV)",
           ylabel=r"Sheet Hall conductance $G_H/(e^2/h)$", xlim=(-1.5, 1.5))
    ax.set_xticks((-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5),
                  (r"\textnormal{-1.5}", r"\textnormal{-1.0}",
                   r"\textnormal{-0.5}", "0.0", "0.5", "1.0", "1.5"))
    ax.set_yticks((-1.0, -0.5, 0.0, 0.5, 1.0),
                  (r"\textnormal{-1.0}", r"\textnormal{-0.5}",
                   "0.0", "0.5", "1.0"))
    ax.tick_params(direction="in", top=True, right=True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18),
              frameon=True, ncol=3)
    return finish(fig, "haldane_hall_vs_mu")


def plot_convergence():
    rows = {}
    with (DATA / "convergence.tsv").open() as stream:
        for line in stream:
            if not line.startswith("#"):
                name, mesh, gamma, hall = line.split()
                rows[name] = (int(mesh), float(gamma), float(hall))
    assert len(rows) == 4 and all(np.isfinite(row[-1]) for row in rows.values())
    mesh_names = ("tb_topological_n61_g002", "tb_topological", "tb_topological_n181_g002")
    gamma_names = ("tb_topological_n121_g001", "tb_topological")
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.8), sharey=True)
    axes[0].plot([rows[name][0] for name in mesh_names],
                 [abs(rows[name][2] + 1) for name in mesh_names],
                 "o-", color=COLORS["topological"])
    axes[0].set_xlabel(r"In-plane mesh $N\times N$")
    axes[1].plot([rows[name][1] for name in gamma_names],
                 [abs(rows[name][2] + 1) for name in gamma_names],
                 "o-", color=COLORS["reversed"])
    axes[1].set_xlabel(r"Relaxation rate $\gamma$ (eV)")
    axes[0].set_ylabel(r"$|G_H/(e^2/h)+1|$ at $\mu=0$")
    for ax in axes:
        ax.set_ylim(0, 1.4e-4)
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.1e"))
        ax.tick_params(direction="in", top=True, right=True)
    return finish(fig, "haldane_convergence")


def main():
    os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
    check_render_environment()
    check_model_identity()
    band_table, vertices, valley_gaps = build_band_table()
    inputs = [DATA / "hall_curves.tsv", DATA / "convergence.tsv",
              DATA / "reference.json", ROOT.parents[1] / "models" / 'haldane/HaldaneModel.jl', band_table,
              Path(__file__)]
    outputs = plot_phase_diagram() + plot_bands(band_table, vertices)
    outputs += plot_hall() + plot_convergence()
    receipt = {
        "schema": "wanniernlqg-tutorials.haldane-figures/1.1",
        "qualification": "PRESENTATION_ONLY",
        "matplotlib_version": matplotlib.__version__,
        "band_path": {"labels": ["Gamma", "K", "M", "K_prime", "Gamma"],
                      "distance_1_per_angstrom": vertices.tolist(),
                      "points": 405,
                      "direct_valley_gaps_ev": valley_gaps},
        "inputs_sha256": {os.path.relpath(path,ROOT): digest(path) for path in inputs},
        "outputs_sha256": {os.path.relpath(path,ROOT): digest(path) for path in outputs},
    }
    (FIGURES / "FIGURE_SHA256.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("HALDANE_FIGURES_OK", len(outputs))


if __name__ == "__main__":
    main()
