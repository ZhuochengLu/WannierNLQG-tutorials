#!/usr/bin/env julia
using DelimitedFiles
using JSON3
using SHA
const ROOT = normpath(joinpath(@__DIR__, ".."))
failures = String[]
required = ["README.md", "LICENSE", "CITATION.cff", "Project.toml",
            "Materials/GeS/vasp_SOC/GeS_tb.dat", "examples/ExampleSupport.jl",
            "Materials/Fe/vasp_SOC/Fe_tb.dat", "Materials/Fe/vasp_SOC/POTCAR.txt",
            "Materials/Fe/vasp_SOC/DATA_MANIFEST.json",
            "Materials/Fe/vasp_SOC/MODEL_STATUS.json",
            "Materials/Fe/vasp_SOC/FE_BUNDLE_FILES.json",
            "Materials/Fe/vasp_SOC/bands/Fe_vasp_path_receipt.json",
            "Materials/Fe/vasp_SOC/bands/Fe_tb_path_receipt.json",
            "examples/11_fe_oam_and_linear_response/figures/FIGURE_SHA256.json",
            "examples/11_fe_oam_and_linear_response/results/reference/THREE_MECHANISM_VALIDATION.json",
            "examples/11_fe_oam_and_linear_response/README.md",
            "examples/12_fe_wannierization/results/native_paw_2026-09-25/RESULT.json",
            "examples/12_fe_wannierization/results/native_paw_2026-09-25/Fe_new_tb_path_absolute.dat",
            "examples/12_fe_wannierization/results/native_paw_2026-09-25/Fe_new_tb_vs_vasp.png"]
for relative in required
    isfile(joinpath(ROOT, relative)) || push!(failures, "missing $(relative)")
end
forbidden_names = Set(["POTCAR", "WAVECAR", "OUTCAR", "CHGCAR"])
optional_release_names = Set(["GeS.spn", "GeS.chk", "GeS.eig", "GeS.mmn"])
for (directory, dirs, files) in walkdir(ROOT)
    ".git" in dirs && deleteat!(dirs, findfirst(==(".git"), dirs))
    for name in files
        name in forbidden_names && push!(failures, "forbidden payload $(relpath(joinpath(directory, name), ROOT))")
        name == "Fe_fixed_full.h5" && push!(failures, "Fe bundle must remain a separate Release asset")
        path = joinpath(directory, name)
        if occursin(joinpath("Materials", "Fe", "vasp_SOC"), directory) &&
           lowercase(splitext(name)[2]) in (".amn", ".mmn", ".eig", ".chk")
            push!(failures, "forbidden Fe intermediate $(relpath(path, ROOT))")
        end
        name in optional_release_names && continue
        filesize(path) > 100 * 1024^2 && push!(failures, "Git object exceeds 100 MiB $(relpath(path, ROOT))")
    end
end
fe_manifest = JSON3.read(read(joinpath(ROOT, "Materials/Fe/vasp_SOC/DATA_MANIFEST.json"), String))
optical_export = JSON3.read(read(joinpath(ROOT, "examples/11_fe_oam_and_linear_response/results/reference/THREE_MECHANISM_VALIDATION.json"), String))
Bool(optical_export.native_file_names) ||
    push!(failures, "Fe optical outputs are not natively named")
String(optical_export.export_contract) == "THREE_MECHANISM_VALIDATED" ||
    push!(failures, "Fe optical export validation receipt is missing")
for record in fe_manifest.files
    path = joinpath(ROOT, String(record.path))
    isfile(path) || (push!(failures, "missing Fe input $(record.path)"); continue)
    digest = bytes2hex(open(SHA.sha256, path))
    digest == String(record.sha256) || push!(failures, "Fe input hash mismatch $(record.path)")
    filesize(path) == Int(record.bytes) || push!(failures, "Fe input size mismatch $(record.path)")
