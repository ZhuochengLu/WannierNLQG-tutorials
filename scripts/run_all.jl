#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, ".."))
groups = sort(filter(name -> occursin(r"^\d\d_", name) && isdir(joinpath(ROOT, "examples", name)), readdir(joinpath(ROOT, "examples"))))
for group in groups
    project = (startswith(group, "10_") || startswith(group, "11_") || startswith(group, "12_")) ?
              get(ENV, "WANNIERNLQG_V110_PROJECT", ROOT) : ROOT
    run(`$(Base.julia_cmd()) --project=$(project) $(joinpath(ROOT, "examples", group, "run.jl")) $(ARGS)`)
end
println("TUTORIAL_ALL_OK groups=$(length(groups))")
