#!/usr/bin/env python3
"""Three-method shift-current overlay using the v1.0.1 visualization parser/style."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIS = Path(os.environ["WANNIERNLQG_VISUALIZATION_ROOT"])
sys.path.insert(0, str(VIS))
from visualization.response_parser import load_response, validate_response_comparison
from visualization.style import apply_margins, apply_style, resolve_style, style_axes
import matplotlib.pyplot as plt

chapter = ROOT / "examples/02_integral_charge_responses"
sources = [
    ("Conventional", chapter / "results/reference/integral_shift_current_conventional/GeS_sc_conv.dat", "#606060", "-"),
    ("Geometric Loop", chapter / "results/reference/integral_shift_current_geometric_loop/GeS_sc_geo.dat", "#104E8B", "--"),
    ("Wilson Loop", chapter / "results/reference/integral_shift_current_wilson_loop/GeS_sc_wilson.dat", "#FF7F24", "-."),
]
datasets = [load_response(path, label) for label, path, _, _ in sources]
for dataset in datasets[1:]:
    validate_response_comparison(datasets[0], dataset)
index = datasets[0].components.index("yyy")
style = resolve_style({"figsize": [6.4, 4.4], "dpi": 600})
apply_style(style)
figure, axis = plt.subplots(figsize=tuple(style["figsize"]))
for dataset, (_, _, color, linestyle) in zip(datasets, sources):
    axis.plot(dataset.omega_ev, dataset.values[:, index].real, label=dataset.label,
              color=color, linestyle=linestyle, linewidth=1.6)
axis.axhline(0.0, color="#777777", linewidth=0.7, linestyle="--")
axis.set_xlim(0.0, 4.0)
axis.set_xlabel(r"$\hbar\omega\ \mathrm{(eV)}$")
axis.set_ylabel(r"$\mathrm{Re}\,\sigma^{yyy}\ \mathrm{(native\ output\ units)}$")
axis.set_title(r"$\sigma^{yyy}$: supported methods")
axis.legend(frameon=False, ncols=3, loc="upper left")
style_axes(axis, style)
apply_margins(figure, style)
stem = chapter / "figures/GeS_shift_current_methods"
figure.savefig(stem.with_suffix(".pdf"), dpi=600, facecolor="white")
figure.savefig(stem.with_suffix(".png"), dpi=600, facecolor="white")
plt.close(figure)

def audited(path, role):
    return {"path": "./" + str(path.relative_to(ROOT)), "role": role,
            "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

sidecar = {
    "schema": "wanniernlqg.presentation-plot", "schema_version": "1.0",
    "qualification": "PRESENTATION_ONLY", "renderer": "v1.0.1 visualization parser/style",
    "datasets": [dataset.audit_record() for dataset in datasets],
    "inputs": [audited(path, "response_tensor") for _, path, _, _ in sources],
    "transform": {"component": "yyy", "part": "real", "interpolation": "none"},
    "outputs": [audited(stem.with_suffix(".pdf"), "plot_pdf"), audited(stem.with_suffix(".png"), "plot_png")],
}
(stem.parent / (stem.name + ".plot.json")).write_text(json.dumps(sidecar, indent=2) + "\n")
print("SHIFT_CURRENT_METHODS_PLOT_OK")
