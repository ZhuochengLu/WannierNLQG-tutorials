# Fe SOC Wannierization: rebuild and diagnose an 18-WF model

This example separates two tasks. The default command verifies the distributed Fe
model and 801-point DFT/TB path-band receipts offline; it does **not** run VASP or
Wannierization. An explicit, licensed reconstruction starts from the
[Fe SOC input and provenance guide](../../Materials/Fe/vasp_SOC/README.md).
The recorded terminal state is `MAX_ITERATIONS`, with
`DIAGNOSTIC_ONLY / Physics HOLD / Production NOT_ELIGIBLE`. Readability and
band agreement are not a convergence certificate.

## Offline readback

From the tutorial root, use WannierNLQG 1.1.0:

```bash
export WANNIERNLQG_V110_PROJECT=/path/to/WannierNLQG-v1.1.0
julia --project="$WANNIERNLQG_V110_PROJECT" examples/12_fe_wannierization/run.jl --profile=smoke
```

The check binds the 18-orbital TB hash, solver receipt, both 801-point tables,
their `64/18` band counts, common SCF Fermi reference and path distances. It
does not need the optional Fe operator bundle. The first-principles path table
comes from an already verified fixed-charge calculation; VASP is not rerun here.

![Fe first-principles path bands](../11_fe_oam_and_linear_response/figures/Fe_vasp_path_bands.png) [PDF](../11_fe_oam_and_linear_response/figures/Fe_vasp_path_bands.pdf)

![Diagnostic Fe DFT/TB path comparison](../11_fe_oam_and_linear_response/figures/Fe_vasp_tb_path_comparison_bands.png) [PDF](../11_fe_oam_and_linear_response/figures/Fe_vasp_tb_path_comparison_bands.pdf)

![Diagnostic Fe DFT/TB band errors](../11_fe_oam_and_linear_response/figures/Fe_vasp_tb_path_comparison_errors.png) [PDF](../11_fe_oam_and_linear_response/figures/Fe_vasp_tb_path_comparison_errors.pdf)

The DFT/TB energy-set comparison is diagnostic, not wavefunction matching or a
material-fit pass. The plots use one SCF Fermi reference without a fitted shift.

## Explicit licensed reconstruction

Stage only the redistributable inputs into a new directory outside this
repository. The helper verifies their hashes and refuses to overwrite a path:

```bash
python3 examples/12_fe_wannierization/stage_rebuild.py --workdir /path/to/new-fe-workdir
```

Supply a licensed `POTCAR` matching `POTCAR.txt` there, then follow the staged
commands in the [material guide](../../Materials/Fe/vasp_SOC/README.md): VASP,
`vasp-preflight`, `rebase-inputs`, `prepare`, `target`, `spn`, `uiu`, `uhu`,
`siu`, `shu`, `solve`, and `readback`. Run from the staged directory with Julia
1.11.2 and the 1.1.0 project. Use four Julia threads, at most two streaming
workers/24 GiB during preparation, and one stage at a time. Outputs stay in the
workdir and are **not** copied into the public tutorial automatically. Preserve
each stage's logs, hashes and actual terminal status; different builds or a
nonconverged solve cannot promise byte-identical results.

Neither VASP, POTCAR, WAVECAR, OUTCAR, CHGCAR nor the Wannier intermediate
files are distributed. The Fe TB and band tables are tutorial evidence only.
