#!/usr/bin/env python3
"""Stage only redistributable Fe inputs in an empty directory outside this repository."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATERIAL = ROOT / "Materials" / "Fe" / "vasp_SOC"
FILES = (
    "POSCAR", "INCAR", "KPOINTS", "POTCAR.txt",
    "Fe_ordinary_full_driver.jl", "run_vasp.sh",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    workdir = args.workdir.resolve()
    if workdir == ROOT or ROOT in workdir.parents:
        parser.error("workdir must be outside the tutorial repository")
    if workdir.exists():
        parser.error("workdir already exists; refusing to overwrite it")
    manifest = json.loads((MATERIAL / "DATA_MANIFEST.json").read_text())
    expected = {Path(entry["path"]).name: entry["sha256"] for entry in manifest["files"]}
    for name in FILES:
        if digest(MATERIAL / name) != expected[name]:
            parser.error(f"input identity mismatch: {name}")
    workdir.mkdir(parents=True)
    for name in FILES:
        shutil.copyfile(MATERIAL / name, workdir / name)
    (workdir / "run_vasp.sh").chmod(0o755)
    print(f"FE_REBUILD_STAGED workdir={workdir}")
    print("Supply your licensed POTCAR in this directory before running VASP.")


if __name__ == "__main__":
    main()
