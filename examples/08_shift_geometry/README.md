# Shift geometry

Shift vectors and quantum Hermitian connections from three supported constructions.

## 1. Physical quantity and method

Each row is one independently executable `TaskConfig`. Integral tasks retain the complete native tensor; the component column is the default visualization selection.

| Case | Quantity | Method | Reference mesh | Photon energy (eV) | Component | Band selection | Optional spin data |
|---|---|---|---:|---:|---|---|---|
| `shift_vector_geometric_loop.jl` | `shift_vector` | `geometric_loop` | 200×200 | None | `(2,2,2)` | `{"conduction":[21,22],"valence":[19,20]}` | no |
| `shift_vector_wilson_loop.jl` | `shift_vector` | `wilson_loop` | 200×200 | None | `(2,2,2)` | `{"conduction":[21,22],"valence":[19,20]}` | no |
| `quantum_hermitian_connection_conventional.jl` | `quantum_hermitian_connection` | `conventional` | 200×200 | None | `(2,2,2)` | `{"conduction":[21,22],"valence":[19,20]}` | no |
| `quantum_hermitian_connection_geometric_loop.jl` | `quantum_hermitian_connection` | `geometric_loop` | 200×200 | None | `(2,2,2)` | `{"conduction":[21,22],"valence":[19,20]}` | no |
| `quantum_hermitian_connection_wilson_loop.jl` | `quantum_hermitian_connection` | `wilson_loop` | 200×200 | None | `(2,2,2)` | `{"conduction":[21,22],"valence":[19,20]}` | no |

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
julia --project=. examples/08_shift_geometry/run.jl --profile=smoke
julia --project=. examples/08_shift_geometry/run.jl --profile=reference
julia --project=. scripts/visualize_all.jl
```

Individual smoke commands:

```bash
julia --project=. examples/08_shift_geometry/cases/shift_vector_geometric_loop.jl --profile=smoke
julia --project=. examples/08_shift_geometry/cases/shift_vector_wilson_loop.jl --profile=smoke
julia --project=. examples/08_shift_geometry/cases/quantum_hermitian_connection_conventional.jl --profile=smoke
julia --project=. examples/08_shift_geometry/cases/quantum_hermitian_connection_geometric_loop.jl --profile=smoke
julia --project=. examples/08_shift_geometry/cases/quantum_hermitian_connection_wilson_loop.jl --profile=smoke
```

Existing result directories are never overwritten.

## 5. Output interpretation

- `kslice_shift_vector_geometric_loop`: `GeS_svk_i_geo.dat`, `GeS_svk_r_geo.dat`
- `kslice_shift_vector_wilson_loop`: `GeS_svk_i_wilson.dat`, `GeS_svk_r_wilson.dat`
- `kslice_quantum_hermitian_connection_conventional`: `GeS_qhck_i_conv.dat`, `GeS_qhck_r_conv.dat`
- `kslice_quantum_hermitian_connection_geometric_loop`: `GeS_qhck_i_geo.dat`, `GeS_qhck_r_geo.dat`
- `kslice_quantum_hermitian_connection_wilson_loop`: `GeS_qhck_i_wilson.dat`, `GeS_qhck_r_wilson.dat`

Every task directory also contains native `metadata.txt` and a tutorial `summary.json` with input/output SHA-256 values. Complex K-slice quantities retain separate real (`_r_`) and imaginary (`_i_`) files; the default figure shows the real part. `raw/`-style quantities retain the package's native stable filenames without renaming.

## 6. Figure-reading guide

`GeS_shift_vector_methods` uses a shared color contract for Geometric and Wilson maps; `GeS_qhc_methods` places Conventional, Geometric, and Wilson maps in declared panel order. They expose method differences without classifying those differences as numerical errors.

K-slice rendering uses the package's periodic-centered `fftshift + transpose` convention. Heat-map color limits use the symmetric 99.5th percentile for presentation and the sidecar records that clipping; numerical files remain unchanged. Integral figures show the declared component. All PNGs are white-background 600 dpi and each PDF/PNG pair has a `.plot.json` audit sidecar.

Reference-profile figures below display the selected components and units stated in the case table and axes. The PNG/PDF files are presentation artifacts, not additional convergence evidence.

![kslice shift vector geometric loop](figures/kslice_shift_vector_geometric_loop.png)  [PDF](figures/kslice_shift_vector_geometric_loop.pdf) [Plot audit](figures/kslice_shift_vector_geometric_loop.plot.json)

*Geometric Loop shift-vector K-slice, component (2,2,2); native output units; presentation only.*

![kslice shift vector wilson loop](figures/kslice_shift_vector_wilson_loop.png)  [PDF](figures/kslice_shift_vector_wilson_loop.pdf) [Plot audit](figures/kslice_shift_vector_wilson_loop.plot.json)

*Wilson Loop shift-vector K-slice, component (2,2,2); native output units; presentation only.*

![kslice quantum hermitian connection conventional](figures/kslice_quantum_hermitian_connection_conventional.png)  [PDF](figures/kslice_quantum_hermitian_connection_conventional.pdf) [Plot audit](figures/kslice_quantum_hermitian_connection_conventional.plot.json)

*Conventional quantum Hermitian connection, component (2,2,2); native output units; presentation only.*

![kslice quantum hermitian connection geometric loop](figures/kslice_quantum_hermitian_connection_geometric_loop.png)  [PDF](figures/kslice_quantum_hermitian_connection_geometric_loop.pdf) [Plot audit](figures/kslice_quantum_hermitian_connection_geometric_loop.plot.json)

*Geometric Loop quantum Hermitian connection, component (2,2,2); native output units; presentation only.*

![kslice quantum hermitian connection wilson loop](figures/kslice_quantum_hermitian_connection_wilson_loop.png)  [PDF](figures/kslice_quantum_hermitian_connection_wilson_loop.pdf) [Plot audit](figures/kslice_quantum_hermitian_connection_wilson_loop.plot.json)

*Wilson Loop quantum Hermitian connection, component (2,2,2); native output units; presentation only.*

![GeS shift vector methods](figures/GeS_shift_vector_methods.png)  [PDF](figures/GeS_shift_vector_methods.pdf) [Plot audit](figures/GeS_shift_vector_methods.plot.json)

*Geometric Loop and Wilson Loop shift-vector comparison, component (2,2,2); native output units; presentation only.*

![GeS qhc methods](figures/GeS_qhc_methods.png)  [PDF](figures/GeS_qhc_methods.pdf) [Plot audit](figures/GeS_qhc_methods.plot.json)

*Conventional, Geometric Loop, and Wilson Loop quantum-Hermitian-connection comparison, component (2,2,2); native output units; presentation only.*

## 7. Relation to the manuscript

This tutorial follows quantities and parameter choices used in the manuscript workflow, but uses the released ordinary GeS model and a separately audited VASP display reference. It is not a byte-identical reconstruction of the manuscript's SAWF band bundle and is not evidence that manuscript figures were reproduced.

## 8. Qualification limits

Committed outputs are `TUTORIAL_NUMERICAL_EVIDENCE`: finite, hashed, and reproduced with WannierNLQG v1.0.1 at the stated mesh. They are not Physics PASS or Production PASS. Differences between Conventional, Geometric Loop, and Wilson Loop are displayed as method differences, not automatically classified as errors.
