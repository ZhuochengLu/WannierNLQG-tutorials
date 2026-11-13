#!/usr/bin/env python3
"""Independent single-cone polar integration and finite-region result validation.

No WannierNLQG kernel or eigenvector is imported. Radial integrals are analytic;
scipy.integrate.quad_vec performs only the remaining angle integral over a square.
All conductivities below are dimensionless in e^2/h; k is in inverse Angstrom.
"""
import cmath
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

import numpy as np
from scipy.integrate import quad_vec

ROOT = Path(__file__).resolve().parent
V = 2.0
QUANTUM = 1.602176634e-19 ** 2 / 6.62607015e-34
MAIN = ['hall_positive', 'optical_positive', 'hall_negative', 'optical_negative']
SCANS = [f'optical_positive_{tag}' for tag in ('n201','n801','k025','k050','k200','g001')] + [
 'hall_positive_k004','hall_positive_k016','hall_positive_k064','hall_positive_n9601',
 'hall_positive_g0001','hall_optical_matched']
DC_SOURCE = 'f77e56f31af0b781c2c97f30ce5351e135acb361e335cbf84356f3b264d8e6bf'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def energy(kx, ky, mass):
    return np.sqrt(mass * mass + V * V * (kx * kx + ky * ky))


def berry(kx, ky, mass):
    """Lower-band curvature for A=i<u|du>; upper band has the opposite sign."""
    return mass * V * V / (2 * energy(kx, ky, mass) ** 3)


def metric_xx(kx, ky, mass):
    e = energy(kx, ky, mass)
    return V * V / (4 * e * e) * (1 - V * V * kx * kx / (e * e))


def box_flux(cutoff, mass):
    """(1/2pi) integral Omega over [-K,K]^2; not a lattice Chern number."""
    return math.copysign(1, mass) / math.pi * math.atan(
        V * V * cutoff * cutoff / (abs(mass) * math.sqrt(mass * mass + 2 * V * V * cutoff * cutoff)))


def polar_response(axis, cutoff, mass, gamma, optical, tolerance):
    """C4 symmetry averages g_xx and g_yy. r dr = E dE/v^2.

    With D=2E, z=photon+i gamma, dimensionless integrands before polar
    integration are -2i D z g_xx/(D^2-z^2) and -Omega D^2/(D^2-z^2).
    The measure is d^2k/(2pi): (e^2/hbar)/(e^2/h)=2pi.
    """
    axis = np.asarray(axis)
    z = axis + 1j * gamma if optical else np.full(axis.shape, 1j * gamma)
    minimum = np.full(axis.shape, abs(mass)) if optical else np.maximum(abs(mass), np.abs(axis))

    def primitives(e):
        log = np.log((2 * e - z) / (2 * e + z))
        hall = -mass / (2 * z) * log
        xx = -1j / 8 * (1 + 4 * mass * mass / (z * z)) * log - 1j * mass * mass / (2 * z * e)
        return xx, hall

    low_xx, low_hall = primitives(minimum)

    def angular(theta):
        maximum = math.sqrt(mass * mass + V * V * (cutoff / math.cos(theta)) ** 2)
        high_xx, high_hall = primitives(maximum)
        mask = maximum > minimum
        return np.stack([np.where(mask, high_xx - low_xx, 0),
                         np.where(mask, high_hall - low_hall, 0)]) * (4 / math.pi)

    result, estimate = quad_vec(angular, 0, math.pi / 4, epsabs=tolerance, epsrel=tolerance)
    return result, float(estimate)


def clean_xx(axis, mass):
    axis = np.asarray(axis)
    result = np.zeros_like(axis)
    mask = axis > 2 * abs(mass) # theta(0)=0 for display; the threshold point is not a clean-limit test
    result[mask] = math.pi / 8 * (1 + 4 * mass * mass / axis[mask] ** 2)
    return result


