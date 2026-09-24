#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, ".."))
length(ARGS) >= 1 || error("usage: run_group.jl GROUP [--profile=smoke|reference]")
group_id = lpad(ARGS[1], 2, '0')
groups = sort(filter(name -> isdir(joinpath(ROOT, "examples", name)) && startswith(name, group_id * "_"), readdir(joinpath(ROOT, "examples"))))
length(groups) == 1 || error("unknown or ambiguous group $(ARGS[1])")
project = (startswith(only(groups), "10_") || startswith(only(groups), "11_") || startswith(only(groups), "12_")) ?
          get(ENV, "WANNIERNLQG_V110_PROJECT", ROOT) : ROOT
run(`$(Base.julia_cmd()) --project=$(project) $(joinpath(ROOT, "examples", only(groups), "run.jl")) $(ARGS[2:end])`)
