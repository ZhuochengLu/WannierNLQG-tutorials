#!/usr/bin/env python3
"""Shared-scale method grids using v1.0.1 visualization styling and transforms."""
import hashlib, json, os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VIS = Path(os.environ["WANNIERNLQG_VISUALIZATION_ROOT"])
sys.path.insert(0, str(VIS))
from visualization.style import apply_margins, apply_style, resolve_style, style_axes
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import TwoSlopeNorm

chapter = ROOT / "examples/08_shift_geometry"
groups = [
    ("GeS_shift_vector_methods", [
        ("Geometric Loop", chapter / "results/reference/kslice_shift_vector_geometric_loop/GeS_svk_r_geo.dat"),
        ("Wilson Loop", chapter / "results/reference/kslice_shift_vector_wilson_loop/GeS_svk_r_wilson.dat")]),
    ("GeS_qhc_methods", [
        ("Conventional", chapter / "results/reference/kslice_quantum_hermitian_connection_conventional/GeS_qhck_r_conv.dat"),
        ("Geometric Loop", chapter / "results/reference/kslice_quantum_hermitian_connection_geometric_loop/GeS_qhck_r_geo.dat"),
        ("Wilson Loop", chapter / "results/reference/kslice_quantum_hermitian_connection_wilson_loop/GeS_qhck_r_wilson.dat")])]

def audited(path, role):
    return {"path": "./" + str(path.relative_to(ROOT)), "role": role, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

for stem_name, sources in groups:
    matrices = [np.fft.fftshift(np.loadtxt(path)).T for _, path in sources]
    limit = float(np.percentile(np.abs(np.concatenate([m.ravel() for m in matrices])), 99.5))
    style = resolve_style({"figsize": [5.0, 4.2], "dpi": 600})
    apply_style(style)
    figure, axes = plt.subplots(1, len(sources), figsize=(5.0 * len(sources), 4.2), squeeze=False)
    for axis, matrix, (label, _) in zip(axes.flat, matrices, sources):
        image = axis.imshow(matrix, origin="lower", extent=[-0.5,0.5,-0.5,0.5], aspect="equal",
                            cmap="RdBu_r", norm=TwoSlopeNorm(vcenter=0.0, vmin=-limit, vmax=limit), interpolation="nearest")
        axis.set_title(label); axis.set_xlabel(r"$u$ along $\bm{v}_1$"); axis.set_ylabel(r"$v$ along $\bm{v}_2$")
        style_axes(axis, style)
        cax = make_axes_locatable(axis).append_axes("right", size="5%", pad=0.08)
        figure.colorbar(image, cax=cax).set_label("native output units")
    grid_style = dict(style); grid_style["figsize"] = [5.0 * len(sources), 4.2]
    apply_margins(figure, grid_style)
    stem = chapter / "figures" / stem_name
    figure.savefig(stem.with_suffix(".pdf"), dpi=600, facecolor="white")
    figure.savefig(stem.with_suffix(".png"), dpi=600, facecolor="white")
    plt.close(figure)
    sidecar = {"schema":"wanniernlqg.presentation-plot","schema_version":"1.0","qualification":"PRESENTATION_ONLY",
        "renderer":"v1.0.1 visualization style","inputs":[audited(path,"kslice_matrix") for _,path in sources],
        "transform":{"operations":["fftshift","transpose"],"part":"real","percentile":99.5,"shared_vmin":-limit,"shared_vmax":limit,"interpolation":"none"},
        "outputs":[audited(stem.with_suffix(".pdf"),"plot_pdf"),audited(stem.with_suffix(".png"),"plot_png")]}
    (stem.parent/(stem.name+".plot.json")).write_text(json.dumps(sidecar,indent=2)+"\n")
print("GEOMETRY_METHOD_COMPARISONS_OK")
