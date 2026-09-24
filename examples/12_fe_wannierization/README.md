# Fe SOC Wannierization: source to diagnostic bands

This chapter runs the WannierNLQG solver on Fe wavefunctions, computes bands
from **that run's** 18-WF TB, and compares them with published 64-band VASP
bands. Solver convergence is not required for this diagnostic lesson. An
accepted-state TB must actually be exported before the band steps can run.
All results remain `DIAGNOSTIC_ONLY / Physics HOLD / Production NOT_ELIGIBLE`.

The default `run.jl --profile=smoke|reference` is still the historical
**offline readback** used by the repository-wide smoke runner. It does not run
VASP or Wannierization.

## 1. Prepare the Fe source

One Fe SOC calculation must provide `POSCAR`, `POTCAR`, `INCAR`, `OUTCAR`,
`WAVECAR`, `wannier90.win`, `wannier90.eig`, and `wannier90.mmn` in an external
work directory. The raw MMN supplies neighbor topology; the native PAW route
recomputes numerical MMN/AMN from WAVECAR. Raw `wannier90.amn` is not used.

Stage the [redistributable inputs](../../Materials/Fe/vasp_SOC/) into a new
directory, supply the matching licensed `POTCAR`, and follow the
[VASP instructions](../../Materials/Fe/vasp_SOC/README.md). If you already
have the complete matching source calculation, use it without rerunning VASP.
Protected VASP files and Wannier intermediates are not distributed.

```bash
python3 examples/12_fe_wannierization/stage_rebuild.py --workdir /path/to/new-fe-workdir
# Supply a licensed POTCAR there, then run the staged run_vasp.sh.
```

The comparison uses the published [801-point VASP path table](../../Materials/Fe/vasp_SOC/bands/Fe_vasp_path_absolute.dat)
and its [source receipt](../../Materials/Fe/vasp_SOC/bands/Fe_vasp_path_receipt.json).
This chapter does not rerun the fixed-charge path calculation.

## 2. Run Wannierization

Use Julia 1.11.2 and WannierNLQG 1.1.0. The comparison also needs Python 3
with NumPy. Choose a `FE_OUTPUT` path that does not yet exist. From the tutorial
root:

```bash
export WANNIERNLQG_V110_PROJECT="/path/to/WannierNLQG-v1.1.0"
export FE_WORKDIR="/path/to/fe-vasp-source"
export FE_OUTPUT="/path/to/new-fe-output"
export JULIA_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1
julia --project="$WANNIERNLQG_V110_PROJECT" \
  examples/12_fe_wannierization/wannierize_fe.jl "$FE_WORKDIR" "$FE_OUTPUT"
```

Read [the solver script](wannierize_fe.jl) top to bottom. Its configuration is
kept in one file:

| Setting | Value | Role |
| --- | --- | --- |
| `source` | Fe VASP `POSCAR/POTCAR/INCAR/OUTCAR/WAVECAR`, spinor bands `1:64` | Wavefunctions and native PAW matrix elements |
| `projection_basis` | Fe s/p/d from `wannier90.win`, `num_wannier=18` | Initial 18-WF subspace |
| `wannierization_mode` | `:ordinary` | Full-BZ Wannierization without a symmetry-reduced target |
| `outer_min_ev/outer_max_ev` | `-8/50` | Disentanglement window in eV |
| `frozen_min_ev/frozen_max_ev` | `-8/20` | States retained exactly in eV |
| `solver` | AMN start, fixed two-stage, tolerance `1e-10` | Original Fe optimization settings |
| `checkpoint` | Every 50 iterations; total ceiling 2500 | Retains the last accepted state |
| `output.profile` | `:hamiltonian_position` | Hamiltonian and position for TB bands |

The raw MMN provides topology while `NativeVASPPAWMatrices` regenerates its
numerical overlaps and AMN. The H/r profile does not change convergence;
full-profile SPN/uIu/uHu/sIu/sHu inputs are unnecessary here. The solver's
`constraint_operation_scope=:full` refers to its constraint scope, not to
the 11-operator output profile.

`$FE_OUTPUT/attempt1.json` and `terminal_result.json` record the actual
status, source and input hashes, and artifacts. The disentanglement and
localization stages each have a 1000-step cap, so this configuration can stop
before the 2500 total-iteration ceiling. It does not auto-restart.
`selected_model.json` appears only after TB and bundle readback.
If no TB passes the accepted-state structural export gate, the script stops
here and never substitutes the historical `Fe_tb.dat`.

## 3. Compute and compare bands

After the new TB exists:

```bash
julia --project="$WANNIERNLQG_V110_PROJECT" \
  examples/12_fe_wannierization/fe_bands.jl "$FE_OUTPUT"
python3 examples/12_fe_wannierization/compare_fe_bands.py "$FE_WORKDIR" "$FE_OUTPUT"
julia --project="$WANNIERNLQG_V110_PROJECT" \
  "$WANNIERNLQG_V110_PROJECT/scripts/plot_band_structure.jl" \
  --config "$FE_OUTPUT/band_plot.json"
```

The `Band` task calculates 801 points on Γ–H–P–N–Γ from **this run's TB**.
The comparison checks the lattice, path coordinates and distances, both band
tables, hashes, and common SCF Fermi reference. It applies no fitted shift.
The overlay and `comparison_result.json` are an energy-set diagnosis. Its
nearest-VASP-energy numbers allow many TB bands to select the same VASP band;
they are neither wavefunction matching nor a material-fit pass. Complete run
artifacts remain in `$FE_OUTPUT` outside the public repository; only the
checked lightweight table, PNG, and path-free receipt are copied below.

### Recorded first-run result (2026-09-25)

![New Fe TB versus VASP diagnostic bands](results/native_paw_2026-09-25/Fe_new_tb_vs_vasp.png)

The published [18-band table](results/native_paw_2026-09-25/Fe_new_tb_path_absolute.dat)
and [hash receipt](results/native_paw_2026-09-25/RESULT.json) come from the
first accepted-state export, at iteration 2000 with `MAX_ITERATIONS`. The
requested total ceiling was 2500; the two 1000-step stage caps stopped it
earlier. The recorded continuation to iteration 2001 was started before the
no-restart instruction, is retained as unselected local evidence, and was not
used for this table or plot. The near-Fermi nearest-energy-set RMS is about
`0.00981 eV`; that many-to-one number is diagnostic only. The new large TB,
bundle, checkpoint, and licensed VASP inputs are not published.

## 4. Historical readback and full reconstruction

The quick offline check is:

```bash
julia --project="$WANNIERNLQG_V110_PROJECT" \
  examples/12_fe_wannierization/run.jl --profile=smoke
```

It verifies the distributed [historical model status](../../Materials/Fe/vasp_SOC/MODEL_STATUS.json)
and Fe TB/VASP tables. The historical terminal state is `MAX_ITERATIONS`;
readability and band agreement do not imply convergence. For the complete
11-operator reconstruction and audits, consult the
[advanced driver](../../Materials/Fe/vasp_SOC/Fe_ordinary_full_driver.jl)
and [material guide](../../Materials/Fe/vasp_SOC/README.md).