def load_case(profile, name):
    folder = ROOT / 'results' / profile / name
    summary = json.loads((folder / 'summary.json').read_text())
    require(summary['package_version'] == '1.2.0' and summary['source_manifest_sha256'] == DC_SOURCE and summary['finite_values'], f'VERSION_OR_FINITE {name}')
    require(summary['periodic'] is False and summary['integration_dimension'] == 2,
            f'NONPERIODIC_SCOPE {name}')
    for path, digest in summary['input_sha256'].items():
        require(sha(ROOT / path) == digest, f'INPUT_HASH {name}/{path}')
    for path, digest in summary['output_sha256'].items():
        require(sha(folder / path) == digest, f'OUTPUT_HASH {name}/{path}')
    require(set(summary['shared_output_sha256']) == {'native_derivatives.tsv'}, f'DERIVATIVE_INVENTORY {name}')
    require(sha(folder/'native_derivatives.tsv') == summary['shared_output_sha256']['native_derivatives.tsv'],
            f'DERIVATIVE_HASH {name}')
    metadata = (folder / 'metadata.txt').read_text()
    for key, value in (('model_input_mode', 'analytic_k'), ('native_derivative_method', 'automatic'),
                       ('backend', 'direct')):
        require(re.search(r'^' + key + r'\s*=\s*' + value + r'$', metadata, re.M), f'ACTUAL_ROUTE {name}/{key}')
    require('Cartesian_region_integral' in (folder / 'spectral_response_metadata.txt').read_text(),
            f'ACTUAL_REGION {name}')
    derivatives = (folder / 'native_derivatives.tsv').read_text()
    expected_points = int(summary['mesh'][0]) * int(summary['mesh'][1])
    require(f'1\tFORWARDDIFF\t{expected_points}\tEVALUATED' in derivatives, f'ACTUAL_AD {name}')
    require(re.search(r'^native_periodic\s*=\s*false$', metadata, re.M) and
            re.search(r'^integration_dimension\s*=\s*2$', metadata, re.M), f'ACTUAL_NONPERIODIC {name}')
    reference = profile in ('reference','matched_optical_dc')
    settings = {
      'hall_positive':(32.,6401,.002), 'hall_negative':(32.,6401,.002),
      'hall_positive_g0001':(32.,6401,.001), 'hall_positive_k004':(4.,201,.002),
      'hall_positive_k016':(16.,801,.002), 'hall_positive_k064':(64.,3201,.002),
      'hall_positive_n9601':(32.,9601,.002), 'hall_optical_matched':(1.,401,.02),
      'optical_positive':(1.,401,.02), 'optical_negative':(1.,401,.02),
      'optical_positive_n201':(1.,201,.02), 'optical_positive_n801':(1.,801,.02),
      'optical_positive_k025':(.25,101,.02), 'optical_positive_k050':(.5,201,.02),
      'optical_positive_k200':(2.,801,.02), 'optical_positive_g001':(1.,801,.01),
    }
    if profile=='matched_optical_dc':expected=(1.,401,.02)
    else:
        require(name in settings,f'CASE_INVENTORY {name}')
        expected=settings[name] if reference else (1.,21,.002 if name.startswith('hall_') else .02)
    require((float(summary['cutoff_A_inverse']),summary['mesh'][0],summary['gamma_ev'])==expected and
        summary['mesh'][0]==summary['mesh'][1] and summary['mass_ev']==(-.2 if name.endswith('negative') else .2) and
        summary['velocity_ev_angstrom']==V and summary['eta_fs_ev']==.01, f'RESPONSE_SETTINGS {name}')
    require(re.search(r'^k_mesh\s*=\s*'+re.escape(f'({expected[1]}, {expected[1]})')+r'$',metadata,re.M),f'ACTUAL_MESH {name}')
    bounds=re.search(r'^native_evaluation_bounds_A_inverse\s*=\s*(.+)$',metadata,re.M)
    require(bounds is not None,f'EVALUATION_DOMAIN_MISSING {name}')
    import ast
    lower,upper=ast.literal_eval(bounds.group(1))
    require(all(lower[i]<-expected[0] and upper[i]>expected[0] for i in (0,1)) and lower[2]<0<upper[2],f'EVALUATION_DOMAIN {name}')
    family = summary['response_family']
    quantity = 'linear_transport' if family == 'hall' else 'linear_optical_response'
    expected = {f'{quantity}_{term}.dat' for term in ('drude', 'quantum_metric', 'berry_curvature', 'total')}
    require(set(summary['output_files']) == expected | {'spectral_response_metadata.txt'}, f'RESPONSE_FILE_LIST {name}')
    curves = {}
    reference = profile in ('reference','matched_optical_dc')
    expected_axis = np.asarray(summary.get('fermi_energies_ev', np.linspace(-0.8,0.8,161))) if reference and family == 'hall' else \
        (np.linspace(0,3,301) if reference else (np.array([-.4,0,.4]) if family=='hall' else np.linspace(0,3,16)))
    cutoff = float(summary['cutoff_A_inverse'])
    spectral = (folder/'spectral_response_metadata.txt').read_text()
    require(f'integration_bounds = (({-cutoff}, {-cutoff}, 0.0), ({cutoff}, {cutoff}, 0.0))' in spectral, f'ACTUAL_BOUNDS {name}')
    require('cell_volume_m3 = "NOT_APPLICABLE_CARTESIAN_REGION"' in spectral, f'NO_VACUUM_CONVERSION {name}')
    labels = [a+b for a in 'xyz' for b in 'xyz']
    for term in ('drude', 'quantum_metric', 'berry_curvature', 'total'):
        path = folder / f'{quantity}_{term}.dat'
        content = path.read_text()
        for rate in ('gamma_intra_ev','gamma_inter_ev'):
            actual = re.search(r'^'+rate+r'\s*=\s*"?([0-9.eE+\-]+)"?$', spectral, re.M)
            require(actual is not None and float(actual.group(1))==summary['gamma_ev'], f'ACTUAL_RATE {name}/{rate}')
            if family=='hall':require(f'# {rate}={summary["gamma_ev"]}' in content, f'ACTUAL_RATE_HEADER {name}/{rate}')
        require('# units=(S/m)*m^1' in content, f'SHEET_UNITS {name}/{term}')
        if family == 'hall':
            require('# schema=wanniernlqg.cartesian-region-spectral/1.0' in content, f'REGION_SCHEMA {name}')
        wanted = '# ' + ('mu_eV' if family == 'hall' else 'energy_eV') + ' ' + ' '.join(
            label + suffix for label in labels for suffix in ('_real', '_imag'))
        require(wanted in content, f'TENSOR_COLUMNS {name}/{term}')
        rows = np.loadtxt(path)
        require(rows.shape == (len(expected_axis), 19) and np.isfinite(rows).all(), f'TABLE_SHAPE {name}')
        require(np.max(np.abs(rows[:, 0] - expected_axis)) < 1e-12, f'AXIS {name}')
        tensor = (rows[:, 1::2] + 1j * rows[:, 2::2]).reshape(-1, 3, 3) / QUANTUM
        curves[term] = tensor
    require(np.max(np.abs(curves['total'] - curves['drude'] - curves['quantum_metric'] - curves['berry_curvature'])) < 1e-8,
            f'MECHANISM_SUM {name}')
    out_of_plane = np.concatenate([curves['total'][:, 2, :].ravel(), curves['total'][:, :, 2].ravel()])
    require(np.max(np.abs(out_of_plane)) < 1e-8, f'OUT_OF_PLANE {name}')
    require(np.max(np.abs(curves['total'][:, 0, 0] - curves['total'][:, 1, 1])) < 1e-8,
            f'SQUARE_ISOTROPY {name}')
    return expected_axis, curves, summary


