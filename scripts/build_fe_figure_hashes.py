#!/usr/bin/env python3
"""Bind the new Fe figure set after visual and numerical review."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "examples/11_fe_oam_and_linear_response/figures"
STEMS = (
    "Fe_vasp_path_bands",
    "Fe_vasp_tb_path_comparison_bands",
    "Fe_vasp_tb_path_comparison_errors",
    "Fe_oam_40x40x40_integral",
    "Fe_linear_optical_xx_spectra",
    "Fe_linear_optical_xy_spectra",
    "Fe_linear_optical_decomposition_xx",
    "Fe_linear_optical_decomposition_xy",
    "berry_legacy_style_sos",
    "berry_legacy_style_transport_equivalent",
)

result = {}
for stem in STEMS:
    for extension in ("png", "pdf"):
        name = f"{stem}.{extension}"
        path = FIGURES / name
        assert path.is_file(), path
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
output = FIGURES / "FIGURE_SHA256.json"
output.write_text(json.dumps(result, indent=2) + "\n")
print(f"FE_FIGURE_HASHES_OK files={len(result)}")
