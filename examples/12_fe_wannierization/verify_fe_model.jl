#!/usr/bin/env julia

# Audit a finished Fe solve before its TB is used for bands.
using JSON3
using SHA
using WannierNLQG
import WannierNLQG.Wannierization as W

Base.pkgversion(WannierNLQG) == v"1.1.0" || error("WannierNLQG 1.1.0 is required")
length(ARGS) == 2 || error("usage: verify_fe_model.jl WORKDIR OUTPUT_DIR")
workdir, output_dir = abspath.(ARGS)
selected_path = joinpath(output_dir, "selected_model.json")
ispath(selected_path) && error("Selected model already exists: $selected_path")
attempt = JSON3.read(read(joinpath(output_dir, "attempt1.json"), String))
sha(path) = bytes2hex(open(SHA.sha256, path))

function artifact_record(value, output_dir)
    value === nothing && return nothing
    path = value isa AbstractString ? String(value) : String(value.path)
    relative = relpath(path, realpath(output_dir))
    (relative == ".." || startswith(relative, "../")) &&
        error("Solver artifact is outside this run: $path")
    isfile(path) || return Dict("path" => path, "exists" => false, "sha256" => nothing)
    real_relative = relpath(realpath(path), realpath(output_dir))
    (real_relative == ".." || startswith(real_relative, "../")) &&
        error("Solver artifact resolves outside this run: $path")
    digest = sha(path)
    if !(value isa AbstractString) && value.sha256 !== nothing
        digest == String(value.sha256) || error("Solver artifact hash changed: $path")
    end
    return Dict("path" => path, "exists" => true, "sha256" => digest)
end

manifest = joinpath(dirname(Base.active_project()), "SOURCE_MANIFEST.tsv")
isfile(manifest) || error("WannierNLQG source manifest is missing: $manifest")
String(attempt.package_version) == string(Base.pkgversion(WannierNLQG)) ||
    error("Solver and verifier used different package versions")
String(attempt.source_manifest_sha256) == sha(manifest) ||
    error("Solver and verifier used different WannierNLQG source manifests")
source_kind = hasproperty(attempt, :matrix_source_kind) ? String(attempt.matrix_source_kind) :
              "native_vasp_paw"
inputs = if source_kind == "native_vasp_paw"
    ("POSCAR", "POTCAR", "INCAR", "OUTCAR", "WAVECAR",
     "wannier90.win", "wannier90.eig", "wannier90.mmn")
elseif source_kind == "external_wannier90"
    ("POSCAR", "OUTCAR", "wannier90.win", "wannier90.eig",
     "wannier90.mmn", "wannier90.amn")
else
    error("Unknown Fe matrix source: $source_kind")
end
Set(String.(collect(keys(attempt.input_sha256)))) == Set(inputs) ||
    error("Recorded Fe input inventory disagrees with matrix source")
all(isfile(joinpath(workdir, name)) for name in inputs) || error("Fe source input is missing")
input_sha256 = Dict(name => sha(joinpath(workdir, name)) for name in inputs)
for name in inputs
    input_sha256[name] == String(getproperty(attempt.input_sha256, Symbol(name))) ||
        error("Fe source changed since the solve: $name")
end
artifacts = Dict(string(name) => artifact_record(value, output_dir)
                 for (name, value) in pairs(attempt.artifacts))
receipt = Dict(
    "schema" => "wanniernlqg-tutorials.fe-wannierization-run",
    "schema_version" => "1.0", "qualification" => "DIAGNOSTIC_ONLY",
    "physics_status" => "HOLD", "production_eligible" => false,
    "package_version" => String(attempt.package_version),
    "source_manifest_sha256" => String(attempt.source_manifest_sha256),
    "julia_version" => String(attempt.julia_version),
    "julia_threads" => Int(attempt.julia_threads),
    "matrix_source_kind" => source_kind,
    "selected_attempt" => "attempt1", "status" => String(attempt.status),
    "accepted_iteration" => attempt.accepted_iteration,
    "max_iterations" => 2500, "auto_restart" => false,
    "input_sha256" => input_sha256,
    "profile" => "hamiltonian_position", "orbitals" => 18,
    "artifacts" => artifacts,
)
open(joinpath(output_dir, "terminal_result.json"), "w") do io
    JSON3.pretty(io, receipt)
    println(io)
end

String(attempt.status) in ("COMPLETED", "COMPLETED_WITH_WARNINGS", "MAX_ITERATIONS") ||
    error("Solver did not end in an exportable state; see terminal_result.json")
iteration = attempt.accepted_iteration
iteration !== nothing && 0 <= Int(iteration) <= 2500 ||
    error("No accepted iteration within the original 2500-step ceiling")
for name in ("wannier90_tb", "packed_hdf5", "checkpoint_hdf5")
    haskey(artifacts, name) && artifacts[name] !== nothing && artifacts[name]["exists"] ||
        error("Missing accepted-state artifact: $name")
end
checkpoint = W.read_wannierization_checkpoint_hdf5(artifacts["checkpoint_hdf5"]["path"])
checkpoint.restart_state === nothing && error("Checkpoint has no accepted restart state")
checkpoint.restart_state.iteration == iteration || error("Checkpoint iteration differs from solver")
size(checkpoint.wannier_centers_cartesian) == (18, 3) ||
    error("Checkpoint has an unexpected Wannier-center shape")
tb = WannierNLQG.IO.read_wannier_tb(artifacts["wannier90_tb"]["path"])
tb.num_orbitals == 18 || error("Exported TB does not contain 18 orbitals")
bundle = WannierNLQG.IO.read_real_space_operator_bundle(artifacts["packed_hdf5"]["path"])
bundle.manifest.profile == :hamiltonian_position || error("Unexpected operator profile")
length(bundle.operators) == 2 || error("Expected Hamiltonian and position only")
for operator in values(bundle.operators)
    all(isfinite, operator.data) || error("Nonfinite operator: $(operator.spec.kind)")
end
open(selected_path, "w") do io
    JSON3.pretty(io, receipt)
    println(io)
end
println("FE_MODEL_VERIFIED status=$(attempt.status) tb=$(artifacts["wannier90_tb"]["path"])")
