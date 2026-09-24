#!/usr/bin/env julia
using JSON3
using SHA
const ROOT = normpath(joinpath(@__DIR__, ".."))
profile = isempty(ARGS) ? "reference" : only(ARGS)
summaries = String[]
for (directory, _, files) in walkdir(joinpath(ROOT, "examples"))
    if "summary.json" in files && occursin(joinpath("results", profile), directory)
        push!(summaries, joinpath(directory, "summary.json"))
    end
end
expected = profile == "reference" ? 46 : 40
length(summaries) >= expected || error("expected at least $(expected) summaries, found $(length(summaries))")
manifest_entries = Dict{String, Any}()
fe_model = JSON3.read(read(joinpath(ROOT, "Materials", "Fe", "vasp_SOC", "MODEL_STATUS.json"), String))
fe_bundle = JSON3.read(read(joinpath(ROOT, "Materials", "Fe", "vasp_SOC", "FE_BUNDLE_FILES.json"), String))
fe_tb_sha256 = bytes2hex(open(SHA.sha256, joinpath(ROOT, "Materials", "Fe", "vasp_SOC", "Fe_tb.dat")))
fe_bundle_sha256 = String(only(fe_bundle.files).sha256)
contract = JSON3.read(read(joinpath(ROOT, "manifests", "tutorial_contract.json"), String))
smoke_source_manifest = if profile == "smoke"
    source_root = get(ENV, "WANNIERNLQG_V110_PROJECT", "")
    isempty(source_root) && error("WANNIERNLQG_V110_PROJECT is required to validate v1.1.0 smoke results")
    source_sums = joinpath(source_root, "SHA256SUMS")
    isfile(source_sums) || error("missing v1.1.0 source SHA256SUMS: $(source_sums)")
    bytes2hex(open(SHA.sha256, source_sums))
else
    nothing
end
if profile == "reference"
    manifest = JSON3.read(read(joinpath(ROOT, "manifests", "results_manifest.json"), String))
    Int(manifest.count) == 46 && length(manifest.entries) == 46 ||
        error("wrong reference results manifest count")
    manifest_entries = Dict(String(entry.summary) => entry for entry in manifest.entries)
end
for path in summaries
    summary = JSON3.read(read(path, String))
    Bool(summary.finite_values) || error("non-finite result recorded in $(path)")
    version = String(summary.package_version)
    expected_version = (occursin("10_second_harmonic_generation", path) || occursin("11_fe_oam_and_linear_response", path)) ? "1.1.0" :
                       profile == "reference" ? "1.0.1" : version
    version == expected_version || error("wrong package version in $(path)")
    if profile == "reference"
        relative = relpath(path, ROOT)
        haskey(manifest_entries, relative) || error("summary missing from results manifest: $(relative)")
        entry = manifest_entries[relative]
        bytes2hex(open(SHA.sha256, path)) == String(entry.summary_sha256) ||
            error("stale summary hash in results manifest: $(relative)")
        version == String(entry.package_version) || error("manifest version mismatch: $(relative)")
        summary.package_commit == entry.package_commit || error("manifest commit mismatch: $(relative)")
        get(summary, :source_manifest_sha256, nothing) == entry.source_manifest_sha256 ||
            error("manifest source digest mismatch: $(relative)")
    end
    if occursin("10_second_harmonic_generation", path)
        summary.package_commit === nothing || error("local SHG result must not claim a public commit")
        expected_shg_manifest = profile == "reference" ?
            "5bb4904fb1f5f17a03faf4cba555743e906898cd0146f8328f7191ea498f3186" :
            smoke_source_manifest
        String(summary.source_manifest_sha256) == expected_shg_manifest ||
            error("wrong local v1.1.0 source manifest in $(path)")
        length(summary.output_files) == 36 || error("wrong SHG output count in $(path)")
        for name in summary.output_files
            file = joinpath(dirname(path), String(name))
            isfile(file) || error("missing SHG output $(file)")
            bytes2hex(open(SHA.sha256, file)) == String(summary.output_sha256[String(name)]) ||
                error("SHG output hash mismatch in $(file)")
            lines = readlines(file)
            response = startswith(String(name), "shg_chi_") ? "chi units=pm/V" : "sigma units=A/V^2"
            occursin(response, lines[1]) || error("wrong SHG unit in $(file)")
            lines[3] == "# energy_eV total_re total_im" || error("wrong SHG columns in $(file)")
            numeric = filter(line -> !startswith(line, "#"), lines)
            length(numeric) == 200 || error("wrong SHG row count in $(file)")
            for (index, line) in enumerate(numeric)
                values = parse.(Float64, split(line))
                length(values) == 3 && all(isfinite, values) || error("invalid SHG row in $(file)")
                abs(values[1] - 4 * (index - 1) / 199) <= 1e-12 ||
                    error("wrong SHG energy grid in $(file)")
            end
        end
    end
    if occursin("11_fe_oam_and_linear_response", path)
        if profile == "reference"
            String(summary.source_tree_sha256) == String(contract.fe_oam_and_linear_response.source_tree_sha256) ||
                error("Fe reference source tree mismatch")
            String(summary.source_manifest_sha256) == String(contract.fe_oam_and_linear_response.source_manifest_sha256) ||
                error("Fe reference source manifest mismatch")
        else
            String(summary.source_manifest_sha256) == smoke_source_manifest ||
                error("Fe smoke source manifest mismatch")
        end
        String(summary.qualification) == "DIAGNOSTIC_ONLY" || error("wrong Fe qualification")
        String(summary.wannierization_status) == String(fe_model.status) || error("Fe model status lost")
        String(summary.physics_status) == "HOLD" || error("Fe physics hold lost")
        !Bool(summary.production_eligible) || error("Fe falsely production eligible")
        String(summary.input_sha256["Fe_tb.dat"]) == fe_tb_sha256 ||
            error("wrong Fe TB identity")
        String(summary.input_sha256["Fe_fixed_full.h5"]) == fe_bundle_sha256 ||
            error("wrong Fe bundle identity")
        for name in summary.output_files
            file = joinpath(dirname(path), String(name))
            isfile(file) || error("missing Fe output $(file)")
            bytes2hex(open(SHA.sha256, file)) == String(summary.output_sha256[String(name)]) ||
                error("Fe output hash mismatch in $(file)")
            if profile == "reference"
                String(summary.source_provenance[String(name)].sha256) == String(summary.output_sha256[String(name)]) ||
                    error("Fe output differs from imported source in $(file)")
            end
        end
    else
        String(summary.qualification) == "TUTORIAL_NUMERICAL_EVIDENCE" || error("wrong qualification")
    end
end
println("RESULTS_OK profile=$(profile) summaries=$(length(summaries))")
