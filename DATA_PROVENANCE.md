# Data provenance, attribution and license scope

The selected set `tutorial-unified-GeS-Fe-20261109` contains one consistent GeS TB/operator pair and one Fe pair: four scientific files, four private bindings, 7,196,026,439 bytes. GeS is pairWS/canonical-spin034; Fe is U559/orbital-frame145. Both operators use mathematical model format 3.0. [Pair/frame evidence](manifests/material_consistency.json), [exact-array conversion](manifests/model_format_copy302.json) and [requirements](manifests/material_requirements.json) retain all original hashes and transformations.

## Approved data license and author

The user has confirmed self-generation and authority to authorize public distribution of both final material datasets, and has approved **CC BY 4.0** with data author **Zhuocheng Lu**. The grant and exact file scope are in [LICENSE_DATA.md](LICENSE_DATA.md); the data citation is [DATA_CITATION.cff](DATA_CITATION.cff). Family-specific notices accompany each archive and survive extraction. No dataset DOI or release date is invented. Archive metadata/text changes do not alter any model byte or imply a new material calculation.

| Material file | Technical source |
| --- | --- |
| `Materials/GeS/model_tb.dat` | full010 pair-WS H/r, 32 orbitals / 465 R |
| `Materials/GeS/operators.h5` | parent010 orbital data with canonical periodic-link spin034 replacement; exact-array format 3 copy302, 55 components / 11 classes |
| `Materials/Fe/model_tb.dat` | U559/profile-wide001 H/r, 18 orbitals / 1115 R |
| `Materials/Fe/operators.h5` | once-only orbital-frame145 transformation, exact-array format 3 copy302, 31 components / seven classes |

The code's existing [GPL-2.0-only license](LICENSE) is unchanged. The material-data grant is not a blanket license for every tutorial file, result or figure and does not change the software/paper author lists. Software and relevant method citations remain appropriate to the calculations actually performed, without adding conditions beyond the data license.

## Third-party THG reference

The current THG comparison retains the independently redrawn 122-node approximation extracted from the published PDF vector path of F. Hipólito, Alireza Taghizadeh and T. G. Pedersen, *Physical Review B* 98, 205420 (2018), [DOI 10.1103/PhysRevB.98.205420](https://doi.org/10.1103/PhysRevB.98.205420), Fig. 3(a). It is not an author-supplied raw array or an independent recomputation of that paper. The numerical files, source calibration and published-figure identity remain unchanged.

This third-party reference and its contribution to the composite figure are **excluded from the GeS/Fe CC BY 4.0 grant**. The user-approved treatment retains the comparison with citation, figure identification, digitization limitations and this exclusion. No publisher permission is claimed, and the absence of a visible open-license notice is not treated as proof that every extracted factual number needs permission. Applicable terms or exceptions depend on the actual reuse. [Detailed attribution and source links](THIRD_PARTY_REFERENCES.md).

## Reproduction and publication boundaries

Each chapter's `reproduce.json` and the [case sources](manifests/material_case_results.json) distinguish actual recomputation from reuse. The source/archive/format changes retain original evidence and failures. Chapter 12's native Wannier model is an output of its separate producer workflow, not a second canonical Fe input. Its five raw same-calculation VASP prerequisites remain user-supplied; VASP programs/source, POTCAR/PP databases, WAVECAR, vaspout.h5 and unrelated raw outputs are not in these response-model assets. User-generated runtime matrices are not classified as prohibited merely because VASP was used upstream; see the [official FAQ](https://vasp.at/info/faq/).

The licensed archives and local incremental install are prepared without a public upload. Exact identities, notices and local checks are in the [distribution](manifests/material_distribution.json) and [licensing record](manifests/material_licensing420.json). Original 415 packages/manifests and all failed preparation records remain retained separately. New metadata changes archive hashes but preserves all four scientific hashes. No new integration, SCF or Wannierization is implied, and scientific limits remain independent of licensing. GitHub submission and publication await the user's next confirmation.
