# bcc Fe SOC inputs, Wannierization, and path bands

This directory contains the original bcc-Fe first-principles input, a staged
WannierNLQG v1.1.0 input script, the rerun's 18-WF TB model, and lightweight
first-principles/TB path-band tables. `MODEL_STATUS.json` binds the actual
solver terminal status, frozen source identity, TB, and full operator bundle.
The model and response tables remain `DIAGNOSTIC_ONLY / Physics HOLD /
Production NOT_ELIGIBLE`; numerical readability is not material convergence.
The earlier response-source optical term writer had a label-order conflict.
The corrected-source response run is identified separately from this model in
[chapter 11](../../../examples/11_fe_oam_and_linear_response/README.md);
package acceptance and material qualification remain separate.

## Inputs and licensed boundary

`POSCAR`, `INCAR`, and `KPOINTS` are the source calculation inputs. `INCAR`
contains the projection and window block that VASP writes into its generated
interface input. `POTCAR.txt` identifies the required licensed PAW-PBE Fe
dataset; no POTCAR is distributed. Neither VASP executables nor WAVECAR,
OUTCAR, CHGCAR, `.amn`, `.mmn`, `.eig`, or `.chk` are distributed. The native
PAW route uses generated MMN only for neighbour topology; it regenerates
numerical matrix elements from the VASP wavefunctions.

The source used VASP 6.6.0 with a Wannier90 3.1.0 interface, Julia 1.11.2,
`10×10×10` Γ-centered VASP sampling, 64 spinor bands, 18 Wannier functions,
and `ENCUT=450 eV`. The source VASP Fermi energy was
`5.7156290716733436 eV`; the response reference mesh is separate (`40³`).
The exact input and model checksums are in `DATA_MANIFEST.json`. The published
`POSCAR` differs from the frozen VASP input only by removal of one trailing tab
on lattice-vector line 5; all numerical tokens are unchanged. The manifest
`files` entry hashes this 316-byte published copy, while
`source_frozen_vasp_inputs.POSCAR` and the VASP band receipt retain the
317-byte historical calculation-input hash. Historical path-band replay
requires that original raw input.

The source snapshot used to generate the Fe TB and bundle has tree SHA-256
`aaf92433a5b3a87849162d0fef744a59544fde97f10e558aa3cb1a1bf151ec2c`.

`bands/Fe_vasp_path_absolute.dat` is a publishable 801-point/64-band table
converted from the separately verified LMAXMIX=4 fixed-charge VASP path. Its
SCF Fermi-level and Γ-point consistency check, source hashes, and path shape
are recorded in `bands/Fe_vasp_path_receipt.json`. The matching 801-point/
18-band Wannier path is `bands/Fe_tb_path_absolute.dat`; its receipt binds the
new TB and pointwise path coordinates. Both use the same absolute-energy
reference, with no fitted offset. The VASP EIGENVAL/OUTCAR themselves are not
distributed.

## Rebuild the calculation

Use [chapter 12](../../../examples/12_fe_wannierization/) to stage this
directory's redistributable inputs into a **new external workdir**. In a
licensed VASP environment, place the matching POTCAR in that workdir and run
the following commands from there; do not create VASP or Wannier intermediate
files inside the public tutorial directory:

```bash
export VASP_NCL=/path/to/vasp_ncl
export MPIEXEC=/path/to/matching/mpiexec
MPI_RANKS=4 ./run_vasp.sh > Fe_vasp.out 2>&1
export JULIA_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
for stage in vasp-preflight rebase-inputs prepare target spn uiu uhu siu shu solve readback; do
  julia --project=/path/to/WannierNLQG-v1.1.0 Fe_ordinary_full_driver.jl "$stage"
done
```

The driver exposes the exact input configuration and stage checks, with at
most two streaming workers and a 24-GiB preparation budget on the rerun host.
Only execution parallelism differs from the preceding calculation. It refuses
to replace accepted outputs. Preserve the actual terminal status and never
force byte-for-byte parity across nonconverged runs. The public TB hash is in
`MODEL_STATUS.json` and `DATA_MANIFEST.json`.

## Optional operator bundle for response runs

The full 11-operator `Fe_fixed_full.h5` is not tracked in Git.
A separately prepared archive named in `FE_BUNDLE_FILES.json` is intended for
Release asset distribution; check its availability on the Release page. Its
archive and extracted-file hashes are in `FE_BUNDLE_FILES.json`.
Install a verified local copy with:

```bash
bash scripts/install_fe_bundle.sh /path/to/archive-named-in-FE_BUNDLE_FILES.json
```

Run that command from the tutorial repository root. The installer refuses to
overwrite an existing bundle. One may instead set
`FE_OPERATOR_BUNDLE=/path/to/verified/Fe_fixed_full.h5` for local testing.
The bundle and TB must pass their hashes together; a similarly named file is
not sufficient.

Identical first-principles inputs do not guarantee byte-identical VASP or
nonconverged Wannierization output across builds and machines. Compare
provenance, solver status, bands, and downstream response metrics, and keep
Engineering, Numerical, Physics, and Production qualifications separate.
