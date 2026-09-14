#!/usr/bin/env julia
    isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "ExampleSupport.jl"))
    profile = Main.ExampleSupport.profile_from_args(ARGS)
    case_files = [
        "berry_curvature_dipole_conventional.jl",
"berry_curvature_quadrupole_conventional.jl",
"quantum_metric_dipole_conventional.jl",
"quantum_metric_quadrupole_conventional.jl",
"quantum_christoffel_symbol_conventional.jl"
    ]
    for case_file in case_files
        command = `$(Base.julia_cmd()) --project=$(Main.ExampleSupport.REPOSITORY_ROOT) $(joinpath(@__DIR__, "cases", case_file)) --profile=$(profile)`
        run(command)
    end
    println("TUTORIAL_GROUP_OK group=07_qg_multipoles profile=$(profile)")