def hall(curves):
    tensor = curves['berry_curvature']
    return (tensor[:, 0, 1] - tensor[:, 1, 0]) / 2


def write_tsv(path, columns, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(path, np.asarray(data), delimiter='\t', header='\t'.join(columns), comments='# ', fmt='%.16e')


def validate(profile, scope="all"):
    require(profile in ('smoke', 'reference'), 'BAD_PROFILE')
    require(scope in ('all','optical'), 'BAD_SCOPE')
    cases = MAIN + SCANS if profile == 'reference' else MAIN
    if scope=='optical': cases=[name for name in cases if name.startswith('optical_')]
    data, checks = {}, {'profile': profile, 'status': 'PENDING_VERIFICATION', 'cases': {},
                        'conductance_quantum_S': QUANTUM, 'band_gap_ev': 0.4,
                        'tolerances': {'finite_region': .01, 'mesh': .005, 'closed_form': .005,
                                       'symmetry_absolute_e2_over_h': 1e-8, 'reference_self': .001, 'half_integer_distance': .003}}
    failures = []
    scope_failures = {'dc_in_gap_platform': [], 'dc_full_axis_benchmark': [], 'dc_full_axis_mesh': [], 'complex_optical_spectrum': [], 'same_parameter_zero_frequency': []}
    for name in cases:
        axis, curves, summary = load_case(profile, name)
        data[name] = (axis, curves)
        optical = summary['response_family'] == 'optical'
        mass, cutoff, gamma = summary['mass_ev'], summary['cutoff_A_inverse'], summary['gamma_ev']
        reference, estimate = polar_response(axis, cutoff, mass, gamma, optical, 1e-9)
        fine, fine_estimate = polar_response(axis, cutoff, mass, gamma, optical, 1e-11)
        xx, gh = curves['total'][:, 0, 0], hall(curves)
        scale_h = max(np.max(np.abs(fine[1])), .5)
        scale_x = max(np.max(np.abs(fine[0])), math.pi / 8)
        self_error = float(np.max(np.abs(reference - fine)))
        require(max(self_error, fine_estimate) < .001 * min(scale_x, scale_h), f'INDEPENDENT_QUADRATURE {name}')
        error_h = float(np.max(np.abs(gh - fine[1])) / scale_h)
        error_x = float(np.max(np.abs(xx - fine[0])) / scale_x) if optical else None
        record = {'mass_ev': mass, 'cutoff_A_inverse': cutoff, 'mesh': summary['mesh'][0], 'gamma_ev': gamma,
                  'hall_max_absolute_e2_over_h': float(np.max(np.abs(gh - fine[1]))),
                  'hall_max_fraction': error_h, 'xx_complex_max_fraction': error_x,
                  'independent_coarse_fine_abs': self_error, 'independent_error_estimate_abs': fine_estimate,
                  'metadata_sha256': sha(ROOT/'results'/profile/name/'metadata.txt'),
                  'derivatives_sha256': sha(ROOT/'results'/profile/name/'native_derivatives.tsv')}
        if not optical:
            center = int(np.argmin(abs(axis)))
            target = -box_flux(cutoff, mass)
            record.update(hall_mu0_e2_over_h=float(gh[center].real), clean_box_target_e2_over_h=target,
                          closed_form_fraction=abs(gh[center].real - target) / abs(target))
            if profile == 'reference' and record['closed_form_fraction'] >= .005:
                failures.append(f'CLOSED_FORM {name}: {record["closed_form_fraction"]}')
        if not optical:
            in_gap = np.abs(axis) < abs(mass)-1e-12
            plateau_error = float(np.max(np.abs(gh[in_gap]-fine[1,in_gap]))/.5)
            record['in_gap_max_fraction_of_half'] = plateau_error
            record['in_gap_status'] = 'PASS' if profile=='reference' and plateau_error < .01 and record['closed_form_fraction'] < .005 else 'SMOKE_NOT_ACCURACY_QUALIFIED'
            if profile=='reference' and (plateau_error >= .01 or record['closed_form_fraction'] >= .005):
                scope_failures['dc_in_gap_platform'].append(name)
            if name in ('hall_positive','hall_negative') and profile=='reference':
                half_distance = abs(gh[center].real + math.copysign(.5,mass))/.5
                record['half_integer_distance_fraction'] = half_distance
                if half_distance >= .003:scope_failures['dc_in_gap_platform'].append('HALF_LIMIT '+name)
        if optical and profile=='reference' and (error_h>=.01 or error_x>=.01):
            scope_failures['complex_optical_spectrum'].append(name)
        if profile=='reference' and name in ('hall_positive','hall_negative') and error_h>=.01:
            scope_failures['dc_full_axis_benchmark'].append(name)
        record['full_axis_status'] = ('PASS' if error_h < .01 and (not optical or error_x < .01) else 'FAIL') if profile=='reference' else 'SMOKE_NOT_ACCURACY_QUALIFIED'
        if profile == 'reference':
            if error_h >= .01 or (optical and error_x >= .01):
                failures.append(f'FINITE_REGION {name}: hall={error_h}, xx={error_x}')
        checks['cases'][name] = record
        clean = clean_xx(axis, mass) if optical else np.zeros_like(axis)
        write_tsv(ROOT/'validation'/f'{profile}_{name}.tsv',
                  ['axis_eV', 'xx_real', 'xx_imag', 'hall_real', 'hall_imag',
                   'reference_xx_real', 'reference_xx_imag', 'reference_hall_real', 'reference_hall_imag', 'clean_xx_infinite'],
                  np.column_stack([axis, xx.real, xx.imag, gh.real, gh.imag,
                                   fine[0].real, fine[0].imag, fine[1].real, fine[1].imag, clean]))
    symmetry = {}
    for family in ('hall', 'optical'):
        if f'{family}_positive' not in data:continue
        plus, minus = data[f'{family}_positive'][1], data[f'{family}_negative'][1]
        symmetry[f'{family}_hall_odd'] = float(np.max(np.abs(hall(plus) + hall(minus))))
        symmetry[f'{family}_xx_even'] = float(np.max(np.abs(plus['total'][:, 0, 0] - minus['total'][:, 0, 0])))
    require(max(symmetry.values()) < 1e-8, f'MASS_REVERSAL {symmetry}')
    # Cross-family equality is meaningful only with equal K, mesh, mass and gamma.
    if profile=='reference':
        matched_axis, dc, matched_summary = load_case(profile,'hall_optical_matched')
        optical_axis, optical, optical_summary = load_case(profile,'optical_positive')
        for key in ('mass_ev','cutoff_A_inverse','mesh','gamma_ev','eta_fs_ev'):
            require(matched_summary[key] == optical_summary[key], f'ZERO_LIMIT_PARAMETER_MISMATCH {key}')
        center=int(np.argmin(abs(matched_axis)))
        zero_error=float(np.max(np.abs(dc['total'][center]-optical['total'][0])))
        require(zero_error<1e-8, f'MATCHED_OPTICAL_DC_LIMIT {zero_error}')
        checks['same_parameter_zero_frequency'] = {'status':'PASS','dc_case':'hall_optical_matched','optical_case':'optical_positive',
            'cutoff_A_inverse':1.,'mesh':401,'gamma_ev':.02,'maximum_absolute_e2_over_h':zero_error}
        checks['different_parameter_zero_frequency_comparison'] = 'NOT_APPLICABLE'
    else:
        checks['same_parameter_zero_frequency']={'status':'NOT_RUN_DIFFERENT_RELAXATION_SETTINGS'}
    checks['symmetry_absolute_e2_over_h']=symmetry
    # Independent primitive normalization checks against the closed flux and literature limit.
    clean_box, _ = polar_response([0.0], 1.0, .2, 1e-7, False, 1e-11)
    closed_error = abs(clean_box[1, 0].real + box_flux(1.0, .2))
    require(closed_error < 1e-9, f'POLAR_CLOSED_FORM_IDENTITY {closed_error}')
    clean_axis = np.array([.2, .3, .6, 1.0, 2.0])
    infinite, _ = polar_response(clean_axis, 1e4, .2, 1e-7, True, 1e-11)
    literature_error = float(np.max(np.abs(infinite[0].real - clean_xx(clean_axis, .2))))
    require(literature_error < 1e-5, f'SINGLE_CONE_OPTICAL_NORMALIZATION {literature_error}')
    checks.update(polar_closed_form_absolute=closed_error,
                  single_cone_literature_clean_limit_absolute=literature_error,
                  literature_test_energies_ev=clean_axis.tolist())
    if profile=='reference':
        primary=data['optical_positive'][1];fine=data['optical_positive_n801'][1]
        scale=max(float(np.max(abs(primary['total'][:,0,0]))),.5)
        optical_mesh=float(np.max(abs(primary['total'][:,0,0]-fine['total'][:,0,0]))/scale)
        bc_scale=max(float(np.max(abs(hall(primary)))),.5)
        optical_hall_mesh=float(np.max(abs(hall(primary)-hall(fine)))/bc_scale)
        checks['mesh_checks']={'optical_xx_401_801_fraction':optical_mesh,'optical_hall_401_801_fraction':optical_hall_mesh}
        if scope=='all':
            coarse_axis,coarse=data['hall_positive'];fine_axis,fine_dc=data['hall_positive_n9601']
            require(np.array_equal(coarse_axis,fine_axis),'DC_MESH_AXIS_MISMATCH')
            plateau_mesh=abs(hall(coarse)[np.argmin(abs(coarse_axis))]-hall(fine_dc)[np.argmin(abs(fine_axis))])/.5
            full_mesh=float(np.max(abs(hall(coarse)-hall(fine_dc)))/.5)
            checks['mesh_checks'].update(dc_plateau_6401_9601_fraction=float(plateau_mesh),
                dc_full_axis_6401_9601_fraction=full_mesh,dc_scan_scope='full chemical-potential axis; fixed K=32 and gamma=0.002',
                dc_full_axis_status='PASS' if full_mesh<.005 else 'FAIL')
            if plateau_mesh>=.005:failures.append('DC_PLATFORM_MESH');scope_failures['dc_in_gap_platform'].append('MESH')
            if full_mesh>=.005:
                failures.append('DC_FULL_AXIS_MESH: '+str(full_mesh))
                scope_failures['dc_full_axis_mesh'].append('6401_vs_9601')
        if max(optical_mesh,optical_hall_mesh)>=.005:failures.append('OPTICAL_MESH');scope_failures['complex_optical_spectrum'].append('MESH')
    checks['verified_scopes']={key:('PASS' if not failed else 'FAIL') if profile=='reference' else 'SMOKE_ONLY' for key,failed in scope_failures.items()}
    if scope=='optical':
        for key in ('dc_in_gap_platform','dc_full_axis_benchmark','dc_full_axis_mesh'):checks['verified_scopes'][key]='NOT_RUN'
    checks['scope_failures']=scope_failures
    checks['validation_scope']=scope
    checks['failures'] = failures
    checks['status'] = 'PASS' if not failures else 'FAIL'
    checks['dc_model_source_sha256']=sha(ROOT/'DCModel.jl')
    checks['model_source_sha256'] = sha(ROOT/'DiracModel.jl')
    checks['validator_source_sha256'] = sha(Path(__file__))
    checks['curve_sha256'] = {p.name: sha(p) for p in sorted((ROOT/'validation').glob(f'{profile}_*.tsv'))}
    path = ROOT/'validation'/(f'{profile}.json' if scope=='all' else f'{scope}_{profile}.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checks, indent=2, sort_keys=True) + '\n')
    require(not failures, '\n'.join(failures))
    print(f'DIRAC_SPECTRUM_OK profile={profile} cases={len(cases)}')


if __name__ == '__main__':
    validate(sys.argv[1] if len(sys.argv) > 1 else 'reference', 'optical' if '--scope=optical' in sys.argv else 'all')
