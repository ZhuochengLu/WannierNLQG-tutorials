#!/usr/bin/env python3
"""Hash the positive, public Fe input inventory; do not include licensed outputs."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [
    "Materials/Fe/vasp_SOC/POSCAR",
    "Materials/Fe/vasp_SOC/INCAR",
    "Materials/Fe/vasp_SOC/KPOINTS",
    "Materials/Fe/vasp_SOC/POTCAR.txt",
    "Materials/Fe/vasp_SOC/Fe_ordinary_full_driver.jl",
    "Materials/Fe/vasp_SOC/run_vasp.sh",
    "Materials/Fe/vasp_SOC/Fe_tb.dat",
    "Materials/Fe/vasp_SOC/MODEL_STATUS.json",
    "Materials/Fe/vasp_SOC/bands/INCAR_path_lmaxmix4",
    "Materials/Fe/vasp_SOC/bands/KPOINTS_path_lmaxmix4",
    "Materials/Fe/vasp_SOC/bands/Fe_vasp_path_absolute.dat",
    "Materials/Fe/vasp_SOC/bands/Fe_vasp_path_receipt.json",
    "Materials/Fe/vasp_SOC/bands/Fe_tb_path_absolute.dat",
    "Materials/Fe/vasp_SOC/bands/Fe_tb_path_receipt.json",
]
records = []
for relative in files:
    path = root / relative
    records.append({
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
manifest = {
    "schema": "wanniernlqg-tutorials.fe-data",
    "schema_version": "1.0",
    "model_status": json.loads((root / "Materials/Fe/vasp_SOC/MODEL_STATUS.json").read_text())["status"],
    "qualification": "DIAGNOSTIC_ONLY",
    "source_frozen_vasp_inputs": {
        "POSCAR": "0706c1b1c7630dc2f92e886e49ef07c124c00748051f17e85de513e30d286071",
        "INCAR": "a9580130eb190236880990d06a273ad9d702e92b6615b907908fd68512dde84f",
        "KPOINTS": "66d57bd04d37f858dff87938ff011af8ba58d86df48e9c277638f5366f27b00c",
        "POTCAR_NOT_DISTRIBUTED": "cd5a22d9368cc8b5cc476bea79732366149640da08ac9009b0e1b7fc627eea28",
    },
    "files": records,
    "forbidden": ["POTCAR", "WAVECAR", "OUTCAR", "CHGCAR", "*.amn", "*.mmn", "*.eig", "*.chk"],
}
out = root / "Materials/Fe/vasp_SOC/DATA_MANIFEST.json"
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"FE_DATA_MANIFEST_OK files={len(records)}")
