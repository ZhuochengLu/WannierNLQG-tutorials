# Tutorial provenance follow-up

This follow-up extends the retained [315 inventory](all_case_provenance315.json). It covers all 86 reference cases and 71 smoke inputs. Current adopted public 1.2.0 has source manifest `725ed8e66c2429c94bf299a5db38343ee39ba8b94d3c7fb0f35de6dae791d230`. Historical source identities keep their original hash domains.

| Reference classification | Cases |
|---|---:|
| Actual calculation recorded | 56 |
| Existing result supported by evidence | 30 |
| Further normal-result validation pending | 0 |

This phase completed 34 reference cases at their existing meshes and recovered sufficient source/input/data/selected-path evidence for 12 other cases. Another 1 selected Hall display has an explicitly bounded model-specific reuse scope rather than a new full-axis execution. It did not start a new SCF, Wannier optimization, mesh-convergence scan or WN source repair. The 71 smoke inputs retain their individual parsing/history records; current reference calculations do not count as smoke execution.

## New computations and retained results

- Chapters 01/12: both normal band inputs ran on the unified GeS/Fe TB. Fe matches its old native table byte-for-byte. GeS uses its actual new energies and existing fixed energy reference; historical comparison data remain historical.
- Chapter 13: all nine original Haldane calculations ran. Real-space and analytic routes satisfy the original Hall/plateau/mesh checks. Independent Chern and model data retain their own source.
- Chapter 14: all ten original Rice–Mele calculations ran. Route, inversion reversal, forbidden controls, independent equation-21 and original mesh checks retain their separate numerical meanings; no fitted scale was applied.
- Chapter 15: current executed cases are individually identified. The failed full-axis Hall mesh accuracy test is preserved. A model-specific eta applicability bound is recorded separately; it is not called an executed full-axis spectrum.
- Chapter 16: both original121×121/126-energy THG inputs ran using supported `distribution_broadening`, intermediate eta=.001 and eta correction. The two reference inputs and two smoke files now make those already-executed defaults explicit. The new spectra/low-frequency figures correspond to those runs. Old61/181 causal datasets and figures remain historical; the removed causal prescription is not silently restored or relabelled.
- Chapter 04 selected injection map and eleven non-OM Fe cases: producer seals, exact source or inventory domain, model/array frame and selected response paths were recovered. They need no new integral. The Fe eight linear kernels retain their selected arithmetic; the two drifted retained files are tests, not production kernels.

## Remaining normal-result scope

No reference source-applicability gap remains in this inventory.

## Boundaries and reproducibility

Native tensors, deterministic display transforms, exact input/source hashes and individual call-path reviews are distinguished in [the JSON](all_case_provenance334.json) and [flat list](all_case_provenance334.csv). The selected-path reuse proof and Dirac-only bound are included in `retained-source-records/followup334`. Resource-stop and other failed attempts remain in the external task evidence; none is upgraded to a successful execution. Material band accuracy, finite-square effects and scientific qualification retain their stated limits.

Old scientific data, source snapshots and images are retained in the verified external archive and the per-change adoption backup. No GitHub upload or push was performed.
