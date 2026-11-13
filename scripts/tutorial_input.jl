module TutorialInput
using WannierNLQG, TOML, SHA
include(joinpath(@__DIR__, "..", "models", "TutorialModels.jl"))
const ROOT = normpath(joinpath(@__DIR__, ".."))
const MODEL_PATH_FIELDS = ("model_file", "real_space_operator_bundle_file", "seedname",
    "spin_file", "checkpoint_file", "wsvec_file")

# Read a small host-binding file once; execution and saved provenance share this snapshot.
function load_data_paths(data_paths)
    data_paths === nothing && return nothing
    data_paths isa AbstractString || return data_paths
    file = abspath(data_paths)
    raw = read(file)
    document = TOML.parse(String(copy(raw)))
    return (file=file, base_dir=dirname(file), raw=raw,
        sha256=bytes2hex(SHA.sha256(raw)),
        paths=get(document, "paths", Dict{String, Any}()))
end

"""Resolve explicit host data locations while leaving physical TOML settings unchanged.

Keys in `[paths]` are repository-relative logical material paths. Values are existing
host paths; a binding file is private host configuration, not an input-model schema.
No model is downloaded, copied, generated or selected by a latest alias.
"""
function bind_data_paths!(document, input_path, data_paths)
    data_paths === nothing && return
    snapshot = load_data_paths(data_paths)
    bindings = snapshot.paths
    model = get(document, "model", Dict{String, Any}())
    for name in MODEL_PATH_FIELDS
        value = get(model, name, "")
        isempty(value) && continue
        logical = replace(relpath(abspath(dirname(input_path), value), ROOT), '\\' => '/')
        haskey(bindings, logical) || continue
        host_path = bindings[logical]
        host_path isa AbstractString || error("material path binding must be a string: $logical")
        model[name] = abspath(snapshot.base_dir, host_path)
    end
    return nothing
end

"""List explicitly required files using the same path bindings as execution."""
function missing_input_paths(path; data_paths=nothing)
    path = abspath(path)
    document = TOML.parsefile(path)
    bind_data_paths!(document, path, data_paths)
    model = get(document, "model", Dict{String, Any}())
    required = String[]
    for name in MODEL_PATH_FIELDS
        name == "seedname" && continue
        value = get(model, name, "")
        isempty(value) || push!(required, abspath(dirname(path), value))
    end
    if !isempty(get(model, "seedname", ""))
        seed = abspath(dirname(path), model["seedname"])
        append!(required, [seed * ext for ext in (".spn", ".chk", ".eig", ".mmn")])
    end
    return filter(p -> !isfile(p), required)
end

"""Use the package parser, with declared tutorial models and explicit host path overrides."""
function read_input(path; check_paths=true, output_root=nothing, data_paths=nothing)
    path = abspath(path)
    document = TOML.parsefile(path)
    bind_data_paths!(document, path, data_paths)
    native = get(get(document, "model", Dict()), "source", "") == "julia"
    payload = native ? TutorialModels.model(document["model"]["identity"]) : nothing
    if output_root !== nothing
        get!(document, "output", Dict{String, Any}())["output_root"] = abspath(output_root)
    end
    return resolve_task_input(document; base_dir=dirname(path), model=payload,
        input_path=path, check_paths)
end

"""Check or explain a TOML, or execute it with fresh records and original package semantics."""
function main(args)
    positional = String[]
    data_paths = nothing
    for arg in args
        if startswith(arg, "--data-paths=")
            data_paths = split(arg, "="; limit=2)[2]
        else
            push!(positional, arg)
        end
    end
    length(positional) in (2, 3) || error("usage: tutorial_input.jl check|explain|run INPUT.toml [NEW_RECORDS] [--data-paths=HOST.toml]")
    action, path = positional[1:2]
    action in ("check", "explain", "run") || error("unknown action: $action")
    action == "run" && length(positional) != 3 && error("run requires NEW_RECORDS")
    records = action == "run" ? abspath(positional[3]) : nothing
    records !== nothing && ispath(records) && error("fresh records directory required: $records")
    bindings = load_data_paths(data_paths)
    input = read_input(path; data_paths=bindings,
        output_root=records === nothing ? nothing : joinpath(records, "outputs"))
    isempty(input.pending) || error("unresolved input: $(join(input.pending, ", "))")
    if action == "run"
        run_task_input(input; record_directory=records)
        if bindings !== nothing
            binding_file = joinpath(records, "host_path_bindings.toml")
            origin_file = joinpath(records, "host_path_bindings_origin.toml")
            # These two names belong to this fresh, single-writer run directory.
            any(ispath, (binding_file, origin_file)) && error("binding record already exists")
            write(binding_file, bindings.raw)
            open(origin_file, "w") do io
                TOML.print(io, Dict("binding_file" => bindings.file,
                    "binding_sha256" => bindings.sha256,
                    "scope" => "Explicit host data locations; no numerical parameter override."))
            end
        end
        println("TUTORIAL_INPUT_RUN_OK ", path)
    elseif action == "explain"
        print(explain_task_input(input))
    else
        println("TUTORIAL_INPUT_CHECK_OK ", path)
    end
end
end
abspath(PROGRAM_FILE) == abspath(@__FILE__) && TutorialInput.main(ARGS)
