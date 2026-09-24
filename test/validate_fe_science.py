#!/usr/bin/env python3
"""Validate the newly computed Fe reference tables and figure identities."""
import hashlib
import json
import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples/11_fe_oam_and_linear_response"
REF = CASE / "results/reference"
TERMS = ("drude", "quantum_metric", "berry_curvature")


def table(reference_root, task, name):
    path = reference_root / task / name
    value = np.loadtxt(path, comments="#")
    assert np.isfinite(value).all(), path
    return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, help="optional new numerical run root for live SHA-256 comparison")
    parser.add_argument("--reference-root", type=Path, default=REF,
                        help="staged or installed reference directory")
    args = parser.parse_args()
    reference_root = args.reference_root.resolve()
    if args.source_root:
        source = args.source_root.resolve()
        checked = 0
        for summary_path in reference_root.glob("*/summary.json"):
            summary = json.loads(summary_path.read_text())
            for name, provenance in summary["source_provenance"].items():
                expected = provenance["sha256"]
                if "source_relative" not in provenance:
                    assert digest(summary_path.parent / name) == expected
                    continue
                assert digest(source / provenance["source_relative"]) == expected
                assert digest(summary_path.parent / name) == expected
                checked += 1
        assert checked == 46, checked
        print(f"FE_SOURCE_RECEIPTS_OK files={checked}")
    export = json.loads((reference_root / "THREE_MECHANISM_VALIDATION.json").read_text())
    assert export["native_file_names"]
    assert export["optical_terms"] == ["drude", "quantum_metric", "berry_curvature", "total"]
    assert export["transport_terms"] == export["optical_terms"]
    expected_contract = ("THREE_MECHANISM_VALIDATED" if reference_root == REF.resolve()
                         else "THREE_MECHANISM_PENDING_VALIDATION")
    assert export["export_contract"] == expected_contract
    max_oam = max_transport = max_optical = max_zero = max_zero_terms = 0.0
    for method in ("conventional", "projector"):
        for temp in ("T000", "T300"):
            oam = f"oam_{method}_{temp}"
            parts = [table(reference_root, oam, f"orbital_magnetization_{term}.dat") for term in ("srocc", "cmocc")]
            total = table(reference_root, oam, "orbital_magnetization_total.dat")
            assert total.shape == (7,) and all(part.shape == (7,) for part in parts)
            assert all(np.isclose(part[0], 5.7156290716733436, atol=1e-12) for part in (*parts, total))
            max_oam = max(max_oam, float(np.max(np.abs(total[1:] - sum(part[1:] for part in parts)))))

            dc = f"linear_transport_{method}_{temp}"
            dc_parts = [table(reference_root, dc, f"linear_transport_{term}.dat") for term in TERMS]
            dc_total = table(reference_root, dc, "linear_transport_total.dat")
            assert dc_total.shape == (19,) and all(part.shape == (19,) for part in dc_parts)
            assert all(np.isclose(part[0], 5.7156290716733436, atol=1e-12) for part in (*dc_parts, dc_total))
            max_transport = max(max_transport, float(np.max(np.abs(dc_total[1:] - sum(part[1:] for part in dc_parts)))))

            optical = f"linear_optical_{method}_{temp}"
            optical_parts = [table(reference_root, optical, f"linear_optical_response_{term}.dat") for term in TERMS]
            optical_total = table(reference_root, optical, "linear_optical_response_total.dat")
            optical_summary = json.loads((reference_root / optical / "summary.json").read_text())
            assert optical_summary["optical_export_contract"] == "native_three_mechanism_filenames"
            assert optical_summary["source_tree_sha256"] == export["source_tree_sha256"]
            assert optical_total.shape == (401, 19)
            assert np.allclose(optical_total[:, 0], np.arange(401) * 0.02, atol=1e-12, rtol=0)
            max_optical = max(max_optical, float(np.max(np.abs(optical_total[:, 1:] - sum(part[:, 1:] for part in optical_parts)))))
            max_zero = max(max_zero, float(np.max(np.abs(optical_total[0, 1:] - dc_total[1:]))))
            for term, optical_part, dc_part in zip(TERMS, optical_parts, dc_parts):
                provenance = optical_summary["source_provenance"][f"linear_optical_response_{term}.dat"]
                assert Path(provenance["source_relative"]).name == f"linear_optical_response_{term}.dat"
                assert "raw_export_name" not in provenance
                max_zero_terms = max(max_zero_terms, float(np.max(np.abs(optical_part[0, 1:] - dc_part[1:]))))
    assert max_oam < 1e-12, max_oam
    assert max_transport < 1e-6, max_transport
    assert max_optical < 1e-6, max_optical
    assert max_zero < 1e-6, max_zero
    assert max_zero_terms < 1e-6, max_zero_terms

    sos = table(reference_root, "berry_sos_occupied_xy", "Fe_bck_sum_conv.dat")
    assert sos.shape == (200, 200)
    berry_task = "berry_transport_equivalent_xy"
    berry = table(reference_root, berry_task, "linear_transport_berry_curvature.dat")
    assert berry.shape == (40000, 5)
    assert np.allclose(berry[0, :3], 0, atol=1e-14)
    assert np.allclose(berry[1, :3], [-0.0025, 0.0025, 0.0025], atol=1e-14)
    c = (1.602176634e-19**2 / 1.054571817e-34) * 1e-20
    equivalent = (-berry[:, 3] / c).reshape(200, 200).T
    recorded = table(reference_root, berry_task, "berry_ky0_transport_equivalent.dat")
    assert recorded.shape == (200, 200)
    max_derived = float(np.max(np.abs(equivalent - recorded)))
    assert max_derived < 1e-8, max_derived
    difference = sos - recorded
    pearson = float(np.corrcoef(sos.ravel(), recorded.ravel())[0, 1])
    max_difference = float(np.max(np.abs(difference)))
    assert np.isfinite(pearson) and np.isfinite(max_difference)

    contract = json.loads((ROOT / "Materials/Fe/vasp_SOC/FE_BUNDLE_FILES.json").read_text())
    assert contract["release_status"] == "SEPARATE_RELEASE_ASSET"
    bands = ROOT / "Materials/Fe/vasp_SOC/bands"
    vasp = np.loadtxt(bands / "Fe_vasp_path_absolute.dat")
    tb_bands = np.loadtxt(bands / "Fe_tb_path_absolute.dat")
    assert vasp.shape == (801, 65) and tb_bands.shape == (801, 19)
    assert np.isfinite(vasp).all() and np.isfinite(tb_bands).all()
    assert np.array_equal(vasp[:, 0], tb_bands[:, 0]), "DFT/TB path coordinate differs"
    vasp_receipt = json.loads((bands / "Fe_vasp_path_receipt.json").read_text())
    tb_receipt = json.loads((bands / "Fe_tb_path_receipt.json").read_text())
    assert vasp_receipt["table_sha256"] == digest(bands / "Fe_vasp_path_absolute.dat")
    assert tb_receipt["table_sha256"] == digest(bands / "Fe_tb_path_absolute.dat")
    assert vasp_receipt["gamma_near_fermi_max_abs_ev"] < vasp_receipt["gamma_gate_threshold_ev"]
    assert vasp_receipt["scf_fermi_energy_ev"] == tb_receipt["scf_fermi_energy_ev"]
    assert tb_receipt["fractional_kpoint_max_abs_difference"] <= 5e-7
    assert tb_receipt["distance_max_abs_difference_A_inverse"] <= 5e-6
    if reference_root == REF.resolve():
        presentation = json.loads((CASE / "plot_configs/berry_legacy_style_contract.json").read_text())
        assert presentation["schema"] == "wanniernlqg.fe.berry-legacy-presentation.v2"
        for key, data_file, stem, limit in (
            ("sos", REF / "berry_sos_occupied_xy/Fe_bck_sum_conv.dat", "berry_legacy_style_sos", 10000),
            ("transport_equivalent", REF / "berry_transport_equivalent_xy/berry_ky0_transport_equivalent.dat",
             "berry_legacy_style_transport_equivalent", 10000),
        ):
            item = presentation["figures"][key]
            assert item["coordinate"] == "legacy_uncentered_periodic_cell"
            assert item["norm"] == "signed-log-exponent-with-linear-core"
            assert item["linthresh"] == 1.0 and item["fixed_symmetric_color_limit"] == limit
            assert item["clipped_negative_count"] >= 0 and item["clipped_positive_count"] >= 0
            assert item["data_sha256"] == digest(data_file)
            assert item["png_sha256"] == digest(CASE / "figures" / f"{stem}.png")
            assert item["pdf_sha256"] == digest(CASE / "figures" / f"{stem}.pdf")
        for key, data_file in (
            ("sos", REF / "berry_sos_occupied_xy/Fe_bck_sum_conv.dat"),
            ("transport_equivalent", REF / "berry_transport_equivalent_xy/berry_ky0_transport_equivalent.dat"),
        ):
            field = np.loadtxt(data_file)
            item = presentation["figures"][key]
            assert field.shape == (200, 200)
            assert item["clipped_negative_count"] == int(np.count_nonzero(field < -10000))
            assert item["clipped_positive_count"] == int(np.count_nonzero(field > 10000))
        expected_figures = json.loads((CASE / "figures/FIGURE_SHA256.json").read_text())
        assert set(expected_figures) >= {"berry_legacy_style_sos.png", "berry_legacy_style_transport_equivalent.png"}
        for name, expected in expected_figures.items():
            assert digest(CASE / "figures" / name) == expected
    print(json.dumps({
        "status": "FE_SCIENCE_OK",
        "tasks": 14,
        "oam_closure_muB_cell": max_oam,
        "transport_closure_S_per_m": max_transport,
        "optical_closure_S_per_m": max_optical,
        "optical_zero_vs_dc_S_per_m": max_zero,
        "optical_zero_vs_dc_by_term_S_per_m": max_zero_terms,
        "berry_derived_max_abs": max_derived,
        "berry_sos_vs_transport_max_abs": max_difference,
        "berry_pearson": pearson,
        "vasp_path_shape": [801, 64],
        "tb_path_shape": [801, 18],
        "qualification": "DIAGNOSTIC_ONLY",
    }, indent=2))


if __name__ == "__main__":
    main()
