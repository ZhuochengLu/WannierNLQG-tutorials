# WannierNLQG tutorials

Reproducible tutorials for real-material studies with WannierNLQG, including runnable
workflows, reference results, visualization, and interpretation for band,
nonlinear-response, and quantum-geometry calculations.

## Tutorials at a glance

The current collection contains nine chapters and 31 independently runnable cases:

1. [Band structure](examples/01_band_structure/) — interpolate bands along a
   high-symmetry path and compare the model bands with a first-principles reference.
2. [Integrated charge responses](examples/02_integral_charge_responses/) — calculate
   shift and injection currents and compare the available shift-current methods.
3. [Integrated spin responses](examples/03_integral_spin_responses/) — calculate
   frequency-dependent injection and shift spin currents using optional spin data.
4. [Momentum-resolved charge responses](examples/04_kslice_charge_responses/) — map
   charge photocurrent contributions across a two-dimensional momentum slice.
5. [Momentum-resolved spin responses](examples/05_kslice_spin_responses/) — map spin
   photocurrent contributions using the optional spin dataset.
6. [Pairwise quantum geometry](examples/06_qg_pairwise/) — visualize Berry curvature,
   quantum metric, and their interband counterparts.
7. [Quantum-geometric multipoles](examples/07_qg_multipoles/) — explore dipoles,
   quadrupoles, and the quantum Christoffel symbol.
8. [Shift geometry](examples/08_shift_geometry/) — compare shift-vector and quantum
   Hermitian-connection formulations across supported methods.
9. [Higher-order and spin geometry](examples/09_higher_and_spin_geometry/) — examine
   Hermitian curvature, triple phase products, and Zeeman quantum geometry.

For a focused first pass, follow chapters 01, 02, 04, and 06. Chapters 03 and 05,
as well as the Zeeman cases in chapter 09, require the optional spin dataset. Each
chapter includes its own parameter definitions, run commands, reference outputs,
visualization settings, and interpretation notes.

## Quick start

```bash
julia --project=. scripts/bootstrap.jl
julia --project=. scripts/run_group.jl 01 --profile=smoke
julia --project=. scripts/run_all.jl --profile=smoke
```

The ordinary examples use `Materials/GeS/vasp_SOC/GeS_tb.dat`. Six spin-dependent
examples require the optional release asset described in
`Materials/GeS/vasp_SOC/OPTIONAL_SPIN_DATA.md`.

Reference settings are 100 x 100 x 1 for Brillouin-zone integrals and 200 x 200 for
k-slices. These settings are tutorial reference settings, not convergence claims.

## Repository map

- `Materials/GeS/vasp_SOC`: redistributable inputs, hashes, and provenance.
- `examples`: nine tutorial chapters and 31 independently runnable cases.
- `scripts`: bootstrap, execution, visualization, and release validation.
- `manifests`: task inventory, source identities, and result inventory.
- `test`: static, smoke, result, and public-payload checks.

## License

GPL-2.0-only. The VASP POTCAR is not distributed. Users must obtain licensed
pseudopotential data independently.
