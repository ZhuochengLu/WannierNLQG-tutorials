#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, ".."))
# Stabilize the PDF creation-time field; sidecars still audit each rendered PDF byte stream.
ENV["SOURCE_DATE_EPOCH"] = "0"
run(`python3 $(joinpath(@__DIR__, "generate_plot_configs.py"))`)
package_root = dirname(pathof(Base.require(Base.PkgId(Base.UUID("89ebeb90-0f9c-4af9-9f6b-5e6907d2c4e5"), "WannierNLQG"))))
package_root = normpath(joinpath(package_root, ".."))
for chapter in sort(filter(name -> occursin(r"^\d\d_", name), readdir(joinpath(ROOT, "examples"))))
    config_root = joinpath(ROOT, "examples", chapter, "plot_configs")
    isdir(config_root) || continue
    for config in sort(filter(name -> endswith(name, ".json"), readdir(config_root)))
        config_path = joinpath(config_root, config)
        if startswith(chapter, "10_")
            run(`python3 $(joinpath(@__DIR__, "plot_shg_spectrum.py")) $(config_path)`)
            continue
        end
        text = read(config_path, String)
        script = startswith(chapter, "01_") ? "plot_band_structure.jl" :
                 occursin("integral_", config) ? "plot_response_integral.jl" : "plot_kslice.jl"
        run(`$(Base.julia_cmd()) --project=$(ROOT) $(joinpath(package_root, "scripts", script)) --config $(config_path)`)
    end
end
withenv("WANNIERNLQG_VISUALIZATION_ROOT" => joinpath(package_root, "scripts")) do
    run(`python3 $(joinpath(@__DIR__, "plot_shift_current_methods.py"))`)
    run(`python3 $(joinpath(@__DIR__, "plot_geometry_method_comparisons.py"))`)
end
run(`python3 $(joinpath(@__DIR__, "sanitize_public_metadata.py"))`)
println("VISUALIZATION_ALL_OK")
