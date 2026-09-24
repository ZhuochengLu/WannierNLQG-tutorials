#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, "..", ".."))
const ACTIVE_PROJECT = Base.active_project()
ACTIVE_PROJECT === nothing && error("start Julia with --project pointing to WannierNLQG v1.1.0")
run(`$(Base.julia_cmd()) --project=$(dirname(ACTIVE_PROJECT)) $(joinpath(@__DIR__, "cases", "second_harmonic_generation_conventional.jl")) $(ARGS)`)
println("TUTORIAL_GROUP_OK group=10_second_harmonic_generation")
