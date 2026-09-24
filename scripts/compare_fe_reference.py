#!/usr/bin/env python3
"""Report shape-aligned old/new Fe differences without treating parity as a gate."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / "examples/11_fe_oam_and_linear_response/results/reference"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-reference", type=Path, required=True)
    parser.add_argument("--new-reference", type=Path, default=NEW)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "manifests/fe_old_new_comparison.json")
    args = parser.parse_args()
    old = args.old_reference.resolve()
    new = args.new_reference.resolve()
    report = {"schema": "wanniernlqg-tutorials.fe-old-new-comparison", "qualification": "DIAGNOSTIC_ONLY", "tasks": {}}
    export = json.loads((new / "THREE_MECHANISM_VALIDATION.json").read_text())
    assert export["native_file_names"]
    report["optical_export_contract"] = "native_three_mechanism_filenames"
    report["comparison_note"] = "Fe model remains Physics HOLD; numerical closeness or differences are not a material qualification gate. Berry-curvature response is the anomalous-Hall mechanism and combines historical contact and interband Hall terms."
    for new_summary_path in sorted(new.glob("*/summary.json")):
        task = new_summary_path.parent.name
        old_summary_path = old / task / "summary.json"
        assert old_summary_path.is_file(), task
        new_summary = json.loads(new_summary_path.read_text())
        old_summary = json.loads(old_summary_path.read_text())
        assert new_summary["task_id"] == old_summary["task_id"] == task
        files = {}
        for name in sorted(set(old_summary["output_files"]) & set(new_summary["output_files"])):
            if not name.endswith(".dat"):
                continue
            previous = np.loadtxt(old_summary_path.parent / name, comments="#")
            current = np.loadtxt(new_summary_path.parent / name, comments="#")
            item = {
                "old_sha256": digest(old_summary_path.parent / name),
                "new_sha256": digest(new_summary_path.parent / name),
                "old_shape": list(previous.shape),
                "new_shape": list(current.shape),
            }
            comparable = current
            if previous.ndim == current.ndim and previous.shape[:-1] == current.shape[:-1] and current.shape[-1] == previous.shape[-1] + 1 and task.startswith(("oam_", "linear_transport_")):
                comparable = current[..., 1:]
                item["schema_alignment"] = "new leading mu_eV column omitted; physical columns compared"
                item["new_mu_eV"] = float(np.ravel(current[..., 0])[0])
            if previous.shape == comparable.shape:
                delta = comparable - previous
                scale = np.maximum(np.abs(previous), 1.0)
                item.update({
                    "max_abs": float(np.max(np.abs(delta))),
                    "max_relative_to_max_1": float(np.max(np.abs(delta) / scale)),
                    "rms": float(np.sqrt(np.mean(delta**2))),
                    "nonfinite_count": int(np.size(comparable) - np.isfinite(comparable).sum()),
                })
            else:
                item["comparison_status"] = "SHAPE_MISMATCH_NOT_NUMERICALLY_COMPARED"
            files[name] = item
        for family, prefix in (("linear_transport_", "linear_transport_"),
                               ("linear_optical_", "linear_optical_response_")):
            if task.startswith(family) or (task == "berry_transport_equivalent_xy" and family == "linear_transport_"):
                metric_old = old_summary_path.parent / f"{prefix}metric.dat"
                metric_new = new_summary_path.parent / f"{prefix}quantum_metric.dat"
                hall_old = old_summary_path.parent / f"{prefix}hall_interband.dat"
                contact_old = old_summary_path.parent / f"{prefix}contact.dat"
                berry_new = new_summary_path.parent / f"{prefix}berry_curvature.dat"
                if metric_old.is_file() and metric_new.is_file():
                    previous = np.loadtxt(metric_old, comments="#")
                    current = np.loadtxt(metric_new, comments="#")
                    files[metric_new.name] = {"old_sha256": digest(metric_old), "new_sha256": digest(metric_new),
                                              "max_abs": float(np.max(np.abs(current - previous)))}
                if hall_old.is_file() and contact_old.is_file() and berry_new.is_file():
                    hall = np.loadtxt(hall_old, comments="#")
                    contact = np.loadtxt(contact_old, comments="#")
                    current = np.loadtxt(berry_new, comments="#")
                    expected = hall.copy()
                    expected[..., 1:] += contact[..., 1:] if hall.shape[-1] == 19 else 0
                    if hall.shape[-1] == 5:
                        expected[..., 3:] += contact[..., 3:]
                    files[berry_new.name] = {"old_hall_sha256": digest(hall_old),
                                             "old_contact_sha256": digest(contact_old),
                                             "new_sha256": digest(berry_new),
                                             "max_abs": float(np.max(np.abs(current - expected)))}
        report["tasks"][task] = {
            "old_source_tree_sha256": old_summary.get("source_tree_sha256"),
            "new_source_tree_sha256": new_summary.get("source_tree_sha256"),
            "old_tb_sha256": old_summary["input_sha256"]["Fe_tb.dat"],
            "new_tb_sha256": new_summary["input_sha256"]["Fe_tb.dat"],
            "files": files,
        }
    assert len(report["tasks"]) == 14
    output = args.output.resolve()
    assert not output.exists() or output == (ROOT / "manifests/fe_old_new_comparison.json").resolve(), \
        "refusing to overwrite an existing staged comparison"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("FE_OLD_NEW_COMPARISON_OK tasks=14")


if __name__ == "__main__":
    main()
