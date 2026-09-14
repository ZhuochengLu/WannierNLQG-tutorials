#!/usr/bin/env julia
    isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "ExampleSupport.jl"))
    profile = Main.ExampleSupport.profile_from_args(ARGS)
    case_files = [
        "berry_curvature_conventional.jl",
"quantum_metric_conventional.jl",
"interband_berry_curvature_conventional.jl",
"interband_quantum_metric_conventional.jl"
    ]
    for case_file in case_files
        command = `$(Base.julia_cmd()) --project=$(Main.ExampleSupport.REPOSITORY_ROOT) $(joinpath(@__DIR__, "cases", case_file)) --profile=$(profile)`
        run(command)
    end
    println("TUTORIAL_GROUP_OK group=06_qg_pairwise profile=$(profile)")
