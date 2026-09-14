# WannierNLQG tutorials

Reproducible GeS examples for WannierNLQG v1.0.1, pinned to commit
`1e98f4841d10b6f86aecec8417d3a7da317c0f49`. The repository covers band interpolation, charge and spin
photocurrents, and momentum-resolved quantum geometry. Projector methods, photon-drag
responses, SHG, and model construction are intentionally outside the first release.

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

## Scientific scope

The parameter choices and band subspaces follow the GeS discussion in the associated
manuscript: V=[19,20], C1=[21,22], C2=[23,24], Fermi energy -2.5 eV, temperature 0 K,
Gaussian broadening 0.060 eV, denominator regularization 0.001 eV, and degeneracy
threshold 0.002 eV. The repository uses the ordinary exported GeS model and therefore
does not reproduce the manuscript's symmetrized SAWF data bundle byte for byte.

All numerical outputs are labelled `TUTORIAL_NUMERICAL_EVIDENCE`. Plot sidecars remain
`PRESENTATION_ONLY`; neither label establishes Physics or Production qualification.

## Repository map

- `Materials/GeS/vasp_SOC`: redistributable inputs, hashes, and provenance.
- `examples`: nine tutorial chapters and 31 independently runnable cases.
- `scripts`: bootstrap, execution, visualization, and release validation.
- `manifests`: task inventory, source identities, and result inventory.
- `test`: static, smoke, result, and public-payload checks.

## License

GPL-2.0-only. The VASP POTCAR is not distributed. Users must obtain licensed
pseudopotential data independently.
