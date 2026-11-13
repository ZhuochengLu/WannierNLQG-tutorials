#!/usr/bin/env python3
"""Prepare a qualified-as-diagnostic Fe band comparison from a new band-path run."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bands', type=Path, required=True,
                        help='Fe_bands.dat from the new H/r bundle')
    parser.add_argument('--reference', type=Path, required=True,
                        help='DFT absolute-energy table whose same-path identity is independently established')
    parser.add_argument('--template', type=Path, required=True,
                        help='the chapter review comparison JSON')
    parser.add_argument('--output', type=Path, required=True,
                        help='new private output directory')
    args = parser.parse_args()
    bands, reference, template = (p.resolve(strict=True) for p in
                                  (args.bands, args.reference, args.template))
    text = bands.read_text()
    if '# energy_convention = ascending_eigenvalues_minus_E_ref' not in text:
        parser.error('unrecognized band-energy convention')
    energy_lines = [line for line in text.splitlines()
                    if line.startswith('# energy_reference_E_ref_eV =')]
    if len(energy_lines) != 1:
        parser.error('band output must declare exactly one energy reference')
    energy_ref = float(energy_lines[0].split('=', 1)[1])
    config = json.loads(template.read_text())
    declared_ref = float(config['comparison']['energy_reference']['value_ev'])
    if abs(energy_ref - declared_ref) > 1e-12:
        parser.error('band and comparison energy references differ')
    model = np.loadtxt(bands)
    dft = np.loadtxt(reference)
    if model.shape != (801, 22) or dft.shape != (801, 65):
        parser.error('expected 801 points, 18 Wannier bands and a 64-band DFT pool')
    if not np.isfinite(model).all() or not np.isfinite(dft).all():
        parser.error('nonfinite band values')
    nodes = np.array([[0,0,0], [.5,-.5,-.5], [.75,.25,-.25],
                      [.5,0,-.5], [0,0,0]], dtype=float)
    expected = np.concatenate([np.linspace(nodes[i], nodes[i+1], 201) if i == 0
                               else np.linspace(nodes[i], nodes[i+1], 201)[1:]
                               for i in range(4)])
    frac_error = float(np.max(np.abs(model[:, 1:4] - expected)))
    distance_error = float(np.max(np.abs(model[:, 0] - dft[:, 0])))
    if frac_error > 1e-12 or distance_error > 3e-7:
        parser.error('path points or cumulative distances differ from the declared reference')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    table = out / 'fe_new_absolute_aligned.dat'
    np.savetxt(table, np.column_stack((dft[:, 0], model[:, 4:] + energy_ref)),
               fmt='%.15e', header='Reference display distances; raw band distances retained in source. Absolute energies restored.')
    config['output']['stem'] = 'fe_new_band_review'
    config['comparison']['title'] = 'Fe electronic bands'
    config['comparison']['show_qualification_annotations'] = False
    config['comparison']['reference']['data'] = str(reference)
    m = config['comparison']['models'][0]
    m['data'] = str(table)
    m['label'] = 'Fe model'
    m['usable_for_bands'] = False
    m['qualification_label'] = 'Not qualified'
    manifest = out / 'comparison.json'
    manifest.write_text(json.dumps(config, indent=2) + '\n')
    evidence = {'raw_band_sha256': digest(bands), 'reference_sha256': digest(reference),
                'template_sha256': digest(template), 'aligned_table_sha256': digest(table),
                'energy_reference_ev': energy_ref, 'fractional_path_max_abs_error': frac_error,
                'display_distance_max_abs_difference_inverse_angstrom': distance_error,
                'display_distance_policy': 'After verifying the fractional path, use DFT distances for the shared display axis; preserve raw input distances.',
                'scientific_qualification': 'NOT_ESTABLISHED; the DFT table does not encode fractional coordinates, so verify its path identity independently; inspect solver and matching gates separately.'}
    (out / 'comparison_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(manifest)


if __name__ == '__main__':
    main()
