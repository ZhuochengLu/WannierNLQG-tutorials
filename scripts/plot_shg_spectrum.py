#!/usr/bin/env python3
"""Render the GeS SHG total spectra from the native three-column output tables."""
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(config_path):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    source = (config_path.parent / config["input"]).resolve()
    stem = (config_path.parent / config["output_stem"]).resolve()
    table = np.loadtxt(source, comments="#", ndmin=2)
    if table.shape != (200, 3) or not np.isfinite(table).all():
        raise ValueError(f"expected a finite 200 x 3 SHG table: {source}")
    if not np.allclose(table[:, 0], np.linspace(0.0, 4.0, 200), rtol=0, atol=1e-12):
        raise ValueError(f"unexpected photon-energy grid: {source}")
    header = source.read_text().splitlines()[:3]
    if not any(f"units={config['unit']} component={config['component']}" in line for line in header):
        raise ValueError(f"wrong unit or component header: {source}")
    if "# energy_eV total_re total_im" not in header:
        raise ValueError(f"wrong SHG column header: {source}")

    mpl.rc("text", usetex=True)
    mpl.rc("font", family="serif")
    mpl.rc("font", serif=["Times New Roman"])
    mpl.rcParams["text.latex.preamble"] = r"\usepackage{newtxtext,newtxmath}\usepackage{bm}\usepackage{textgreek}"
    mpl.rcParams.update({"font.size": 12, "axes.labelsize": 14, "xtick.labelsize": 11,
                         "ytick.labelsize": 11, "legend.fontsize": 11, "axes.linewidth": 1.1})
    figure, axis = plt.subplots(figsize=(6.0, 4.0), facecolor="white")
    display_scale = float(config.get("display_scale", 1.0))
    axis.plot(table[:, 0], display_scale * table[:, 1], color="#104E8B", linewidth=1.6, label=r"$\mathrm{Re}$")
    axis.plot(table[:, 0], display_scale * table[:, 2], color="#FF7F24", linewidth=1.6, label=r"$\mathrm{Im}$")
    axis.set_xlabel(config["xlabel"])
    axis.set_ylabel(config["ylabel"])
    axis.set_xlim(config["xlim"])
    axis.tick_params(which="both", direction="in", top=True, right=True)
    axis.yaxis.set_major_formatter(FuncFormatter(
        lambda value, _: r"\textnormal{" + f"{value:g}" + "}"
    ))
    axis.minorticks_on()
    axis.legend(frameon=True, facecolor="white", edgecolor="#808080", framealpha=0.9)
    figure.tight_layout()
    stem.parent.mkdir(parents=True, exist_ok=True)
    png = stem.with_suffix(".png")
    pdf = stem.with_suffix(".pdf")
    figure.savefig(png, dpi=600, facecolor="white")
    figure.savefig(pdf, facecolor="white")
    plt.close(figure)
    summary = {
        "qualification": "PRESENTATION_ONLY",
        "config_sha256": sha256(config_path),
        "input_sha256": sha256(source),
        "png_sha256": sha256(png),
        "pdf_sha256": sha256(pdf),
        "rows": int(table.shape[0]),
        "unit": config["unit"],
        "display_scale": display_scale,
        "component": config["component"],
        "columns": ["energy_eV", "total_re", "total_im"],
    }
    stem.with_suffix(".plot.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"SHG_FIGURE_OK quantity={config['quantity']} png={png.name} pdf={pdf.name}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: plot_shg_spectrum.py CONFIG.json")
    render(sys.argv[1])
