#!/usr/bin/env julia
isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "ExampleSupport.jl"))
profile = Main.ExampleSupport.profile_from_args(ARGS)
case_files = [
    "band_structure.jl"
]
for case_file in case_files
    command = `$(Base.julia_cmd()) --project=$(Main.ExampleSupport.REPOSITORY_ROOT) $(joinpath(@__DIR__, "cases", case_file)) --profile=$(profile)`
    run(command)
end
println("TUTORIAL_GROUP_OK group=01_band_structure profile=$(profile)")
