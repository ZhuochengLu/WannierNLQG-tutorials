#!/usr/bin/env python3
"""Stage selected new Fe 1.1.0 outputs without retaining per-energy scratch files."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "oam": ("orbital_magnetization", ("srocc", "cmocc", "total")),
    "linear_transport": ("linear_transport", ("drude", "quantum_metric", "berry_curvature", "total")),
    "linear_optical": ("linear_optical_response", ("drude", "quantum_metric", "berry_curvature", "total")),
}
TASKS = [
    f"{family}_{method}_{temp}"
    for family in FAMILIES
    for method in ("conventional", "projector")
    for temp in ("T000", "T300")
] + ["berry_sos_occupied_xy", "berry_transport_equivalent_xy"]
def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def task_files(task):
    if task.startswith("berry_sos_"):
        return ["Fe_bck_sum_conv.dat"]
    if task.startswith("berry_transport_"):
        return ["linear_transport_berry_curvature.dat"]
    for family, (prefix, terms) in FAMILIES.items():
        if task.startswith(family + "_"):
            return [f"{prefix}_{term}.dat" for term in terms]
    raise ValueError(task)


def source_directory(root, task, names):
    matches = [path for path in (root / task).rglob(task) if path.is_dir() and
               all((path / name).is_file() for name in names)]
    assert len(matches) == 1, (task, matches)
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--tb", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--selected-model", type=Path, required=True)
    parser.add_argument("--source-tree-sha256", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--source-project", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    destination = args.destination.resolve()
    assert not destination.exists(), "refusing to overwrite staged Fe reference results"
    model = json.loads(args.selected_model.read_text())
    status = model["status"]
    assert status in ("CONVERGED", "MAX_ITERATIONS"), status
    assert digest(args.source_project / "SHA256SUMS") == args.source_manifest_sha256
    assert args.source_tree_sha256 != model["source_tree_sha256"], "response source must differ from model source"
    input_hashes = {"Fe_tb.dat": digest(args.tb), "Fe_fixed_full.h5": digest(args.bundle)}
    destination.mkdir(parents=True)
    for task in TASKS:
        names = task_files(task)
        source_dir = source_directory(source, task, names)
        target = destination / task
        target.mkdir()
        provenance = {}
        for name in names:
            source_file = source_dir / name
            with source_file.open("rb") as stream:
                header = stream.read(4096).decode("utf-8", errors="ignore")
            if header.startswith("# schema="):
                assert f"# release_tree_sha256={args.source_tree_sha256}" in header, source_file
                assert f"# model_sha256={input_hashes['Fe_fixed_full.h5']}" in header, source_file
            assert np.isfinite(np.loadtxt(source_file, comments="#")).all(), source_file
            shutil.copyfile(source_file, target / name)
            provenance[name] = {
                "source_relative": str(source_file.relative_to(source)),
                "sha256": digest(source_file),
            }
        if task == "berry_transport_equivalent_xy":
            berry = np.loadtxt(target / "linear_transport_berry_curvature.dat", comments="#")
            assert berry.shape == (40000, 5)
            coefficient = (1.602176634e-19**2 / 1.054571817e-34) * 1e-20
            field = (-berry[:, 3] / coefficient).reshape(200, 200).T
            name = "berry_ky0_transport_equivalent.dat"
            np.savetxt(target / name, field, fmt="%.14e")
            names.append(name)
            provenance[name] = {
                "derivation": "-berry_curvature/C; reshape(v,u).T",
                "sha256": digest(target / name),
            }
        family = next((name for name in FAMILIES if task.startswith(name + "_")), "berry")
        summary = {
            "task_id": task,
            "package_version": "1.1.0",
            "package_commit": None,
            "source_manifest_sha256": args.source_manifest_sha256,
            "source_tree_sha256": args.source_tree_sha256,
            "profile": "reference",
            "reference_reused": False,
            "mesh": [200, 200] if task.startswith("berry_") else [40, 40, 40],
            "fermi_energy_ev": 5.7156290716733436,
            "temperature_k": 300 if task.endswith("T300") else 0,
            "method": "projector" if "_projector_" in task else "conventional",
            "family": family,
            "input_sha256": input_hashes,
            "output_files": names,
            "output_sha256": {name: digest(target / name) for name in names},
            "source_provenance": provenance,
            "finite_values": True,
            "qualification": "DIAGNOSTIC_ONLY",
            "physics_status": "HOLD",
            "production_eligible": False,
            "wannierization_status": status,
        }
        if task.startswith("linear_optical_"):
            summary["optical_export_contract"] = "native_three_mechanism_filenames"
        (target / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (destination / "THREE_MECHANISM_VALIDATION.json").write_text(json.dumps({
        "schema": "wanniernlqg-tutorials.fe-three-mechanism-validation",
        "source_tree_sha256": args.source_tree_sha256,
        "source_manifest_sha256": args.source_manifest_sha256,
        "model_source_tree_sha256": model["source_tree_sha256"],
        "optical_terms": ["drude", "quantum_metric", "berry_curvature", "total"],
        "transport_terms": ["drude", "quantum_metric", "berry_curvature", "total"],
        "native_file_names": True,
        "qualification": "DIAGNOSTIC_ONLY",
        "export_contract": "THREE_MECHANISM_PENDING_VALIDATION",
    }, indent=2) + "\n")
    print(f"FE_RERUN_STAGE_OK tasks={len(TASKS)} tb={input_hashes['Fe_tb.dat']} bundle={input_hashes['Fe_fixed_full.h5']}")


if __name__ == "__main__":
    main()
