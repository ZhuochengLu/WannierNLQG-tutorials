#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, ".."))
run(`$(Base.julia_cmd()) --project=$(dirname(Base.active_project())) $(joinpath(ROOT, "scripts", "run_all.jl")) --profile=smoke`)
