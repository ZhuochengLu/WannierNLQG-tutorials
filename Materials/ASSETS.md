# Versioned unified material assets

The final set contains exactly one GeS Hamiltonian/operator pair and one Fe pair. Dataset author: **Zhuocheng Lu**. The numerical files are licensed **CC BY 4.0**; see [license scope](../LICENSE_DATA.md) and [data citation](../DATA_CITATION.cff). Tutorial code remains GPL-2.0-only. Third-party paper references are excluded from the material-data license.

## Prepared archives

| Archive | Compressed bytes | SHA-256 |
| --- | ---: | --- |
| `tutorial-data-1.2.0-GeS-model3.tar.gz` | 156,565,555 | `6b34ed999eeb8042facae7bef4a57d00af76c1c7bebc9aa8d26d3eac010ea3d3` |
| `tutorial-data-1.2.0-Fe-model3.tar.gz` | 194,885,981 | `e0a1ff9af845e50f682c8de9c9ccd2e034505ea262d421b6ac2fd12cfd9ef43b` |

The two archives total **351,451,536 bytes**. Each contains two scientific files plus its family-specific `LICENSE_DATA.md` and `DATA_CITATION.cff`. Their exact allowed member names, bytes and hashes are in [material_distribution.json](../manifests/material_distribution.json). Each archive is below 2 GiB, so no physical split is needed. The single part has the same size/hash as its archive; future split parts must be reconstructed in the manifest order and verified before extraction. The existing split-path controls use independent tiny fixtures.

Acquisition uses the versioned release URLs pinned in [material_distribution.json](../manifests/material_distribution.json). An old asset with the same material name is not a substitute. Follow [the acquisition instructions](README.md); the helper checks part/archive/member hashes and rejects unsafe or unexpected members and existing installation roots.

## Scientific payload

| Logical file | Bytes | SHA-256 |
| --- | ---: | --- |
| `Materials/GeS/model_tb.dat` | 94,298,181 | `2808baa3ba824f0045b8baf989950bbc157ab145a550cb5c9ae2acc66fd2bab2` |
| `Materials/GeS/operators.h5` | 4,024,659,779 | `0071f31d8b452d3187d3ee8c306a7195dcd3eb98e8beb1c64c9768ac22446661` |
| `Materials/Fe/model_tb.dat` | 71,573,382 | `5efdff9a7a854342bf44218d01d622d9c9845a386c65019cc571e6d33e011149` |
| `Materials/Fe/operators.h5` | 3,005,495,097 | `7a2c6868ef3d4bc47c1321084db430ed6093a2eddb4b4b0586a8cb2b100d5e51` |

These four files total **7,196,026,439 bytes**. GeS uses the full010 pair-WS H/r data, canonical spin034 replacement and exact-array model-format 3.0 copy302. Fe uses U559/profile-wide001 H/r, the once-only orbital-frame145 transformation and exact-array copy302. All four hashes are unchanged by licensing and repacking. [Pair/frame verification](../manifests/material_consistency.json), [format-copy verification](../manifests/model_format_copy302.json), [requirements and bindings](../manifests/material_requirements.json).

The GeS reader covers 32 orbitals, 465 R vectors and 55 components in 11 operator classes. Fe covers 18 orbitals, 1115 R vectors and 31 components in seven classes; this does not assert a complete Fe spin-operator set. Chapter 12's native output model is a separate producer example, not a second canonical Fe input. Its raw VASP prerequisites are not distributed in these response-model packages.

## Verification and applicability

The original 415 packages and their preparation records are preserved. Their complete-reader and 154-input checks, followed by actual installed-data representative GeS/Fe smoke calculations and original-output read/plots, remain applicable to the unchanged scientific payload. [Existing checks](../CHECKS.md), [representative execution](../manifests/installed_material_smoke419.json).

The licensed revision separately verified both new archives, all four unchanged scientific hashes and four notice/citation hashes through local acquisition and an absent-root installation. It ran no response, model reader or full input suite. [Incremental licensing checks](../manifests/material_licensing420.json). Local installation is distinct from a new public URL download, fresh-machine environment installation or material scientific acceptance. Keep the installed notices with the data and indicate modifications as required by CC BY 4.0.
