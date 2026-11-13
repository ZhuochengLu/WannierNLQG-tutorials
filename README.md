# WannierNLQG Tutorials

These tutorials demonstrate band structures, optical and transport responses, quantum geometry, and model and material workflows with WannierNLQG. Each chapter provides its own explanation, inputs, saved data, figures, and plotting scripts.

## Chapters

- 01 · [Band structure of GeS](examples/01_band_structure/README.md)
- 02 · [Integral charge responses](examples/02_integral_charge_responses/README.md)
- 03 · [Integral spin-current responses](examples/03_integral_spin_responses/README.md)
- 04 · [Momentum-resolved charge responses](examples/04_kslice_charge_responses/README.md)
- 05 · [Momentum-resolved spin-current responses](examples/05_kslice_spin_responses/README.md)
- 06 · [Pairwise quantum geometry](examples/06_qg_pairwise/README.md)
- 07 · [Momentum derivatives of quantum geometry](examples/07_qg_multipoles/README.md)
- 08 · [Shift vectors and quantum Hermitian connections](examples/08_shift_geometry/README.md)
- 09 · [Higher and Zeeman-weighted interband geometry](examples/09_higher_and_spin_geometry/README.md)
- 10 · [Second-harmonic generation in GeS](examples/10_second_harmonic_generation/README.md)
- 11 · [Orbital magnetization and linear response in Fe](examples/11_fe_oam_and_linear_response/README.md)
- 12 · [Fe Wannierization and band assessment](examples/12_fe_wannierization/README.md)
- 13 · [Haldane model and anomalous Hall conductance](examples/13_haldane_anomalous_hall/README.md)
- 14 · [Rice–Mele model and shift current](examples/14_rice_mele_shift_current/README.md)
- 15 · [Nonperiodic Dirac model and response limits](examples/15_nonperiodic_dirac_response/README.md)
- 16 · [Third-harmonic generation in monolayer graphene](examples/16_monolayer_graphene_thg/README.md)
- 17 · [Jerk current: model and material examples](examples/17_jerk_current/README.md)

## Environment and execution

Julia 1.11 or later and WannierNLQG 1.2 are required. Select an existing WannierNLQG 1.2 source directory. The [software validation record](manifests/software_validation.json) identifies the sources used for the recorded tutorial calculations.

From the tutorial repository root, prepare the environment and run the [Haldane-model example](examples/13_haldane_anomalous_hall/README.md), which does not require the external GeS or Fe material data:

```bash
julia --project=. scripts/bootstrap.jl /path/to/WannierNLQG-v1.2.0
julia --project=.runtime/env scripts/run_group.jl 13 --check
julia --project=.runtime/env scripts/run_group.jl 13 --case=tb_topological --output=.runtime/haldane
```

Bootstrap creates a private environment in `.runtime/env` by default. Set `WANNIERNLQG_TUTORIAL_ENV` to choose another location; use that same location in the `--project` option of subsequent Julia commands. Choose a new output directory for a calculation.

Material examples require explicitly supplied data; see the [material data guide](Materials/README.md). Missing data are reported as `UNAVAILABLE_INPUT`, without an automatic download or substitution of another model. Chapter 12 also requires its own VASP inputs, as described in its chapter.

## Plotting and checks

Plotting requires the Python dependencies in [requirements-plot.txt](requirements-plot.txt), plus system installations of Times New Roman, TeX/newtxtext/newtxmath/bm/textgreek, and Poppler. Fonts and TeX assets are not distributed with this package; there is no silent font or Mathtext fallback.

For example, list and check the available figures in [chapter 06](examples/06_qg_pairwise/README.md), then draw one from saved data:

```bash
python examples/06_qg_pairwise/plot.py --list
python examples/06_qg_pairwise/plot.py --check
python examples/06_qg_pairwise/plot.py --figure=kslice_quantum_metric_conventional --output=.runtime/metric-figure
```

`--figure` reads saved data without recomputing responses. Each chapter’s `reproduce.json` maps its inputs, data, and figures. Chapters use `plot_configs/` where applicable; shared runners and plotting styles are in `scripts/`, and model code is in `models/`.

To check the tutorial layout and current inputs:

```bash
python test/validate_layout.py
julia --project=.runtime/env test/current_inputs.jl .runtime/input-check
```

The ordinary suite contains 89 reference inputs and 65 smoke-test fixtures. Of these, 97 use the unified GeS/Fe material pairs; the other 57 do not require those assets. The chapter-specific valley replay and native Wannierization workflows are separate. See [checks](CHECKS.md) and [material case provenance](manifests/material_case_results.json) for recorded validation and execution identities.

## Material data and licenses

Tutorial code is licensed [GPL-2.0-only](LICENSE). The separately supplied unified GeS/Fe numerical model and operator data are licensed **CC BY 4.0** by **Zhuocheng Lu**. See [LICENSE_DATA.md](LICENSE_DATA.md) for the exact four-file scope, attribution and exclusions, and [DATA_CITATION.cff](DATA_CITATION.cff) for the data citation. Use [CITATION.cff](CITATION.cff) for the software citation. Third-party literature references are excluded from the material-data license; see [third-party attribution](THIRD_PARTY_REFERENCES.md).

The four scientific files total 7,196,026,439 bytes. The two prepared archives also include family-specific license and citation notices. See [asset identities and availability](Materials/ASSETS.md), the [distribution manifest](manifests/material_distribution.json), and the [material data guide](Materials/README.md) for acquisition and installation. New public asset URLs have not yet been published.

Representative local GeS/Fe smoke responses and output reading and plotting have been checked with their recorded sources; these checks do not establish complete material, mesh, or full-spectrum convergence. Chapter 12’s unconverged Z, THG’s finite-domain, budget, and prescription limits, and the recorded GeS jerk grid sensitivity remain relevant. See the individual chapters, [data provenance](DATA_PROVENANCE.md), and [release review](RELEASE_REVIEW.md) for details.
