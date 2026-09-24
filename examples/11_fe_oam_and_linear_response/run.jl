#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, "..", ".."))
const PROJECT = Base.active_project()
PROJECT === nothing && error("start Julia with --project pointing to WannierNLQG v1.1.0")
const BUNDLE = get(ENV, "FE_OPERATOR_BUNDLE", joinpath(ROOT, "Materials/Fe/vasp_SOC/Fe_fixed_full.h5"))
if !isfile(BUNDLE)
    println("SKIPPED_MISSING_OPTIONAL_DATA group=11_fe_oam_and_linear_response missing=Fe_fixed_full.h5")
    println("See Materials/Fe/vasp_SOC/README.md for local bundle installation")
else
    for family in ("oam", "linear_transport", "linear_optical"), method in ("conventional", "projector"), temp in ("T000", "T300")
        task = "$(family)_$(method)_$(temp)"
        run(`$(Base.julia_cmd()) --project=$(dirname(PROJECT)) $(joinpath(@__DIR__, "cases", "fe_response.jl")) --task=$(task) $(ARGS)`)
    end
    for task in ("berry_sos_occupied_xy", "berry_transport_equivalent_xy")
        run(`$(Base.julia_cmd()) --project=$(dirname(PROJECT)) $(joinpath(@__DIR__, "cases", "fe_response.jl")) --task=$(task) $(ARGS)`)
    end
    println("TUTORIAL_GROUP_OK group=11_fe_oam_and_linear_response")
end
