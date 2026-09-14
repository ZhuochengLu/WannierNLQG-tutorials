#!/usr/bin/env julia
const ROOT = normpath(joinpath(@__DIR__, ".."))
forbidden_content = ["/Users/luzhuocheng", "/private/tmp/", "BEGIN OPENSSH PRIVATE KEY", "ghp_"]
text_extensions = Set([".md", ".jl", ".json", ".toml", ".txt", ".cff", ".sh", ".py"])
failures = String[]
for (directory, dirs, files) in walkdir(ROOT)
    ".git" in dirs && deleteat!(dirs, findfirst(==(".git"), dirs))
    for name in files
        path = joinpath(directory, name)
        normpath(path) == normpath(@__FILE__) && continue
        if lowercase(splitext(name)[2]) in text_extensions || name in ("README", "LICENSE")
            text = read(path, String)
            for token in forbidden_content
                occursin(token, text) && push!(failures, "forbidden token $(token) in $(relpath(path, ROOT))")
            end
        end
    end
end
isempty(failures) || error(join(failures, "\n"))
println("PUBLIC_PAYLOAD_OK")
