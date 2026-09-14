#!/usr/bin/env julia
    isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "ExampleSupport.jl"))
    profile = Main.ExampleSupport.profile_from_args(ARGS)
    case_files = [
        "shift_vector_geometric_loop.jl",
"shift_vector_wilson_loop.jl",
"quantum_hermitian_connection_conventional.jl",
"quantum_hermitian_connection_geometric_loop.jl",
"quantum_hermitian_connection_wilson_loop.jl"
    ]
    for case_file in case_files
        command = `$(Base.julia_cmd()) --project=$(Main.ExampleSupport.REPOSITORY_ROOT) $(joinpath(@__DIR__, "cases", case_file)) --profile=$(profile)`
        run(command)
    end
    println("TUTORIAL_GROUP_OK group=08_shift_geometry profile=$(profile)")
