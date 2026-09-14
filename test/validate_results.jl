#!/usr/bin/env julia
using JSON3
const ROOT = normpath(joinpath(@__DIR__, ".."))
profile = isempty(ARGS) ? "reference" : only(ARGS)
summaries = String[]
for (directory, _, files) in walkdir(joinpath(ROOT, "examples"))
    if "summary.json" in files && occursin(joinpath("results", profile), directory)
        push!(summaries, joinpath(directory, "summary.json"))
    end
end
expected = profile == "reference" ? 31 : 25
length(summaries) >= expected || error("expected at least $(expected) summaries, found $(length(summaries))")
for path in summaries
    summary = JSON3.read(read(path, String))
    Bool(summary.finite_values) || error("non-finite result recorded in $(path)")
    String(summary.package_version) == "1.0.1" || error("wrong package version in $(path)")
    String(summary.qualification) == "TUTORIAL_NUMERICAL_EVIDENCE" || error("wrong qualification")
end
println("RESULTS_OK profile=$(profile) summaries=$(length(summaries))")
