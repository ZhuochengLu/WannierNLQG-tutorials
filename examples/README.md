# Examples

The nine chapters progress from band interpolation and integrated optical response to
momentum-resolved quantum geometry. Start with chapters 01, 02, 04, and 06. Chapters 03
and 05 require the optional spin asset; in chapter 09 only the two Zeeman cases require it.

Every case is independent:

```bash
julia --project=. examples/06_qg_pairwise/cases/quantum_metric_conventional.jl --profile=smoke
```

Group and repository runners preserve the same case configurations. `reference` is a fixed
tutorial profile, not a convergence or material-qualification claim.
