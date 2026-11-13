#!/usr/bin/env julia
using Dates, JSON3
include(joinpath(@__DIR__, "tutorial_input.jl"))
const ROOT = normpath(joinpath(@__DIR__, ".."))

"""Check chapter inputs or run one explicit case; smoke remains a test-fixture selection."""
function main(args)
    isempty(args) && error("usage: run_group.jl GROUP --check | --case=NAME [--output=NEW_DIR] [--data-paths=HOST.toml]")
    group_id = lpad(first(args), 2, '0')
    groups = filter(n -> startswith(n, group_id * "_") && isdir(joinpath(ROOT, "examples", n)), readdir(joinpath(ROOT, "examples")))
    length(groups) == 1 || error("unknown chapter: $group_id")
    profile = "reference"
    selected = nothing
    check = false
    output = nothing
    data_paths = nothing
    for arg in args[2:end]
        if startswith(arg, "--profile=")
            profile = split(arg, "="; limit=2)[2]
        elseif startswith(arg, "--case=")
            selected = split(arg, "="; limit=2)[2]
        elseif startswith(arg, "--output=")
            output = abspath(split(arg, "="; limit=2)[2])
        elseif startswith(arg, "--data-paths=")
            data_paths = split(arg, "="; limit=2)[2]
        elseif arg == "--check"
            check = true
        else
            error("unknown argument: $arg")
        end
    end
    profile in ("smoke", "reference") || error("profile must be reference or test-fixture smoke")
    !check && selected === nothing && error("Numerical execution requires --case=NAME. Check the inventory before selecting a case.")
    rows = JSON3.read(read(joinpath(ROOT, "manifests", "current_inputs.json"), String))
    cases = filter(r -> r.chapter == only(groups) && r.profile == profile && (selected === nothing || r.case == selected), rows)
    isempty(cases) && error("unknown case/profile")
    output === nothing && (output = joinpath(ROOT, ".runtime", "runs", Dates.format(now(), "yyyymmddTHHMMSS") * "-" * string(getpid()), only(groups)))
    !check && ispath(output) && error("fresh output directory required: $output")
    completed = 0
    unavailable = 0
    for row in cases
        path = joinpath(ROOT, row.input)
        missing = TutorialInput.missing_input_paths(path; data_paths)
        if check && !isempty(missing)
            unavailable += 1
            println("UNAVAILABLE_INPUT ", row.case, " ", join(missing, ", "))
            continue
        end
        command = check ? ["check", path] : ["run", path, joinpath(output, row.case)]
        data_paths === nothing || push!(command, "--data-paths=" * data_paths)
        try
            TutorialInput.main(command)
        catch e
            message = sprint(showerror, e)
            if check && occursin("FULL_DERIVATIVE_OVERLAP_REQUIRED", message)
                unavailable += 1
                println("UNAVAILABLE_INPUT ", row.case, " ", message)
                continue
            end
            rethrow()
        end
        completed += 1
    end
    println("TUTORIAL_GROUP_FINISHED group=", only(groups), " profile=", profile,
        " action=", check ? "check" : "run", " completed=", completed, " unavailable=", unavailable)
end
main(ARGS)
