#!/usr/bin/env python3
"""Rebuild checked Rice--Mele band, shift-vector, response and convergence plots."""

import csv
import argparse
import os
import sys
import hashlib
import json
from pathlib import Path
import os, sys
_CHAPTER = Path(__file__).resolve().parent
sys.path.insert(0, str(_CHAPTER))
import shutil
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.ticker import FuncFormatter

from reference_checks import A, PHASES, ROOT, energy, shift_vector

DATA = Path(os.environ.get("WANNIERNLQG_PLOT_DATA", str(ROOT / "data")))
FIGURES = Path(os.environ.get("WANNIERNLQG_FIGURE_OUTPUT", str(ROOT / "figures")))
COLORS = {"polar": "#104E8B", "reversed": "#C71585", "ssh": "#3CB371", "ionic": "#606060"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_environment():
    findfont(FontProperties(family="Times New Roman"), fallback_to_default=False)
    if not shutil.which("pdflatex") or not shutil.which("kpsewhich"):
        raise RuntimeError("pdflatex and kpsewhich are required")
    for name in ("newtxtext.sty", "newtxmath.sty", "bm.sty", "textgreek.sty"):
        result = subprocess.run(["kpsewhich", name], capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            raise RuntimeError(f"missing TeX package {name}")
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman"],
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage{newtxtext,newtxmath,bm,textgreek}",
        "font.size": 12, "axes.labelsize": 14, "xtick.labelsize": 11,
        "ytick.labelsize": 11, "legend.fontsize": 10,
        "axes.linewidth": 1.1, "savefig.facecolor": "white",
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


def style(ax):
    ax.tick_params(direction="in", top=True, right=True)
    def signed(value, _position):
        magnitude = f"{abs(value):g}"
        return r"\textnormal{-}" + magnitude if value < -1e-12 else magnitude
    ax.xaxis.set_major_formatter(FuncFormatter(signed))
    ax.yaxis.set_major_formatter(FuncFormatter(signed))
    for spine in ax.spines.values():
        spine.set_linewidth(1.1)


def bands_and_shift_vector():
    reduced = np.linspace(-1, 1, 401)
    ks = reduced * np.pi / A
    delta, mass = PHASES["polar"]
    energies = np.array([energy(float(k), delta, mass) for k in ks])
    vectors = np.array([shift_vector(float(k), delta, mass) for k in ks])
    path = DATA / "bands_shift_vector.tsv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(("ka_over_pi", "valence_eV", "conduction_eV", "R_cv_angstrom"))
        writer.writerows(zip(reduced, -energies, energies, vectors))
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
    axes[0].plot(reduced, -energies, color="#104E8B", lw=1.6, label="valence")
    axes[0].plot(reduced, energies, color="#FF7F24", lw=1.6, label="conduction")
    axes[0].set(ylabel=r"$E\ (\mathrm{eV})$", xlabel=r"$ka/\pi$", xlim=(-1, 1))
    axes[0].legend(frameon=True, facecolor="white", edgecolor="gray")
    axes[1].plot(reduced, vectors, color="#104E8B", lw=1.6, label=r"$R_{cv}^{x}$")
    axes[1].plot(reduced, -vectors, color="#C71585", lw=1.6, ls="--",
                 label=r"$R_{cv}^{x}$, reversed")
    axes[1].set(ylabel=r"$R_{cv}^{x}\ (\mathrm{\AA})$", xlabel=r"$ka/\pi$", xlim=(-1, 1))
    axes[1].legend(frameon=True, facecolor="white", edgecolor="gray")
    for ax, label in zip(axes, ("(a)", "(b)")):
        style(ax)
        ax.text(0.03, 0.94, label, transform=ax.transAxes, va="top")
    return [path], finish(fig, "rice_mele_bands_shift_vector")


def read_table(path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {name: np.array([float(row[name]) for row in rows])
                for rows in [list(reader)] for name in reader.fieldnames}


def response_plot(figure_tool=None, output_directory=None):
    """Display-only 1x2 comparison from the preserved ten-series raw table."""
    table = read_table(DATA / "shift_current_curves.tsv")
    omega = table["photon_eV"]
    directory = Path(output_directory) if output_directory else FIGURES
    directory.mkdir(parents=True, exist_ok=True)
    fields = [f"sigma_xxx_{route}_{phase}_A_per_V2"
              for route in ("tb", "analytic", "eq21") for phase in ("polar", "reversed")]
    data = np.column_stack([omega, *(table[field] for field in fields)])
    # All displayed values are unchanged SI values; 1e6 below is solely A -> microA.
    np.savetxt(directory / "rice_mele_shift_current.display.dat", data,
               fmt="%.17g", header="photon_eV " + " ".join(fields))
    indices = sorted(set(range(0, len(omega), 20)) | set(range(160, 245, 4)))
    reference = np.column_stack([omega[indices], table[fields[4]][indices], table[fields[5]][indices]])
    np.savetxt(directory / "rice_mele_shift_current.markers.dat", reference,
               fmt="%.17g", header="photon_eV polar_reference_A_per_V2 reversed_reference_A_per_V2")
    scale = float(np.max(np.abs(table[fields[0]])))
    differences = {route: max(float(np.max(np.abs(table[f"sigma_xxx_{route}_{phase}_A_per_V2"] -
                                                  table[f"sigma_xxx_eq21_{phase}_A_per_V2"])))
                             for phase in ("polar", "reversed")) / scale
                   for route in ("tb", "analytic")}
    panels = []
    for index, (route, title) in enumerate((("tb", "Real-space TB"), ("analytic", "Analytic input"))):
        panels.append({
            "kind": "line", "label": "(a)" if index == 0 else "(b)", "title": title,
            "xlabel": r"$\hbar\omega\ (\mathrm{eV})$",
            "ylabel": r"$\mathrm{Re}\,\sigma^{xxx}\ (\mu\mathrm{A}\,\mathrm{V}^{-2})$",
            "xlim": [0, 4], "ylim": [-60, 60], "xticks": [0, 1, 2, 3, 4],
            "yticks": [-60, -40, -20, 0, 20, 40, 60],
            "yticklabels": [r"\textnormal{-60}", r"\textnormal{-40}", r"\textnormal{-20}", "0", "20", "40", "60"],
            "guide_y": [0], "guide_style": {"color": "#888888", "linewidth": 0.6},
            "legend": True, "legend_loc": "upper center", "legend_bbox_to_anchor": [0.5, -0.17],
            "legend_ncol": 2, "legend_fontsize": 11, "legend_frame": True,
            "legend_edgecolor": "#808080", "legend_facecolor": "white", "legend_framealpha": 0.9,
            "legend_linewidth": 0.8,
            "series": [
                {"data": "rice_mele_shift_current.display.dat", "x_column": 0, "y_column": 1 + 2 * index,
                 "scale": 1e6, "color": COLORS["polar"], "linestyle": "-", "linewidth": 1.6, "label": "polar: calculated"},
                {"data": "rice_mele_shift_current.display.dat", "x_column": 0, "y_column": 2 + 2 * index,
                 "scale": 1e6, "color": COLORS["reversed"], "linestyle": "-", "linewidth": 1.6, "label": "reversed: calculated"},
                {"data": "rice_mele_shift_current.markers.dat", "x_column": 0, "y_column": 1,
                 "scale": 1e6, "color": "#FF7F24", "linestyle": "None", "linewidth": 0, "marker": "o", "markersize": 4.2,
                 "label": "polar: analytic integral"},
                {"data": "rice_mele_shift_current.markers.dat", "x_column": 0, "y_column": 2,
                 "scale": 1e6, "color": "#3CB371", "linestyle": "None", "linewidth": 0, "marker": "D", "markersize": 4.2,
                 "label": "reversed: analytic integral"},
            ],
        })
    manifest = {"output": {"stem": "rice_mele_shift_current", "dpi": 600, "formats": ["png", "pdf"]},
                "figure": {"kind": "grid", "rows": 1, "cols": 2, "figsize": [12.0, 4.8], "panels": panels}}
    manifest_path = directory / "rice_mele_shift_current.plot.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    contract = {"source": "validation/shift_current_curves.tsv", "source_sha256": digest(DATA / "shift_current_curves.tsv"),
                "source_shape": [len(omega), 11], "selected_columns": fields, "original_ssh_ionic_retained": True,
                "reference_marker_source_row_indices": indices, "display_unit_scale": 1e6,
                "curve_offset": 0, "fitted_rescale": False, "full_401_sample_max_reference_difference_fraction": differences,
                "normalization": "maximum absolute real-space polar response", "scientific_recalculation": False}
    (directory / "rice_mele_shift_current.data-contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    tool = Path(figure_tool or os.environ.get("NLQG_FIGURE_TOOL", str(Path.home() / ".codex/skills/nlqg-plot-style/scripts/nlqg_figure.py")))
    if not tool.is_file():
        raise RuntimeError("Set --figure-tool or NLQG_FIGURE_TOOL to the installed nlqg_figure.py")
    subprocess.run([sys.executable, str(tool), "check-glyphs", "--manifest", str(manifest_path)], check=True)
    subprocess.run([sys.executable, str(tool), "render", str(manifest_path)], check=True)
    return [directory / f"rice_mele_shift_current.{suffix}" for suffix in ("png", "pdf")]


def convergence_plot():
    table = read_table(DATA / "convergence.tsv")
    omega = table["photon_eV"]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for mesh, color, line in ((401, "#606060", ":"), (801, "#104E8B", "-"),
                              (1601, "#FF7F24", "--")):
        ax.plot(omega, 1e6 * table[f"sigma_n{mesh}"], color=color, ls=line, lw=1.6,
                label=rf"$N_k={mesh}$")
    ax.set(xlabel=r"$\hbar\omega\ (\mathrm{eV})$",
           ylabel=r"$\sigma^{xxx}\ (\mu\mathrm{A}\,\mathrm{V}^{-2})$",
           xlim=(1.65, 2.45))
    ax.legend(frameon=True, facecolor="white", edgecolor="gray")
    style(ax)
    return finish(fig, "rice_mele_convergence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response-only", action="store_true", help="Render only the retained two-panel response; no other figure/data generation")
    parser.add_argument("--figure-tool", help="Path to installed nlqg_figure.py")
    parser.add_argument("--outdir", type=Path, help="Response-only output directory")
    args = parser.parse_args()
    check_environment()
    if args.response_only:
        response_plot(args.figure_tool, args.outdir)
        print("RICE_MELE_RESPONSE_FIGURE_OK presentation_only=true")
        return
    result = json.loads((DATA / "reference_spectrum.json").read_text())
    checked = json.loads((DATA / "reference.json").read_text())
    if result["profile"] != "reference" or checked["model_source_sha256"] != digest(ROOT.parents[1] / "models" / 'rice_mele/RiceMeleModel.jl'):
        raise RuntimeError("reference physics validation is absent or stale")
    inputs = [ROOT.parents[1] / "models" / 'rice_mele/RiceMeleModel.jl', DATA / "reference_spectrum.json",
              DATA / "shift_current_curves.tsv", DATA / "convergence.tsv", Path(__file__)]
    band_data, band_figures = bands_and_shift_vector()
    outputs = band_figures + response_plot(args.figure_tool) + convergence_plot()
    inputs.extend(band_data)
    manifest = {
        "schema": "rice-mele-figure-hashes-v1",
        "inputs_sha256": {os.path.relpath(path,ROOT): digest(path) for path in inputs},
        "outputs_sha256": {os.path.relpath(path,ROOT): digest(path) for path in outputs},
    }
    (FIGURES / "FIGURE_SHA256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("RICE_MELE_FIGURES_OK", ", ".join(path.name for path in outputs))


if __name__ == "__main__":
    main()
