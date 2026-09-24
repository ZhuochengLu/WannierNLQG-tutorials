# WannierNLQG tutorials

This collection contains Fe results from WannierNLQG v1.1.0 and an
offline Fe Wannierization readback; see [VALIDATION.md](VALIDATION.md).
The frozen three-mechanism source, 14-case Fe rerun, and local tutorial gates
passed as recorded there. Fe remains diagnostic and not production eligible.

Reproducible tutorials for real-material studies with WannierNLQG, including runnable
workflows, reference results, visualization, and interpretation for band,
nonlinear-response, and quantum-geometry calculations.

## Tutorials at a glance

The prepared collection contains twelve chapters and 46 response/band cases.
Chapter 12 is an offline model readback and licensed rebuild guide, not another
response reference case:

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
10. [Second-harmonic generation](examples/10_second_harmonic_generation/) — calculate
    complex susceptibility and conductivity spectra with WannierNLQG v1.1.0.
11. [Fe OAM and linear response](examples/11_fe_oam_and_linear_response/) — follow a VASP-to-WannierNLQG
    input chain and compare OAM, linear responses, and two ky=0 Berry routes.
12. [Fe Wannierization](examples/12_fe_wannierization/) — verify the supplied
    18-WF model and path bands, or explicitly stage a licensed reconstruction.

For a focused first pass, follow chapters 01, 02, 04, and 06. Chapters 03 and 05,
as well as the Zeeman cases in chapter 09, require the optional spin dataset. Each
chapter includes its own parameter definitions, run commands, reference outputs,
visualization settings, and interpretation notes.

## Quick start

```bash
julia --project=. scripts/bootstrap.jl
julia --project=. scripts/run_group.jl 01 --profile=smoke
WANNIERNLQG_V110_PROJECT=/path/to/wannierNLQG-v1.1.0 julia --project=. scripts/run_group.jl 10 --profile=smoke
# After installing the optional Fe operator bundle:
WANNIERNLQG_V110_PROJECT=/path/to/wannierNLQG-v1.1.0 julia --project=. scripts/run_group.jl 11 --profile=smoke
WANNIERNLQG_V110_PROJECT=/path/to/wannierNLQG-v1.1.0 julia --project=. scripts/run_group.jl 12 --profile=smoke
```

The existing 31 GeS reference results retain their v1.0.1 source identity. Chapter 10
uses the earlier local v1.1.0 source identified in its result summary. Chapter 11's
Fe TB and bundle retain the earlier v1.1.0 generation source recorded in
[`MODEL_STATUS.json`](Materials/Fe/vasp_SOC/MODEL_STATUS.json); the 14 response
tasks record their own, later source identity in their result summaries. Their
`DIAGNOSTIC_ONLY` qualification does not change. The tutorial
environment remains pinned to v1.0.1 for the first nine chapters.
`WANNIERNLQG_V110_PROJECT` must point chapters 10–12 to the v1.1.0 source
checkout being tested. The historical Fe reference results retain their recorded
three-mechanism source tree SHA-256
`0c3c61a489d05decfa02544e65e7a3103aed703234ab45efda134a61e6674523`;
new smoke results record the selected checkout's source identity. To run every
smoke case, set that variable on
`julia --project=. scripts/run_all.jl --profile=smoke`.

The GeS examples use the [GeS SOC model](Materials/GeS/vasp_SOC/README.md).
Fe uses the [committed Fe SOC model](Materials/Fe/vasp_SOC/README.md) and an
optional, hash-bound full operator bundle.
Six GeS spin-dependent
examples require the optional release asset described in
`Materials/GeS/vasp_SOC/OPTIONAL_SPIN_DATA.md`.

GeS reference settings are 100 x 100 x 1 for Brillouin-zone integrals and
200 x 200 for k-slices. Chapter 10 uses 200 photon-energy points from 0 to
4 eV. Chapter 11 uses 40³ Fe integrals, 200 × 200 Fe Berry slices, and 401
optical energies from 0 to 8 eV. These are
tutorial reference settings, not convergence claims.

## Repository map

- `Materials/GeS/vasp_SOC` and `Materials/Fe/vasp_SOC`: redistributable inputs, hashes, and provenance.
- `examples`: twelve tutorial chapters and 46 independently addressable cases,
  plus the chapter-12 offline readback.
- `scripts`: bootstrap, execution, visualization, and release validation.
- `manifests`: task inventory, source identities, and result inventory.
- `test`: static, smoke, result, and public-payload checks.

## License

GPL-2.0-only. The VASP POTCAR is not distributed. Users must obtain licensed
pseudopotential data independently.
