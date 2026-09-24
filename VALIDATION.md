# Fe 1.1.0 three-mechanism response validation — local diagnostic candidate

The formal 1.1.0 source now exports `drude`, `quantum_metric`,
`berry_curvature`, and `total` for linear transport and linear optical
response. The Berry-curvature-named conductivity contribution combines the
previous ambient-curvature contact and interband Hall terms; its physical
response mechanism is the anomalous Hall effect. All 14 Fe cases were rerun
from one frozen response source and imported with native filenames. This is
an engineering/numerical result, **not** a converged Fe material prediction.
The model remains `MAX_ITERATIONS / DIAGNOSTIC_ONLY / Physics HOLD /
Production NOT_ELIGIBLE`. At the time of this local validation, nothing was
uploaded to GitHub.

## Source, model, and rollback identity

- Frozen response source-tree SHA-256:
  `0c3c61a489d05decfa02544e65e7a3103aed703234ab45efda134a61e6674523`.
  `SHA256SUMS` SHA-256:
  `55f1867fe07e6f8f278769919380b03e0d4061b12dc7a9f800d29145950d60f9`.
  The 734-file source manifest, formatting, documentation, and release
  whitelist checks passed. The response-code snapshot was also verified in
  a byte-identical temporary directory for the package test gate, avoiding
  a recurrent macOS `.DS_Store` in the iCloud release directory.
- Fe TB and full operator bundle retain their **earlier model-generation**
  source-tree identity
  `aaf92433a5b3a87849162d0fef744a59544fde97f10e558aa3cb1a1bf151ec2c`.
  TB SHA-256 is
  `5e19a8258741f4c4555bb47d2dedc597673972f4f1faf683c44c1ce034949714`;
  bundle SHA-256 is
  `8afdfc64742feb920a3ebc4f49fbd571c3f91fd5a111e588db02ed9676fc0115`.
  VASP inputs and the previously validated 801-point VASP path are bound by
  `Materials/Fe/vasp_SOC/DATA_MANIFEST.json` and the band receipts. VASP and
  Wannierization were **not** rerun for this change.
- Before modification, independent snapshots of formal source and tutorial
  candidate were saved under `Code/internal-validation/linear-three-mechanism-20260924/`.
  Historical five-term Fe results, the old optical-export comparison, and
  the older Berry colorbar receipt are retained there, not presented as the
  current public output contract.

## Source and numerical checks

Synthetic Conventional/Projector × dc/optical kernel comparisons showed
**16/16 exact array SHA matches** against the pre-change source: unchanged
Drude, quantum metric, and total, plus the new Berry-curvature array versus
the old `contact + hall_interband`. Focused source regression tests passed,
including native optical/dielectric names, strict DC readback, legacy/mixed
file rejection, three-term closure, and optical zero-frequency/DC matching.
The separate source gate status is recorded below; numerical parity alone
does not clear a publication gate.

The 14 Fe tasks ran serially with eight MPI ranks, one Julia thread per rank,
and nested BLAS/OpenMP disabled. The 46 selected native files were checked
against their private source SHA-256 receipts; the derived transport-equivalent
Berry table has a separate derivation hash. All values are finite. The new
results bind the response source, original TB, and original bundle in each
`summary.json` and in `manifests/results_manifest.json`.

| Check | Maximum residual or observation |
| --- | ---: |
| OAM `total − SRocc − CMocc` | `1.91×10⁻¹⁷ μB/cell` |
| Linear Transport three-mechanism closure | `1.49×10⁻⁸ S/m` |
| Linear Optical three-mechanism closure | `4.84×10⁻⁸ S/m` |
| Optical zero frequency versus DC total | `1.12×10⁻⁸ S/m` |
| Optical zero frequency versus DC by term | `3.73×10⁻⁸ S/m` |
| Berry `−berry_curvature/C` derived-field check | `4.55×10⁻¹²` |

Against the immediately preceding Fe candidate, all common unchanged
mechanisms and totals are numerically identical. The newly combined
Berry-curvature tables differ from the sum of the two historical decimal
tables by at most `1.31×10⁻¹⁰`, consistent with output rounding; there is
no unexpected physical-value change. This old/new comparison is recorded in
`manifests/fe_old_new_comparison.json`. The earlier Fe-model rerun comparison
remains private rollback evidence and is not a material qualification gate.

## Berry, bands, and figures

The SOS and transport-equivalent Berry paths use the same `200×200`
uncentered `ky=0` slice and `(v,u)→(u,v)` transpose. Their maximum pointwise
difference is `3143.1052`, with Pearson correlation `0.97518`; finite
`0.05 eV` relaxation in the transport-derived AHE channel means equality to
the static SOS map is not expected. Both newly rendered images use the report
style: Γ/H corners, green zero, signed-log-exponent color, `linthresh=1`, and
a fixed symmetric **±10⁴** colorbar. The transport-equivalent field has **0
negative and 0 positive clipped pixels** at that limit (SOS: also 0/0).
The [Berry presentation contract](examples/11_fe_oam_and_linear_response/plot_configs/berry_legacy_style_contract.json)
binds data and PNG/PDF hashes; changing display limits never changes the
numeric tables or physics qualification.

