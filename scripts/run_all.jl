#!/usr/bin/env julia
"""Check the current chapter inventory; numerical runs select one TOML/case explicitly."""
const ROOT = normpath(joinpath(@__DIR__, ".."))
all(arg -> startswith(arg, "--data-paths=") || startswith(arg, "--profile=") || arg == "--check", ARGS) ||
    error("run_all.jl is an input check. Use run_group.jl GROUP --case=NAME for numerical execution.")
for chapter in sort(filter(x -> occursin(r"^\d\d_", x), readdir(joinpath(ROOT, "examples"))))
    command = [joinpath(ROOT, "scripts", "run_group.jl"), chapter[1:2], "--check", ARGS...]
    run(`$(Base.julia_cmd()) --startup-file=no --compiled-modules=existing --project=$(dirname(Base.active_project())) $command`)
end
println("TUTORIAL_ALL_INPUT_CHECKS_FINISHED")
