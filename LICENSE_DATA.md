# License for the GeS and Fe material datasets

Copyright (c) 2026 Zhuocheng Lu.

The original numerical datasets listed below are licensed under the **Creative Commons Attribution 4.0 International Public License (CC BY 4.0)** by Zhuocheng Lu.

- License URI: https://creativecommons.org/licenses/by/4.0/
- Legal code: https://creativecommons.org/licenses/by/4.0/legalcode
- Source: https://github.com/ZhuochengLu/WannierNLQG-tutorials
- Dataset citation: [DATA_CITATION.cff](DATA_CITATION.cff), version 1.2.0.

The license permits sharing and adaptation under its terms, including appropriate credit, a license link and an indication of changes. This notice adds no restriction to those terms and does not imply endorsement. A suggested credit is: “Zhuocheng Lu, Unified GeS and Fe model and real-space operator datasets for WannierNLQG Tutorials, version 1.2.0, CC BY 4.0,” with the source and license links. Attribution should be adapted appropriately if the data are modified.

## Exact numerical scope

| Logical file | Bytes | SHA-256 |
| --- | ---: | --- |
| `Materials/GeS/model_tb.dat` | 94298181 | `2808baa3ba824f0045b8baf989950bbc157ab145a550cb5c9ae2acc66fd2bab2` |
| `Materials/GeS/operators.h5` | 4024659779 | `0071f31d8b452d3187d3ee8c306a7195dcd3eb98e8beb1c64c9768ac22446661` |
| `Materials/Fe/model_tb.dat` | 71573382 | `5efdff9a7a854342bf44218d01d622d9c9845a386c65019cc571e6d33e011149` |
| `Materials/Fe/operators.h5` | 3005495097 | `7a2c6868ef3d4bc47c1321084db430ed6093a2eddb4b4b0586a8cb2b100d5e51` |

The selected GeS data retain full010 pair-WS H/r/orbital operators and the canonical spin034 replacement. Fe retains the U559/profile-wide001 H/r pair with the once-only orbital-frame145 transformation. Both operator files are exact-array mathematical format 3.0 copies302. Numerical provenance and the source/format transformations remain recorded in the manifests; this licensing step does not change any numerical value or imply scientific convergence.

The two separately distributed archives carry family-specific copies of this notice and dataset citation. The data author has confirmed self-generation and authority to authorize public distribution. There is no new publication date or dataset DOI claim.

## Other material

This data license does not replace the tutorial/software code's GPL-2.0-only license. It applies to the four identified material numerical files and accompanying project-created dataset notices; it does not relicense every tutorial result or figure.

The third-party Fig.3(a) reference from Hipólito, Taghizadeh and Pedersen, PRB 98, 205420(2018), DOI 10.1103/PhysRevB.98.205420, including its 122-point digitization and reference contribution to the THG comparison, is **excluded**. See [THIRD_PARTY_REFERENCES.md](THIRD_PARTY_REFERENCES.md). No publisher permission is asserted by this license.

Software and method papers should be cited as appropriate for research use. Those recommendations do not add conditions beyond CC BY 4.0.