The unchanged VASP path table has `801×64` bands and the TB path table has
`801×18`; both use the same Γ–H–P–N–Γ coordinates and SCF Fermi energy.
The existing Γ consistency check is `0.000135 eV < 0.005 eV`.
The TB energy-set diagnostic in ±1 eV has RMS `0.009894 eV` and maximum
`0.055041 eV`; 202 path points retain degeneracy-cluster conflicts. This is
not a validated material fit. Ten Fe PNG/PDF figure pairs are hash-bound in
`FIGURE_SHA256.json`; response and Berry figures were regenerated from the
new tables, while the band figures remain tied to their unchanged tables.
All ten PDFs passed a one-page parse check; regenerated OAM, optical, and
both Berry PNG/PDF previews were visually inspected.

## Acceptance status

- Source: focused regressions, formatter, documentation, 734-file manifest,
  release whitelist, and **all seven required components PASS**: final Fast
  directly on the formal frozen source, five Full-only shards, and MPI-only.
  A separate byte-identical frozen-copy Fast also passed. The earlier
  all-in-one scheduler summary remains `FAIL` solely because macOS recreated
  `.DS_Store` during its Fast whitelist subcheck; it is preserved as an
  environmental failure, not presented as a passing aggregate run. The file
  was hash-quarantined, the final formal Fast whitelist passed, and the
  formal tree has no `.DS_Store` at final check.
- Fe: 14/14 calculations, 46 native source-file hashes, strict numerical
  validation, and both Berry presentation contracts **PASS**.
- Tutorial: 46-entry reference manifest, README/link, public-content,
  100-MiB file limit, and release-static checks **PASS**. In an independent
  moved copy, the hash-checked bundle archive installed and fresh-process
  12-chapter smoke returned `TUTORIAL_ALL_OK`, with 40 new summaries passing
  hash/finite checks. Six optional GeS spin cases were explicitly skipped
  because the separate spin asset is not installed. Chapter 12 offline
  readback passed at `MAX_ITERATIONS` without rerunning Wannierization.

The local optical-export/three-mechanism **engineering HOLD is cleared** by
the seven component source gates, 14-case rerun, and tutorial acceptance
above. This does not authorize GitHub publication or claim a public 1.1.0
tag. Fe's `MAX_ITERATIONS`, Physics HOLD, and Production ineligibility remain
unchanged.

## 2026-09-25 chapter 12 solver-to-bands addition

This is a separate, explicit Fe Wannierization lesson. It reuses the matching
local Fe VASP source files without rerunning VASP and selects the first
accepted-state export. The requested solver ceiling was 2500 total iterations;
the two stage-specific 1000-step caps ended the run at iteration 2000 with
`MAX_ITERATIONS`. The revised tutorial script does not auto-restart. A
continuation that had already started before that correction reached iteration
2001; its outputs are preserved privately but are **not** the selected model.
That abandoned continuation had a 5000-step ceiling but stopped at 2001;
no trajectory reached 5000 iterations.

The current v1.1.0 `SOURCE_MANIFEST.tsv` SHA-256 is
`5911b050475f86346f1023f8187311d78d7804d389fe047d526e8030d4921f01`;
all 735 listed source files matched their size and hash records at final
check. This differs from the earlier model-generation source identity, so no
new/old TB byte parity is claimed. The selected first-run TB SHA-256 is
`d1efec338cc5ff374f12b78b8b8f457f43b09d3d6d2daec3e83dcefac4a7b3e0`.
Independent readback found 18 WFs, a checkpoint with an accepted state, and
exactly Hamiltonian and position in the H/r bundle. The model is
`DIAGNOSTIC_ONLY / Physics HOLD / Production NOT_ELIGIBLE`.

The new `Band` calculation produced 801×18 values on Γ–H–P–N–Γ. Comparison
against the published 801×64 VASP table verified the same source POSCAR,
zero lattice difference, fractional path difference at most `4.17×10⁻¹⁷`,
distance difference at most `2.01×10⁻⁷ Å⁻¹`, and the common SCF reference
`5.7156290716733436 eV`. The many-to-one nearest-energy-set RMS within 1 eV
of that reference was `0.009811 eV`; this is descriptive, not a band-match or
material gate. The [public result receipt](examples/12_fe_wannierization/results/native_paw_2026-09-25/RESULT.json)
binds input, private-model, public table, and PNG hashes. The PDF generated
for local QA was withheld because its rendered negative ticks lost minus
glyphs; the checked PNG is the published figure.
