# Installing the unified GeS and Fe material data

The 154-input suite contains 97 material inputs (54 reference, 43 smoke). They use exactly four logical model files and four bindings: one GeS pair and one Fe pair, 7,196,026,439 scientific bytes. Models/operators are format 3.0 copies with retained physical-array provenance; see [asset identities](ASSETS.md), [requirements](../manifests/material_requirements.json) and [data citation](../DATA_CITATION.cff).

The material numerical files are licensed **CC BY 4.0** by **Zhuocheng Lu**. Each family archive includes `LICENSE_DATA.md` and `DATA_CITATION.cff` beside its two model files. The license does not include tutorial code or third-party paper references. [Exact license scope](../LICENSE_DATA.md).

## Acquire, verify and install

Fetch the versioned release assets using their pinned HTTPS URLs. The helper never substitutes a historical release or a latest alias. Use new download and installation paths:

```bash
python scripts/fetch_material_assets.py fetch --downloads /path/to/new-downloads
python scripts/fetch_material_assets.py install --downloads /path/to/new-downloads --destination /path/to/new-material-root --write-bindings /path/to/new-private-bindings.toml
python scripts/install_material_assets.py --assets-root /path/to/new-material-root
julia --project=.runtime/env scripts/run_group.jl 01 --check --data-paths=/path/to/new-private-bindings.toml
```

The fetch command uses only the pinned HTTPS URLs from [material_distribution.json](../manifests/material_distribution.json). Parts are checked before ordered reconstruction, the reconstructed archive and exact allowed member list are checked, and every extracted scientific/notice file is hash checked. Extraction rejects paths/links/duplicates/unexpected members. Existing installation roots and mismatching downloads are not overwritten. The final archives are below 2 GiB, so no physical split is required; the split path has independent tiny controls.

Four scientific files are checked by the original installer before it writes a new private bindings file. The licensed archives also extract four small notice/citation files; these are not additional numerical requirements. Bindings are host-local paths only and do not change parameters. [Manual binding example](paths.example.toml). Missing models must report `UNAVAILABLE_INPUT`, not load an unrelated file. Old equal-size/filename models are not substitutes.

## Existing representative smoke paths

```bash
julia --project=.runtime/env scripts/run_group.jl 03 --profile=smoke --case=injection_spin_current_conventional --output=.runtime/installed-ges-smoke --data-paths=/path/to/new-private-bindings.toml
julia --project=.runtime/env scripts/run_group.jl 11 --profile=smoke --case=oam_conventional_T000 --output=.runtime/installed-fe-smoke --data-paths=/path/to/new-private-bindings.toml
```

These exact tiny configurations have actual public 8311… execution evidence with the same scientific payload: both numerical children exited 0; Fe formal output readback passed; independent original-output postread/plots passed. The original 417 wrapper column failure remains failed and was not fixed by rerunning responses. [Execution record](../manifests/installed_material_smoke419.json). This is a representative local engineering chain, not convergence or all-material scientific acceptance. Source identities and unchanged-payload applicability are kept separate from package/license revision.

Chapter 12's native workflow additionally needs its own five user-supplied VASP inputs and generates a new model; those raw inputs are outside this runtime-data set. Figure redraws use chapter small tables and need no full model assets. These historical local checks do not establish a fresh-machine dependency installation. To fetch from a separately copied, verified archive directory, add `--source-dir /path/to/verified-archives` to the fetch command.
