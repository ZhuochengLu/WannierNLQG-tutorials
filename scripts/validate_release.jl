#!/usr/bin/env julia
using JSON3
using SHA
const ROOT = normpath(joinpath(@__DIR__, ".."))
failures = String[]
required = ["README.md", "LICENSE", "CITATION.cff", "Project.toml",
            "Materials/GeS/vasp_SOC/GeS_tb.dat", "examples/ExampleSupport.jl"]
for relative in required
    isfile(joinpath(ROOT, relative)) || push!(failures, "missing $(relative)")
end
forbidden_names = Set(["POTCAR", "WAVECAR", "OUTCAR"])
optional_release_names = Set(["GeS.spn", "GeS.chk", "GeS.eig", "GeS.mmn"])
for (directory, dirs, files) in walkdir(ROOT)
    ".git" in dirs && deleteat!(dirs, findfirst(==(".git"), dirs))
    for name in files
        name in forbidden_names && push!(failures, "forbidden payload $(relpath(joinpath(directory, name), ROOT))")
        path = joinpath(directory, name)
        name in optional_release_names && continue
        filesize(path) > 100 * 1024^2 && push!(failures, "Git object exceeds 100 MiB $(relpath(path, ROOT))")
    end
end
manifest = JSON3.read(read(joinpath(ROOT, "Materials/GeS/vasp_SOC/DATA_MANIFEST.json"), String))
for record in manifest.files
    path = joinpath(ROOT, String(record.path))
    digest = bytes2hex(open(SHA.sha256, path))
    digest == String(record.sha256) || push!(failures, "hash mismatch $(record.path)")
end
isempty(failures) || error(join(failures, "\n"))
println("RELEASE_STATIC_OK files=$(sum(length(files) for (_, _, files) in walkdir(ROOT)))")
