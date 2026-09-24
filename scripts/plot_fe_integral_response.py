#!/usr/bin/env python3
"""Render the new Fe integral and optical tables; never infer material qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHAPTER = ROOT / "examples/11_fe_oam_and_linear_response"
COLORS = {"conventional": "#164a70", "projector": "#b64a32"}
STYLES = {"T000": "-", "T300": "--"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(reference: Path, task: str, file: str) -> np.ndarray:
    path = reference / task / file
    value = np.loadtxt(path, comments="#")
    if not np.isfinite(value).all():
        raise ValueError(f"Non-finite Fe data: {path}")
    return value


def style() -> None:
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman"],
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage{newtxtext,newtxmath,bm,textgreek}",
        "font.size": 10, "axes.labelsize": 11, "axes.titlesize": 11,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 8,
        "axes.linewidth": 0.8, "savefig.facecolor": "white",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
    })


def signed_ticks(value: float, _position: int) -> str:
    if abs(value) < 1e-12:
        return r"$0$"
    number = f"{value:.0f}" if abs(value) >= 100 else f"{value:.3f}"
    if number.startswith("-"):
        return rf"\textnormal{{-{number[1:]}}}"
    return rf"${number}$"


def save(fig, out: Path, stem: str, inputs: list[Path]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig.text(0.99, 0.99, "DIAGNOSTIC ONLY", ha="right", va="top",
             fontsize=7, color="0.38")
    png = out / f"{stem}.png"
    pdf = out / f"{stem}.pdf"
    summary = out / f"{stem}.summary.json"
    fig.savefig(png, dpi=600, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    summary.write_text(json.dumps({
        "schema": "wanniernlqg-tutorials.fe-figure",
        "schema_version": "1.0",
        "qualification": "DIAGNOSTIC_ONLY",
        "physics_status": "HOLD",
        "production_eligible": False,
        "inputs_sha256": {str(p.relative_to(ROOT)): digest(p) for p in inputs},
        "png_sha256": digest(png),
        "pdf_sha256": digest(pdf),
    }, indent=2) + "\n")
    print(f"FE_FIGURE_OK {stem}")


def plot_oam(reference: Path, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.5), layout="constrained")
    labels = [r"$M_x$", r"$M_y$", r"$M_z$"]
    x = np.arange(3)
    inputs = []
    for method in COLORS:
        for temp in STYLES:
            task = f"oam_{method}_{temp}"
            file = reference / task / "orbital_magnetization_total.dat"
            inputs.append(file)
            values = read(reference, task, file.name)
            if values.shape != (7,) or not np.isclose(values[0], 5.7156290716733436, atol=1e-12):
                raise ValueError(f"Wrong OAM vector schema: {file}: {values.shape}")
            ax.plot(x, values[1::2], marker="o" if temp == "T000" else "s",
                    markersize=4, lw=1.35, color=COLORS[method], ls=STYLES[temp],
                    label=f"{method.capitalize()}, {0 if temp == 'T000' else 300} K")
    ax.axhline(0, color="0.65", lw=0.7)
    ax.set_xticks(x, labels)
    ax.set_ylabel(r"Orbital magnetization ($\mu_{\mathrm B}$/cell)")
    ax.yaxis.set_major_formatter(FuncFormatter(signed_ticks))
    ax.set_title(r"Fe SOC: integrated orbital magnetization")
    ax.legend(frameon=False, ncol=2)
    save(fig, out, "Fe_oam_40x40x40_integral", inputs)


def plot_optical_total(reference: Path, out: Path, component: str, index: int) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.5), layout="constrained")
    inputs = []
    for method in COLORS:
        for temp in STYLES:
            task = f"linear_optical_{method}_{temp}"
            file = reference / task / "linear_optical_response_total.dat"
            inputs.append(file)
            data = read(reference, task, file.name)
            if data.shape != (401, 19):
                raise ValueError(f"Wrong optical shape: {file}: {data.shape}")
            ax.plot(data[:, 0], data[:, index], color=COLORS[method], ls=STYLES[temp],
                    lw=1.25, label=f"{method.capitalize()}, {0 if temp == 'T000' else 300} K")
    ax.axhline(0, color="0.7", lw=0.7)
    ax.set_xlim(0, 8)
    ax.set_xlabel(r"Photon energy (eV)")
    ax.set_ylabel(rf"$\mathrm{{Re}}\,\sigma_{{{component}}}$ (S/m)")
    if component == "xy":
        ax.yaxis.set_major_formatter(FuncFormatter(signed_ticks))
    ax.set_title(rf"Fe SOC: linear optical $\sigma_{{{component}}}$")
    ax.legend(frameon=False, ncol=2)
    save(fig, out, f"Fe_linear_optical_{component}_spectra", inputs)


def plot_optical_terms(reference: Path, out: Path, component: str, index: int) -> None:
    task = "linear_optical_conventional_T000"
    terms = ("drude", "quantum_metric", "berry_curvature", "total")
    colors = ("#4e79a7", "#59a14f", "#b07aa1", "#222222")
    fig, ax = plt.subplots(figsize=(6.4, 3.5), layout="constrained")
    inputs = []
    for term, color in zip(terms, colors):
        file = reference / task / f"linear_optical_response_{term}.dat"
        inputs.append(file)
        data = read(reference, task, file.name)
        ax.plot(data[:, 0], data[:, index], color=color, lw=1.5 if term == "total" else 1.0,
                label=term.replace("_", " "))
    ax.axhline(0, color="0.7", lw=0.7)
    ax.set_xlim(0, 8)
    ax.set_xlabel(r"Photon energy (eV)")
    ax.set_ylabel(rf"$\mathrm{{Re}}\,\sigma_{{{component}}}$ (S/m)")
    if component == "xy":
        ax.yaxis.set_major_formatter(FuncFormatter(signed_ticks))
    ax.set_title(rf"Fe SOC: $\sigma_{{{component}}}$ terms, conventional, 0 K")
    ax.legend(frameon=False, ncol=2)
    save(fig, out, f"Fe_linear_optical_decomposition_{component}", inputs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path,
                        default=CHAPTER / "results/reference")
    parser.add_argument("--output-dir", type=Path, default=CHAPTER / "figures")
    args = parser.parse_args()
    style()
    plot_oam(args.reference, args.output_dir)
    plot_optical_total(args.reference, args.output_dir, "xx", 1)
    plot_optical_total(args.reference, args.output_dir, "xy", 3)
    plot_optical_terms(args.reference, args.output_dir, "xx", 1)
    plot_optical_terms(args.reference, args.output_dir, "xy", 3)


if __name__ == "__main__":
    main()
