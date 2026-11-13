# Tutorial case provenance audit

This inventory covers all 86 reference cases and 71 smoke inputs in the 17 chapters. It extends the family-scoped `case_update313.json` (35 reference cases and 32 smoke inputs); that earlier record is retained unchanged. No numerical calculation was launched for this audit.

The adopted public software is 1.2.0, source manifest `725ed8e66c2429c94bf299a5db38343ee39ba8b94d3c7fb0f35de6dae791d230`. A historical result retains its actual calculation source. Adoption, configuration parsing, result reading and response execution are separate events.

| Profile | Targeted recomputation already completed | Reuse supported by evidence | Provenance/applicability not fully closed | Total |
|---|---:|---:|---:|---:|
| Reference | 22 | 17 | 47 | 86 |
| Smoke numerical execution | 0 | 0 | 71 | 71 |

These are numerical-provenance categories. All smoke inputs have earlier configuration-check coverage; 63 also have a located historical numerical summary. Current input bytes, model binding and selected numerical branch have not been closed against those old smoke runs. The other eight have no located numerical smoke summary. Neither a reference run nor a parse-only check is counted as a current smoke response. Static TOML and repository checks are reported separately.

An incomplete chain is not evidence of an erroneous result and is not a request to rerun it. First recover the missing source/input/model/producer link or perform an appropriate bounded comparison. Only a demonstrated change reaching the selected numerical behavior, or a necessary bounded validation, justifies execution. Missing records and changed version hashes alone do not.

## Completed recomputations

- Chapters 02 and 04: four shift-current methods in each chapter; chapter 08: two QHC and two shift-vector methods. These 12 reference results were calculated on source `8842d664…`; selected response kernels remain unchanged in the adopted source. Full transition selection keeps complete intermediate states. Geometric-Loop QHC is not an active case.
- Chapters 03 and 05: four spin-current references; chapter 11: four orbital-magnetization references. All eight original-mesh calculations ran on `59c11486…`. Four Fe results were subsequently reread with the repaired current reader; the integrals were not repeated.
- Chapter 17: `two_band_tb` and `two_band_analytic` ran on `4dc1d191…` with the current 129-point, five-energy inputs. Complete tables matched the retained comparison byte-for-byte.

## Evidence supporting reuse

- Chapters 06 and 07: nine zero-eta Conventional/internal geometry references, actual source `f2780d1f…`. Selected response/interpolation arithmetic is preserved; model audit233 binds the consumed H/r arrays exactly to the unified material representation. Later metric-only delegates and Geometric-Loop QHC retirement do not reach these paths.
- Chapter 02 integral injection current; all four chapter 09 references; chapter 10 orthogonal SHG: six retained center/operator-frame results, actual sources `7b3cbe71…` / `90e8fe93…`. Input/raw-data identities are recorded. Positive-eta injection/HCT/triple/Zeeman functions retain their selected arithmetic; Zeeman uses the preserved S matrices. SHG changes affect the optional nonorthogonal cutoff path; ordinary orthogonal arithmetic is retained.
- Chapter 17: two original GeS 35-point/two-energy, T=0 references, actual source `ccabbdcd…`. The later positive-temperature occupation repair does not alter this boundary; the existing two-route control is retained.

Reuse supports the stated calculation scope, not material convergence or independent physical qualification.

## Reference cases with an explicit remaining gap

