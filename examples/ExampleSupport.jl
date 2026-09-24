module ExampleSupport

    using JSON3
    using SHA
    using WannierNLQG

    const REPOSITORY_ROOT = normpath(joinpath(@__DIR__, ".."))
    const MATERIAL_ROOT = joinpath(REPOSITORY_ROOT, "Materials", "GeS", "vasp_SOC")
    const GES_MODEL_FILE = joinpath(MATERIAL_ROOT, "GeS_tb.dat")
    const GES_SEED_PREFIX = joinpath(MATERIAL_ROOT, "GeS")
    const LEGACY_PACKAGE_COMMIT = "1e98f4841d10b6f86aecec8417d3a7da317c0f49"
    const OPTIONAL_FILES = ["GeS.spn", "GeS.chk", "GeS.eig", "GeS.mmn"]

    function profile_from_args(args)
        profile = "smoke"
        index = 1
        while index <= length(args)
            argument = args[index]
            if startswith(argument, "--profile=")
                profile = split(argument, "="; limit=2)[2]
            elseif argument == "--profile"
                index == length(args) && error("--profile requires smoke or reference")
                index += 1
                profile = args[index]
            else
                error("unsupported argument: $(argument)")
            end
            index += 1
        end
        profile in ("smoke", "reference") || error("profile must be smoke or reference")
        return profile
    end

    integral_mesh(profile::AbstractString) = profile == "reference" ? (100, 100) : (2, 2)
    kslice_mesh(profile::AbstractString) = profile == "reference" ? (200, 200) : (4, 4)
    band_segments(profile::AbstractString) = profile == "reference" ? [51, 51, 51, 51] : [3, 3, 3, 3]

    function optional_data_available()
        return all(name -> isfile(joinpath(MATERIAL_ROOT, name)), OPTIONAL_FILES)
    end

    function missing_optional_data()
        return [name for name in OPTIONAL_FILES if !isfile(joinpath(MATERIAL_ROOT, name))]
    end

    function file_sha256(path::AbstractString)
        return bytes2hex(open(SHA.sha256, path))
    end

    function package_identity()
        version = string(Base.pkgversion(WannierNLQG))
        version in ("1.0.1", "1.1.0") || error("unsupported tutorial package version: $(version)")
        package_root = normpath(joinpath(dirname(pathof(WannierNLQG)), ".."))
        manifest = joinpath(package_root, "SHA256SUMS")
        return Dict{String, Any}(
            "package_version" => version,
            "package_commit" => version == "1.0.1" ? LEGACY_PACKAGE_COMMIT : nothing,
            "source_manifest_sha256" => isfile(manifest) ? file_sha256(manifest) : nothing,
        )
    end

    function contains_nonfinite_token(path::AbstractString)
        endswith(lowercase(path), ".dat") || return false
        pattern = r"(?i)(^|[\s,])[+-]?(nan|inf)([\s,]|$)"
        return occursin(pattern, read(path, String))
    end

    function copy_result_tree(source::AbstractString, destination::AbstractString; retain_outputs=nothing)
        ispath(destination) && error("refusing to overwrite existing result directory: $(destination)")
        mkpath(destination)
        for name in readdir(source)
            name in ("progress.jsonl", "WannierNLQG.out") && continue
            retain_outputs !== nothing &&
                !(name in retain_outputs || name in ("metadata.txt", "spectral_response_metadata.txt")) && continue
            source_path = joinpath(source, name)
            destination_path = joinpath(destination, name)
            isdir(source_path) ? cp(source_path, destination_path; force=false) : cp(source_path, destination_path)
        end
    end

    function sanitize_metadata!(path::AbstractString)
        isfile(path) || return
        lines = split(read(path, String), '\n'; keepempty=true)
        for index in eachindex(lines)
            if occursin(r"^case_root\s*=", lines[index])
                lines[index] = "case_root                       = ."
            elseif occursin(r"^run_dir\s*=", lines[index])
                lines[index] = "run_dir                         = EPHEMERAL_RUN_DIRECTORY_OMITTED"
            elseif occursin(r"^output_root\s*=", lines[index])
                lines[index] = "output_root = EPHEMERAL_RUN_DIRECTORY_OMITTED"
            elseif occursin(r"^model_file\s*=", lines[index]) &&
                   !occursin(REPOSITORY_ROOT, lines[index])
                lines[index] = "model_file = EXTERNAL_INPUT_PATH_OMITTED"
            else
                lines[index] = replace(lines[index], REPOSITORY_ROOT => ".")
                occursin("/var/folders/", lines[index]) &&
                    (lines[index] = replace(lines[index], r"/var/folders/\S+" => "EPHEMERAL_RUN_PATH_OMITTED"))
            end
        end
        write(path, join(lines, '\n'))
    end

    function run_case(
        build_config;
        tutorial_dir::AbstractString,
        task_id::AbstractString,
        args=ARGS,
        requires_optional::Bool=false,
        input_files=Dict("GeS_tb.dat" => GES_MODEL_FILE),
        retain_outputs=nothing,
        qualification="TUTORIAL_NUMERICAL_EVIDENCE",
        summary_fields=Dict{String, Any}(),
    )
        profile = profile_from_args(args)
        if requires_optional && !optional_data_available()
            println("SKIPPED_MISSING_OPTIONAL_DATA task=$(task_id) missing=$(join(missing_optional_data(), ','))")
            println("Install the release asset with scripts/download_spin_data.sh")
            return nothing
        end
        destination = joinpath(tutorial_dir, "results", profile, task_id)
        ispath(destination) && error("refusing to overwrite existing result directory: $(destination)")
        mktempdir(; prefix="wanniernlqg-tutorial-") do scratch
            config = build_config(profile=profile, output_root=scratch, progress_enabled=false)
            result = WannierNLQG.run(config)
            child = only(result.task_results)
            copy_result_tree(child.run_dir, destination; retain_outputs=retain_outputs)
            sanitize_metadata!(joinpath(destination, "metadata.txt"))
            output_names = sort(filter(name -> isfile(joinpath(destination, name)), basename.(child.outputs)))
            copied_outputs = [joinpath(destination, name) for name in output_names]
            finite_values = !any(contains_nonfinite_token, copied_outputs)
            hashes = Dict(name => file_sha256(joinpath(destination, name)) for name in output_names)
            summary = Dict{String, Any}(
                "task_id" => task_id,
                package_identity()...,
                "profile" => profile,
                "julia_threads" => Threads.nthreads(),
                "input_sha256" => Dict(name => file_sha256(path) for (name, path) in input_files),
                "output_files" => output_names,
                "output_sha256" => hashes,
                "finite_values" => finite_values,
                "qualification" => qualification,
            )
            merge!(summary, summary_fields)
            open(joinpath(destination, "summary.json"), "w") do io
                JSON3.pretty(io, summary)
                write(io, '
')
            end
            finite_values || error("non-finite token found in numerical outputs for $(task_id)")
            println("TUTORIAL_CASE_OK task=$(task_id) profile=$(profile) outputs=$(join(output_names, ','))")
            return destination
        end
    end

    end