end
result_dir = joinpath(ROOT, "examples/12_fe_wannierization/results/native_paw_2026-09-25")
result_receipt_path = joinpath(result_dir, "RESULT.json")
if isfile(result_receipt_path)
    result = JSON3.read(read(result_receipt_path, String))
    String(result.schema) == "wanniernlqg-tutorials.fe-wannierization-public-result" ||
        push!(failures, "wrong Fe tutorial result schema")
    String(result.profile) == "hamiltonian_position" && Int(result.operator_count) == 2 ||
        push!(failures, "wrong Fe tutorial operator profile")
    String(result.qualification) == "DIAGNOSTIC_ONLY" && !Bool(result.production_eligible) ||
        push!(failures, "Fe tutorial result incorrectly qualified")
    String(result.selected_attempt) == "attempt1" && Int(result.solver_max_iterations) == 2500 &&
        Int(result.selected_accepted_iteration) <= 2500 && !Bool(result.auto_restart) ||
        push!(failures, "Fe tutorial result exceeds the selected first-run ceiling")
    Int(result.path_points) == 801 && Int(result.wannier_functions) == 18 &&
        Int(result.vasp_bands) == 64 || push!(failures, "wrong Fe tutorial band dimensions")
    reference_receipt = JSON3.read(read(joinpath(ROOT,
        "Materials/Fe/vasp_SOC/bands/Fe_vasp_path_receipt.json"), String))
    String(result.reference_table_sha256) == String(reference_receipt.table_sha256) ||
        push!(failures, "Fe tutorial VASP reference hash mismatch")
    published_names = Set{String}()
    for record in result.published_files
        name = String(record.path)
        if !(name in ("Fe_new_tb_path_absolute.dat", "Fe_new_tb_vs_vasp.png"))
            push!(failures, "unexpected Fe tutorial result $(name)")
            continue
        end
        push!(published_names, name)
        path = joinpath(result_dir, name)
        if !isfile(path)
            push!(failures, "missing Fe tutorial result $(name)")
            continue
        end
        filesize(path) == Int(record.bytes) || push!(failures, "Fe result size mismatch $(name)")
        bytes2hex(open(SHA.sha256, path)) == String(record.sha256) ||
            push!(failures, "Fe result hash mismatch $(name)")
    end
    published_names == Set(["Fe_new_tb_path_absolute.dat", "Fe_new_tb_vs_vasp.png"]) ||
        push!(failures, "wrong Fe tutorial public result inventory")
    plotted_hashes = Dict(String(record.file) => String(record.sha256)
                          for record in result.plot_input_sha256)
    public_hashes = Dict(String(record.path) => String(record.sha256)
                         for record in result.published_files)
    get(plotted_hashes, "Fe_new_tb_path_absolute.dat", "") ==
        get(public_hashes, "Fe_new_tb_path_absolute.dat", "") ||
        push!(failures, "Fe plot is not bound to the public TB band table")
    all(haskey(plotted_hashes, name) for name in
        ("Fe_vasp_aligned_path_absolute.dat", "Fe_visualization_path.json", "band_plot.json")) ||
        push!(failures, "Fe plot input hash inventory incomplete")
    table_path = joinpath(result_dir, "Fe_new_tb_path_absolute.dat")
    if isfile(table_path)
        table = readdlm(table_path, comments=true)
        size(table) == (801, 19) && all(isfinite, table) ||
            push!(failures, "invalid Fe tutorial band table")
    end
end
manifest = JSON3.read(read(joinpath(ROOT, "Materials/GeS/vasp_SOC/DATA_MANIFEST.json"), String))
for record in manifest.files
    path = joinpath(ROOT, String(record.path))
    digest = bytes2hex(open(SHA.sha256, path))
    digest == String(record.sha256) || push!(failures, "hash mismatch $(record.path)")
end
isempty(failures) || error(join(failures, "\n"))
run(`python3 $(joinpath(ROOT, "test", "validate_readmes.py"))`)
println("RELEASE_STATIC_OK files=$(sum(length(files) for (_, _, files) in walkdir(ROOT)))")
