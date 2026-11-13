# Tutorials 1.2.0: review before GitHub submission

**The local candidate is prepared for user review. GitHub submission and public publication have not been authorized or performed.**

| Item | Actual status | Scope and evidence |
| --- | --- | --- |
| Unified GeS/Fe models | PASS | Exactly four format 3.0 files, 7,196,026,439 bytes; the 97 material inputs use one pair per material. [Requirements](manifests/material_requirements.json). |
| Data authority, license and credit | APPLIED | User-confirmed self-generation/distribution authority; CC BY 4.0, Zhuocheng Lu. Code GPL-2.0-only and software/paper author lists unchanged. [License](LICENSE_DATA.md), [data citation](DATA_CITATION.cff). |
| Licensed archives and local installation | PASS | Two archives total 351,451,536 bytes; scientific payload unchanged, four new notices checked, local acquisition/reconstruction/extraction into an absent root passed. [Identities](Materials/ASSETS.md), [incremental evidence](manifests/material_licensing420.json). |
| Existing complete reader and input checks | REUSED PASS, engineering only | Actual public 8311…/Julia 1.13.0 complete-reader checks (GeS 55/11, Fe 31/7) and 154 ordinary-input parses. No repeat for licensing. [Original evidence](manifests/release_preparation414.json). |
| Representative response/read/plot chain | COMPLETED WITH PRESERVED WRAPPER FAILURE | Actual installed-data GeS spin injection and Fe OAM children exit0; Fe public readback and independent postread/plots passed. Parent417 column assertion remains failed; no repeated integral. [Exact record](manifests/installed_material_smoke419.json). |
| THG third-party curve | APPROVED HANDLING APPLIED | 122-point PDF-vector digitization, Fig.3(a), accurately attributed and excluded from the GeS/Fe license. No publisher permission is claimed. [Notice](THIRD_PARTY_REFERENCES.md). |
| Software/data CFF | PASS | Version 1.2.0; four CFFs validated against official 1.2.0 schema. No invented dataset DOI or publication date. Software contributor identity and dataset author remain distinct. |
| New public asset download | NOT RUN | New URLs remain unset; local file acquisition is not a GitHub download. |
| Git submission, remote CI, tag, Release, upload | NOT RUN | Explicitly waiting for the user's next GitHub confirmation. No commit or staging done here. |

## Scientific boundaries retained

The current results and case identities are preserved, including the confirmed shift-current band domain, grouping and full intermediate sums, and the position-defined QHC method scope. Chapter 05's allowed channels and eight final bindings, Chapter 12's completed native/reference workflow and 23 checks, and Chapter 16's adopted 30/10/1 meV 84-point results are not replaced by licensing work.

Chapter 12 Z remains unconverged and overall material qualification is not established. THG retains its six finite valley regions, original BZ weights, budget terminations, expression differences and paper-prescription/digitization/normalization limits. Its 12 independently refined reused points do not prove convergence of the other 72 points or the full BZ.

GeS jerk xxxx remains grid sensitive: the original five-frequency comparison gives 8.5641% for 200→300 and 2.2713% for 300→400, above its original 1% criterion. yyyy gives 0.9910% and 0.2555% at those tested points. The user does not require xxxx convergence for release; this is a disclosed scientific limitation, not a release gate. No new convergence run or threshold change is planned. [Unchanged record](manifests/jerk_grid_review414.json).

## Source and verification identities

Actual material/THG results retain public `725ed8e66c2429c94bf299a5db38343ee39ba8b94d3c7fb0f35de6dae791d230` or their recorded per-case source. The later `63d952…` revision changes 12 documentation/theory files; current public `8311ffc1ceda424088a959bfe374ad1a855aa9c5ccc9786422582f4ab212efd0` adds cold invalid-input validation, tests and documentation without changing numerical kernels, dependencies, operators or model format. Old Full904/905/908 evidence belongs to 725; targeted 924 evidence belongs to 8311. Neither is relabeled by this package update. [Software record](manifests/software_validation.json).

The original 415 preparation read complete installed bundles and parsed inputs, without response calculations. Later 417/418 added the representative real response/read/plot chain. The present 420 update adds only approved notice/citation texts, archive metadata and scope documentation: root0, execution/resource PASS, four original identities freshly native GONE, own 3 CPU / 4 GiB allocation closed, external reservations preserved. Scientific qualification remains NOT_EVALUATED and kernel containment UNKNOWN.

## Candidate and future publication steps

The tutorial has its own Git root. HEAD `96d2690ecd1de196cc2c4c4b33d65b98df28b1de` is the September baseline, not this uncommitted 1.2.0 candidate. The previous local reachable-history/payload and remote tag/Release review is retained with its recorded observation time and bounded scan scope. No history rewrite or fresh remote-CI result is inferred. [Prior review](manifests/release_review416.json), [current candidate](manifests/release_candidate420.json).

After the user explicitly confirms GitHub submission, review and commit the exact selected tutorial payload, run the applicable remote checks and publish only the approved versioned assets/tag/Release steps. Pin and review the resulting immutable asset URLs, then test the real public download chain. Public downloads cannot be verified before those assets exist. The WN source owner's CFF/date review is coordinated separately and does not authorize changes to that repository here. No new publication date is asserted by this local candidate.
