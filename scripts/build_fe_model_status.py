#!/usr/bin/env python3
"""Publish only portable identity/status fields from a validated Fe rerun."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Materials/Fe/vasp_SOC/MODEL_STATUS.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-model", type=Path, required=True)
    parser.add_argument("--readback", type=Path, required=True)
    parser.add_argument("--tb", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source-tree-sha256", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    args = parser.parse_args()
    selected = json.loads(args.selected_model.read_text())
    readback = json.loads(args.readback.read_text())
    assert selected["status"] in ("CONVERGED", "MAX_ITERATIONS")
    assert readback["status"] == "PASS"
    assert readback["orbitals"] == 18 and readback["operator_count"] == 11
    assert selected["operator_target_contract_sha256"] == readback["target_contract_sha256"]
    artifacts = selected["artifacts"]
    assert digest(args.tb) == artifacts["wannier90_tb"]["sha256"]
    assert digest(args.bundle) == artifacts["packed_hdf5"]["sha256"]
    assert digest(args.tb) == readback["wannier90_tb"]["sha256"]
    assert digest(args.bundle) == readback["packed_hdf5"]["sha256"]
    assert not OUTPUT.exists(), "refusing to overwrite an existing Fe model identity"
    result = {
        "schema": "wanniernlqg-tutorials.fe-model-status",
        "schema_version": "1.0",
        "package_version": "1.1.0",
        "source_tree_sha256": args.source_tree_sha256,
        "source_manifest_sha256": args.source_manifest_sha256,
        "status": selected["status"],
        "selected_attempt": selected["selected_attempt"],
        "readback_status": readback["status"],
        "orbitals": 18,
        "full_operator_count": 11,
        "target_contract_sha256": selected["operator_target_contract_sha256"],
        "tb_sha256": digest(args.tb),
        "bundle_sha256": digest(args.bundle),
        "qualification": "DIAGNOSTIC_ONLY",
        "physics_status": "HOLD",
        "production_eligible": False,
        "vasp_recomputed": False,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"FE_MODEL_STATUS_OK status={result['status']} tb={result['tb_sha256']}")


if __name__ == "__main__":
    main()
