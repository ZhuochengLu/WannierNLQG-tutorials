# WannierNLQG Tutorials v1.2.0

This release expands the tutorial collection from 12 to 17 chapters and introduces unified material datasets, updated examples, and reproducible plotting workflows.

## Highlights

- Five new chapters cover the Haldane model, the Rice–Mele model, the Dirac model, third-harmonic generation in graphene, and jerk current.
- The Fe Wannierization tutorial presents input preparation, model construction, and band-structure comparison.
- The Fe and GeS examples use consistent Hamiltonian and operator datasets in model format 3.0.
- Updated examples and figures illustrate optical responses, transport, orbital magnetization, and quantum geometry.

## Getting started

Use this release with WannierNLQG 1.2. Follow the [repository instructions](README.md) to set up the tutorial environment and run an example.

The Fe and GeS material examples require their respective data packages. See the [material-data guide](Materials/README.md) and [asset identities](Materials/ASSETS.md) for acquisition, installation, and checksum verification. The versioned archives are [`tutorial-data-1.2.0-GeS-model3.tar.gz`](https://github.com/ZhuochengLu/WannierNLQG-tutorials/releases/download/v1.2.0/tutorial-data-1.2.0-GeS-model3.tar.gz) and [`tutorial-data-1.2.0-Fe-model3.tar.gz`](https://github.com/ZhuochengLu/WannierNLQG-tutorials/releases/download/v1.2.0/tutorial-data-1.2.0-Fe-model3.tar.gz). Previously distributed Fe and GeS datasets are not interchangeable with the new model and operator pairs.

The unified numerical datasets are licensed [CC BY 4.0](LICENSE_DATA.md), with data attribution to **Zhuocheng Lu**. Tutorial code remains [GPL-2.0-only](LICENSE); [third-party literature references](THIRD_PARTY_REFERENCES.md) are outside the material-data license.

## Corrections and changes

- Shift-current comparisons use consistent calculation settings and the corresponding method conventions.
- Quantum Hermitian connection and shift-vector examples have been updated to reflect the supported formulations.
- Tutorial inputs, result tables, plotting scripts, and figures are organized within their respective example directories.

## Notes on the examples

The [Fe Wannierization example](examples/12_fe_wannierization/README.md) illustrates the full workflow; its recorded Z stage did not reach the specified tolerance and does not establish complete material qualification. The [graphene third-harmonic example](examples/16_monolayer_graphene_thg/README.md) uses 30/10/1 meV resonance/low-frequency/intermediate widths over a finite valley domain; budget terminations, differences between the two expressions and the paper prescription, and lack of full-spectrum convergence remain disclosed. The [GeS jerk-current example](examples/17_jerk_current/README.md) retains its measured grid sensitivity, without claiming convergence of the xxxx channel.

See the [individual tutorials](README.md#chapters), [data provenance](DATA_PROVENANCE.md), [checks](CHECKS.md), and [release review](RELEASE_REVIEW.md) for calculation details, references, and checksums.
