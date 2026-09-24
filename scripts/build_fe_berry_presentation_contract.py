#!/usr/bin/env python3
"""Bind freshly rendered Fe Berry images to fixed legacy-style display limits."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTER = ROOT / "examples/11_fe_oam_and_linear_response"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(path):
    return dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sos-summary", type=Path, required=True)
    parser.add_argument("--transport-summary", type=Path, required=True)
    args = parser.parse_args()
    definitions = (
        ("sos", args.sos_summary, "berry_sos_occupied_xy/Fe_bck_sum_conv.dat", 10000),
        ("transport_equivalent", args.transport_summary,
         "berry_transport_equivalent_xy/berry_ky0_transport_equivalent.dat", 10000),
    )
    figures = {}
    for kind, path, data_name, limit in definitions:
        data = CHAPTER / "results/reference" / data_name
        image_stem = "berry_legacy_style_" + ("sos" if kind == "sos" else "transport_equivalent")
        png = CHAPTER / "figures" / f"{image_stem}.png"
        pdf = CHAPTER / "figures" / f"{image_stem}.pdf"
        values = summary(path)
        assert values["shape"] == "(200, 200)"
        assert float(values["linthresh"]) == 1.0
        assert float(values["negative_limit"]) == limit
        assert float(values["positive_limit"]) == limit
        assert float(values["fixed_color_limit"]) == limit
        figures[kind] = {
            "data_sha256": digest(data),
            "png_sha256": digest(png),
            "pdf_sha256": digest(pdf),
            "shape": [200, 200],
            "coordinate": "legacy_uncentered_periodic_cell",
            "corner_labels": ["H(001)", "Gamma(101)", "Gamma(000)", "H(100)"],
            "norm": "signed-log-exponent-with-linear-core",
            "linthresh": 1.0,
            "zero_color": "green",
            "fixed_symmetric_color_limit": limit,
            "clipped_negative_count": int(values["clipped_negative_count"]),
            "clipped_positive_count": int(values["clipped_positive_count"]),
            "raw_min": float(values["raw_min"]),
            "raw_max": float(values["raw_max"]),
            "contour_fermi_energy_ev": float(values["Efermi"]),
        }
    result = {
        "schema": "wanniernlqg.fe.berry-legacy-presentation.v2",
        "status": "PASS",
        "presentation_only": True,
        "qualification": "DIAGNOSTIC_ONLY",
        "figures": figures,
    }
    output = CHAPTER / "plot_configs/berry_legacy_style_contract.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("FE_BERRY_PRESENTATION_OK two_new_paths")


if __name__ == "__main__":
    main()
