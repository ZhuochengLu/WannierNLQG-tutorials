#!/usr/bin/env python3
"""Prepare an isolated Fe band-path input using a specific exported H/r bundle.

Use only an exported model whose source run and qualification have been checked.
The 801-point path and energy reference are copied unchanged from the supplied input.
"""
import argparse
from pathlib import Path
import json
import tomllib

parser = argparse.ArgumentParser()
parser.add_argument('--template', type=Path, required=True)
parser.add_argument('--bundle', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
bundle = args.bundle.resolve(strict=True)
if not bundle.is_file():
    parser.error('bundle must be an existing regular file')
if args.output.exists():
    parser.error('output already exists')
text = args.template.read_text()
needle = 'model_file = "../../../Materials/Fe/model_tb.dat"'
if text.count(needle) != 1:
    parser.error('template model identity or layout differs from expected')
text = text.replace(needle, 'real_space_operator_bundle_file = ' + json.dumps(str(bundle)))
parsed = tomllib.loads(text)
assert parsed['response']['sampling']['kpoints_per_segment'] == [201, 201, 201, 201]
assert parsed['response']['tasks']['fe_bands']['fermi_energy_ev'] == 5.7156290716733436
with args.output.open('x') as output:
    output.write(text)
