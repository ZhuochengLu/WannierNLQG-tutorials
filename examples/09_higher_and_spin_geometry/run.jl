#!/usr/bin/env julia
    isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "ExampleSupport.jl"))
    profile = Main.ExampleSupport.profile_from_args(ARGS)
    case_files = [
        "hermitian_curvature_tensor_conventional.jl",
"triple_phase_product_conventional.jl",
"zeeman_interband_berry_curvature_conventional.jl",
"zeeman_interband_quantum_metric_conventional.jl"
    ]
    for case_file in case_files
        command = `$(Base.julia_cmd()) --project=$(Main.ExampleSupport.REPOSITORY_ROOT) $(joinpath(@__DIR__, "cases", case_file)) --profile=$(profile)`
        run(command)
    end
    println("TUTORIAL_GROUP_OK group=09_higher_and_spin_geometry profile=$(profile)")