| Chapter | Cases | Gap to resolve first |
|---|---:|---|
| 01 | 1 | Producing code/input for the selected audited DFT/TB common-path plot is not fully bound to the ordinary band input. |
| 04 | 1 | The selected injection-current display is a derived selected-band artifact; its precise producer/transformation is not bound by the older center-frame summary alone. |
| 11 | 11 | Non-OM cases: Fe inventory93c is a separate hash domain; old inventory/source closure or exact selected Berry-model/entry closure is incomplete. |
| 12 | 1 | Fe inventory/source and selected audited band-path producer are not fully closed. |
| 13 | 9 | Historical c9de digest/source snapshot unresolved. These are finite-rate linear-transport cases, not the new intrinsic-AHC route. |
| 14 | 10 | Historical c9de source snapshot and post-change selected-route closure unresolved; model-file hashes survive. |
| 15 | 12 | Exact old source d0a/f77 located. Producer/planning changes and the shared current DCModel versus the old optical DiracModel constructor still need an equivalence chain. |
| 16 | 2 | Exact old source d0a/f77 located. Later THG geometry/R-Q decomposition/cache changes need a complete selected-result equivalence check; deleting an unused threshold does not establish this. |

The full case names and individual gaps follow below and in the machine-readable JSON/CSV.

- **01_band_structure**: `band_structure`.
- **04_kslice_charge_responses**: `injection_current_conventional`.
- **11_fe_oam_and_linear_response**: `berry_sos_occupied_xy`, `berry_tb_occupied_xy`, `berry_transport_equivalent_xy`, `linear_optical_conventional_T000`, `linear_optical_conventional_T300`, `linear_optical_projector_T000`, `linear_optical_projector_T300`, `linear_transport_conventional_T000`, `linear_transport_conventional_T300`, `linear_transport_projector_T000`, `linear_transport_projector_T300`.
- **12_fe_wannierization**: `fe_bands`.
- **13_haldane_anomalous_hall**: `analytic_reversed`, `analytic_topological`, `analytic_trivial`, `tb_reversed`, `tb_topological`, `tb_topological_n121_g001`, `tb_topological_n181_g002`, `tb_topological_n61_g002`, `tb_trivial`.
- **14_rice_mele_shift_current**: `analytic_ionic`, `analytic_polar`, `analytic_reversed`, `analytic_ssh`, `tb_ionic`, `tb_polar`, `tb_polar_n1601`, `tb_polar_n401`, `tb_reversed`, `tb_ssh`.
- **15_nonperiodic_dirac_response**: `hall_negative`, `hall_positive`, `hall_positive_g0001`, `hall_positive_n9601`, `optical_negative`, `optical_positive`, `optical_positive_g001`, `optical_positive_k025`, `optical_positive_k050`, `optical_positive_k200`, `optical_positive_n201`, `optical_positive_n801`.
- **16_monolayer_graphene_thg**: `T10`, `T300`.

## Source and execution boundaries

Eight retained calculation snapshots were checked against every payload in their SOURCE_MANIFEST files. Some older records use a field named `source_manifest_sha256` for a SHA256SUMS digest. The THG/Dirac snapshot was recovered through that domain: SHA256SUMS `f77e56f3…`, SOURCE_MANIFEST `d0a7513b…`. Inventory `93c862fd…` remains a different historical domain; it is not silently relabelled as a manifest hash. Unresolved identities remain unresolved.

Per-case records contain current input SHA, task/sampling/model settings, retained record/data hashes, historical source identities with their hash domains, static typed call-path references, production-change assessment and a specific next action. Current static route files are hashed; this is not a captured historical dynamic stack.

Chapter 17 also contains a separate dense 200-energy, 257-point, eta=1e-5 figure. The five-energy reference297 execution did not regenerate that figure. Audited common-path band figures in chapters 01/12 similarly have their own producer contracts. Aggregate plot-recipe provenance can cover several cases and is not itself proof that every current input produced every plotted table.

Historical failed roots, material warnings, missing qualification and incomplete containment claims remain unchanged. Schema2-to3 model copies preserve numeric payloads and originals; a format-label or reader-only change is not a new material calculation. No source kernel was edited, no new SCF/Wannierization/convergence scan was run, and nothing was uploaded or pushed.

## Audit files

- [Complete 157-input provenance inventory](all_case_provenance315.json)
- [Flat case list](all_case_provenance315.csv)
- [Earlier family-scoped update](case_update313.json)
