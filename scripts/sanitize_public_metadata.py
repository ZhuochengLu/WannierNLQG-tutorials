#!/usr/bin/env python3
"""Remove machine-local paths from native metadata and plot audit sidecars."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for path in ROOT.glob("examples/*/results/*/*/metadata.txt"):
    text = path.read_text()
    text = re.sub(r"(?m)^case_root\s*=.*$", "case_root                       = .", text)
    text = re.sub(r"(?m)^run_dir\s*=.*$", "run_dir                         = EPHEMERAL_RUN_DIRECTORY_OMITTED", text)
    text = re.sub(r"(?m)^output_root\s*=.*$", "output_root = EPHEMERAL_RUN_DIRECTORY_OMITTED", text)
    text = re.sub(r"(?m)^model_file\s*=\s*(?!\S*Materials/GeS/vasp_SOC/GeS_tb\.dat).*(?:Fe_fixed_full\.h5).*$", "model_file = EXTERNAL_INPUT_PATH_OMITTED", text)
    text = text.replace(str(ROOT), ".")
    text = re.sub(r"/var/folders/\S+", "EPHEMERAL_RUN_PATH_OMITTED", text)
    path.write_text(text)

def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    if not isinstance(value, str):
        return value
    root = str(ROOT)
    if value == root or value == root + "/":
        return "."
    if value.startswith(root + "/"):
        return "./" + value[len(root) + 1:]
    match = re.search(r"/\.julia/packages/WannierNLQG/[^/]+/(.*)$", value)
    if match:
        return "package://WannierNLQG@1.0.1/" + match.group(1)
    return value

for path in ROOT.glob("examples/*/figures/*.plot.json"):
    value = portable(json.loads(path.read_text()))
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

for path in ROOT.glob("examples/11_fe_oam_and_linear_response/figures/*.json"):
    value = portable(json.loads(path.read_text()))
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

print("PUBLIC_METADATA_SANITIZED")
