#!/usr/bin/env julia
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
            "examples/11_fe_oam_and_linear_response/README.md"]
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
manifest = JSON3.read(read(joinpath(ROOT, "Materials/GeS/vasp_SOC/DATA_MANIFEST.json"), String))
for record in manifest.files
    path = joinpath(ROOT, String(record.path))
    digest = bytes2hex(open(SHA.sha256, path))
    digest == String(record.sha256) || push!(failures, "hash mismatch $(record.path)")
end
isempty(failures) || error(join(failures, "\n"))
run(`python3 $(joinpath(ROOT, "test", "validate_readmes.py"))`)
println("RELEASE_STATIC_OK files=$(sum(length(files) for (_, _, files) in walkdir(ROOT)))")
