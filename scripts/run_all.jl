#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, ".."))
groups = sort(filter(name -> occursin(r"^\d\d_", name) && isdir(joinpath(ROOT, "examples", name)), readdir(joinpath(ROOT, "examples"))))
for group in groups
    run(`$(Base.julia_cmd()) --project=$(ROOT) $(joinpath(ROOT, "examples", group, "run.jl")) $(ARGS)`)
end
println("TUTORIAL_ALL_OK groups=$(length(groups))")
