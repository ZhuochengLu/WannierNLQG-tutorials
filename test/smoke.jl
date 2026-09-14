#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, ".."))
run(`$(Base.julia_cmd()) --project=$(ROOT) $(joinpath(ROOT, "scripts", "run_all.jl")) --profile=smoke`)
