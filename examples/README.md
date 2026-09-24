# Examples

The twelve chapters progress from band interpolation and integrated optical response to
momentum-resolved quantum geometry, v1.1.0 SHG, and Fe SOC OAM and linear response. Start with chapters 01, 02, 04, and 06. Chapters 03
and 05 require the optional spin asset; in chapter 09 only the two Zeeman cases require it.

Every case is independent:

```bash
julia --project=. examples/06_qg_pairwise/cases/quantum_metric_conventional.jl --profile=smoke
```

Group and repository runners preserve the same case configurations. `reference` is a fixed
tutorial profile, not a convergence or material-qualification claim.
Chapter 10 uses WannierNLQG v1.1.0 and is documented separately in its README.
Chapter 11 also uses a frozen v1.1.0 source. Its Fe bundle is optional for
cloning; the rerun's actual Wannierization status is in `MODEL_STATUS.json`,
and all Fe results remain diagnostic only with Physics on hold.
Chapter 12 keeps the supplied Fe Wannierization output as offline smoke evidence
and adds an explicit licensed solver-to-bands lesson. It does not add a response
reference case or treat Fe band agreement as material qualification.
