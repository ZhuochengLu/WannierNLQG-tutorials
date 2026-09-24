# Band structure

TB bands on Γ-X-S-Y-Γ and a diagnostic comparison with unchanged VASP eigenvalues.

## 1. Physical quantity and method

Each row is one independently executable `TaskConfig`. Integral tasks retain the complete native tensor; the component column is the default visualization selection.

| Case | Quantity | Method | Reference mesh | Photon energy (eV) | Component | Band selection | Optional spin data |
|---|---|---|---:|---:|---|---|---|
| `band_structure.jl` | `band_structure` | `conventional` | path | n/a | `fulltensor` | `"all bands"` | no |

The component and ordered band selection are explicit in every case file and repeated in `summary.json`.

## 2. Inputs

- Model: [GeS SOC TB model](../../Materials/GeS/vasp_SOC/README.md).
- Structure and audit inputs: `GeS.win`, `POSCAR`, `INCAR`, `KPOINTS`, and input manifests in the same material directory.
- This chapter needs only the committed ordinary `GeS_tb.dat` model.
- Protected VASP files are not distributed; `POTCAR.txt` records the pseudopotential choices.

## 3. Parameter contract

| Parameter | Reference value |
|---|---|
| Fermi energy / temperature | `-2.5 eV` / `0 K` for optical tasks |
| Broadening | Gaussian, `0.060 eV` for optical tasks |
| Denominator regularization | `0.001 eV` where applicable |
| Finite-difference step | `1e-4 Å^-1` for derivative geometry |
| Degeneracy threshold | `0.002 eV` |
| Bands | `V=[19,20]`, `C1=[21,22]`, `C2=[23,24]` |
| Fourier / centers | `direct` / `Convention_II` |
| Output precision | 17 digits; no tutorial-side numerical reordering or truncation |

The case file is authoritative: parameters irrelevant to a quantity are not artificially applied. `smoke` changes only mesh/path density.

## 4. Run and visualize

```bash
julia --project=. examples/01_band_structure/run.jl --profile=smoke
julia --project=. examples/01_band_structure/run.jl --profile=reference
julia --project=. scripts/visualize_all.jl
```

Individual smoke commands:

```bash
julia --project=. examples/01_band_structure/cases/band_structure.jl --profile=smoke
```

Existing result directories are never overwritten.

## 5. Output interpretation

- `band_structure`: `GeS_bands.dat`, `GeS_kpath.json`

Every task directory also contains native `metadata.txt` and a tutorial `summary.json` with input/output SHA-256 values. Complex K-slice quantities retain separate real (`_r_`) and imaginary (`_i_`) files; the default figure shows the real part. `raw/`-style quantities retain the package's native stable filenames without renaming.

## 6. Figure-reading guide

K-slice rendering uses the package's periodic-centered `fftshift + transpose` convention. Heat-map color limits use the symmetric 99.5th percentile for presentation and the sidecar records that clipping; numerical files remain unchanged. Integral figures show the declared component. All PNGs are white-background 600 dpi and each PDF/PNG pair has a `.plot.json` audit sidecar.

Reference-profile figures below display the selected components and units stated in the case table and axes. The PNG/PDF files are presentation artifacts, not additional convergence evidence.

![GeS vasp band](figures/GeS_vasp_band.png)  [PDF](figures/GeS_vasp_band.pdf) [Plot audit](figures/GeS_vasp_band.plot.json)

*VASP path bands; energy relative to the shared Fermi level (eV); presentation only.*

![band structure](figures/band_structure.png)  [PDF](figures/band_structure.pdf) [Plot audit](figures/band_structure.plot.json)

*Conventional TB path bands; energy relative to the shared Fermi level (eV); presentation only.*

![GeS band comparison](figures/GeS_band_comparison.png)  [PDF](figures/GeS_band_comparison.pdf) [Plot audit](figures/GeS_band_comparison.plot.json)

*DFT/TB path-band comparison on one energy reference (eV); diagnostic display, not a band-fit qualification.*

## 7. Relation to the manuscript

This tutorial follows quantities and parameter choices used in the manuscript workflow, but uses the released ordinary GeS model and a separately audited VASP display reference. It is not a byte-identical reconstruction of the manuscript's SAWF band bundle and is not evidence that manuscript figures were reproduced.

## 8. Qualification limits

Committed outputs are `TUTORIAL_NUMERICAL_EVIDENCE`: finite, hashed, and reproduced with WannierNLQG v1.0.1 at the stated mesh. They are not Physics PASS or Production PASS. Differences between Conventional, Geometric Loop, and Wilson Loop are displayed as method differences, not automatically classified as errors.
