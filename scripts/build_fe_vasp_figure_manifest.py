#!/usr/bin/env python3
"""Build a reproducible first-principles Fe path-band figure manifest."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Materials/Fe/vasp_SOC/bands"
TABLE = DATA_DIR / "Fe_vasp_path_absolute.dat"
RECEIPT = DATA_DIR / "Fe_vasp_path_receipt.json"
EF = 5.7156290716733436

data = np.loadtxt(TABLE)
receipt = json.loads(RECEIPT.read_text())
assert data.shape == (801, 65)
assert receipt["scf_fermi_energy_ev"] == EF
ticks = [float(data[index, 0]) for index in (0, 200, 400, 600, 800)]
manifest = {
    "output": {
        "stem": "../../../../examples/11_fe_oam_and_linear_response/figures/Fe_vasp_path_bands",
        "dpi": 600,
        "formats": ["png", "pdf"],
    },
    "figure": {
        "kind": "line",
        "figsize": [6.4, 4.6],
        "title": "Fe SOC first-principles bands",
        "xlabel": "$k$-path distance ($\\mathrm{\\AA}^{-1}$)",
        "ylabel": "$E$ (eV)",
        "xlim": [ticks[0], ticks[-1]],
        "ylim": [EF - 8.0, EF + 8.0],
        "xticks": ticks,
        "xticklabels": ["\\textGamma", "\\textnormal{H}", "\\textnormal{P}", "\\textnormal{N}", "\\textGamma"],
        "guide_x": ticks,
        "guide_y": [EF],
        "legend": False,
        "series": [
            {
                "data": TABLE.name,
                "x_column": 0,
                "y_column": index,
                "color": "#606060",
                "linewidth": 0.65,
            }
            for index in range(1, 65)
        ],
    },
}
output = DATA_DIR / "Fe_vasp_bands.figure.json"
assert not output.exists(), "refusing to overwrite figure manifest"
output.write_text(json.dumps(manifest, indent=2) + "\n")
print("FE_VASP_FIGURE_MANIFEST_OK bands=64")
