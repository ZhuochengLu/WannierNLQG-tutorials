#!/usr/bin/env python3
"""Audit saved one-to-one Fe band matches; never modify the matching or its gate."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def clusters(values, tolerance):
    ordered = np.sort(values)
    if not ordered.size:
        return []
    boundaries = np.r_[0, np.flatnonzero(np.diff(ordered) > tolerance) + 1, len(ordered)]
    return np.diff(boundaries).tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matches', type=Path, default=Path(__file__).resolve().parents[1] / 'data/native_fe_diagnostic_matches.npz')
    args = parser.parse_args()
    with np.load(args.matches) as data:
        reference = data['new_tb__matched_reference_energies_ev']
        model = data['new_tb__model_energies_ev']
        if reference.shape != (801, 18) or model.shape != reference.shape:
            raise ValueError('Expected 801 k points and 18 matched bands')
        if not (np.isfinite(reference).all() and np.isfinite(model).all()):
            raise ValueError('Nonfinite matched energies')
        mask = (reference >= -1.0) & (reference <= 1.0)
        full = [i for i in range(801) if clusters(reference[i], 0.01) != clusters(model[i], 0.01)]
        window = [i for i in range(801) if clusters(reference[i][mask[i]], 0.01) != clusters(model[i][mask[i]], 0.01)]
        errors = (model - reference)[mask]
        result = {'matches_sha256': hashlib.sha256(args.matches.read_bytes()).hexdigest(),
                  'adjacent_gap_tolerance_ev': 0.01, 'full_18_band_conflict_count': len(full),
                  'full_18_band_conflicts_zero_based': full, 'window_reference_energy_ev': [-1.0, 1.0],
                  'window_conflict_count': len(window), 'window_conflicts_zero_based': window,
                  'window_matched_pair_count': int(errors.size),
                  'window_rms_ev': float(np.sqrt(np.mean(errors**2))),
                  'window_max_abs_ev': float(np.max(np.abs(errors))),
                  'scope': 'Energy-set diagnostic only; the full-band gate is not replaced or upgraded.'}
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
