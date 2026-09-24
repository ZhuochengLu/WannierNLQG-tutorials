#!/usr/bin/env julia

# Fe SOC: VASP wavefunctions -> ordinary 18-WF Wannierization -> H/r model.
# Run only after the same VASP calculation has produced every input below.
using JSON3
using SHA
using LinearAlgebra
using WannierNLQG
import WannierNLQG.SymmetryFoundation as S
import WannierNLQG.WannierProjection as WP
import WannierNLQG.Wannierization as W

Base.pkgversion(WannierNLQG) == v"1.1.0" || error("WannierNLQG 1.1.0 is required")
VERSION == v"1.11.2" || error("Julia 1.11.2 is required")
Threads.nthreads() == 4 || error("Set JULIA_NUM_THREADS=4")
BLAS.set_num_threads(1)

length(ARGS) == 2 || error("usage: wannierize_fe.jl WORKDIR NEW_OUTPUT_DIR")
workdir, output_dir = abspath.(ARGS)
isdir(workdir) || error("Fe VASP workdir is missing: $workdir")
ispath(output_dir) && error("Output path already exists: $output_dir")
for name in ("POSCAR", "POTCAR", "INCAR", "OUTCAR", "WAVECAR",
             "wannier90.win", "wannier90.eig", "wannier90.mmn")
    isfile(joinpath(workdir, name)) || error("Same-run VASP input is missing: $name")
end

win = joinpath(workdir, "wannier90.win")
eig = joinpath(workdir, "wannier90.eig")
mmn = joinpath(workdir, "wannier90.mmn")
basis = WP.build_wannier_projection_basis(win)
basis.num_wannier == 18 || error("Expected 18 spinor Wannier functions")
source = S.VASPWavefunctionSource(
    joinpath(workdir, "POSCAR"), joinpath(workdir, "WAVECAR");
    potcar_file=joinpath(workdir, "POTCAR"),
    incar_file=joinpath(workdir, "INCAR"),
    outcar_file=joinpath(workdir, "OUTCAR"),
    spin_basis_saxis=(0.0, 0.0, 1.0),
    band_range=1:64, spin_channel=1, spinor=true,
    representation_cutoff_ev=nothing, include_time_reversal=false,
)

# The VASP MMN provides neighbor topology. Native PAW recomputes its numerical
# overlaps and the AMN from WAVECAR; the raw VASP AMN is not a solver input.
function config(checkpoint)
    input = W.WannierizationInputConfig(
        construction_policy=:standard, wannierization_mode=:ordinary,
        source=source, sewing_backend=W.CoefficientMappingSewing(),
        wavefunction_gauge_backend=W.NativeEigenstateGauge(),
        authoritative_hamiltonian=W.NativeDFTHamiltonian(),
        win_file=win, eig_file=eig, mmn_file=mmn, amn_file=nothing,
        matrix_elements=W.NativeVASPPAWMatrices(
            mmn; artifact_dir=joinpath(output_dir, "native_paw"), require_oracle=false,
        ),
        projection_basis=basis,
        outer_min_ev=-8.0, outer_max_ev=50.0,
        frozen_min_ev=-8.0, frozen_max_ev=20.0,
        num_wannier=18, degeneracy_tolerance_ev=0.01,
        representation_tolerance=1.0e-10,
        target_center_matching_tolerance=1.0e-7,
        compatibility_policy=:strict,
        preparation_execution=W.WavefunctionPreparationExecutionConfig(
            mode=:streaming_threads, max_workers=2,
            memory_budget_bytes=24 * 1024^3,
            checkpoint_directory=joinpath(output_dir, "preparation_checkpoints"),
            resume=true,
        ),
    )
    acceleration = W.WannierizationAccelerationConfig(
        strategy=:fixed, schedule=:two_stage,
        disentanglement_max_steps=1000, localization_max_steps=1000,
        constraint_operation_scope=:full,
    )
    solver = W.WannierizationSolverConfig(
        algorithm_profile=:auto, initialization=:amn,
        initialization_backend=W.AMNExactFrozenInitialization(),
        z_mix_ratio=0.1, u_mix_ratio=1.0, acceleration=acceleration,
        max_iterations=2500, convergence_tolerance=1.0e-10,
        convergence_window=3, localize=true, symmetrize_z=false,
        parallel=:threads, random_seed=UInt64(0x6e6c71675f66655),
    )
    return W.SymmetryAdaptedWannierizationConfig(
        input=input, solver=solver,
        checkpoint=W.WannierizationCheckpointConfig(
            checkpoint_hdf5=checkpoint,
            checkpoint_interval=50,
        ),
        runtime=W.WannierizationRuntimeConfig(progress_interval=50),
        output=W.WannierizationOutputConfig(
            profile=:hamiltonian_position,
            tb_output_formats=(:packed_hdf5, :wannier90_tb),
            write_wannier90_tb=true,
        ),
    )
end

sha(path) = bytes2hex(open(SHA.sha256, path))
function file_record(path)
    path === nothing && return nothing
    return Dict("path" => path, "exists" => isfile(path),
                "sha256" => isfile(path) ? sha(path) : nothing)
end
function write_json(path, value)
    open(path, "w") do io
        JSON3.pretty(io, value)
        println(io)
    end
end
function attempt_record(result)
    artifacts = Dict(
        string(name) => file_record(getproperty(result.artifacts, name))
        for name in fieldnames(typeof(result.artifacts))
    )
    return Dict(
        "status" => string(result.status), "history_count" => length(result.history),
        "accepted_iteration" => result.restart_state === nothing ? nothing : result.restart_state.iteration,
        "artifacts" => artifacts,
    )
end

mkdir(output_dir)
checkpoint1 = joinpath(output_dir, "attempt1.wannierization.h5")
result = W.construct_symmetry_adapted_wannier_functions(config(checkpoint1))
write_json(joinpath(output_dir, "attempt1.json"), attempt_record(result))

artifacts = attempt_record(result)["artifacts"]
tb = artifacts["wannier90_tb"]
packed = artifacts["packed_hdf5"]
checkpoint = artifacts["checkpoint_hdf5"]
hard_failures = Set(("IO_FAILURE", "INVALID_INPUT", "REPRESENTATION_INCOMPATIBLE",
                     "REPRESENTATION_UNDETERMINED", "SINGULAR_LOCALIZATION",
                     "LOCALIZATION_FAILED"))
receipt = Dict(
    "schema" => "wanniernlqg-tutorials.fe-wannierization-run",
    "schema_version" => "1.0", "qualification" => "DIAGNOSTIC_ONLY",
    "physics_status" => "HOLD", "production_eligible" => false,
    "package_version" => string(Base.pkgversion(WannierNLQG)),
    "source_manifest_sha256" => sha(joinpath(dirname(Base.active_project()), "SOURCE_MANIFEST.tsv")),
    "selected_attempt" => "attempt1", "status" => string(result.status),
    "accepted_iteration" => result.restart_state === nothing ? nothing : result.restart_state.iteration,
    "max_iterations" => 2500, "auto_restart" => false,
    "input_sha256" => Dict(name => sha(joinpath(workdir, name)) for name in
                           ("POSCAR", "POTCAR", "INCAR", "OUTCAR", "WAVECAR",
                            "wannier90.win", "wannier90.eig", "wannier90.mmn")),
    "profile" => "hamiltonian_position", "orbitals" => 18,
    "artifacts" => artifacts,
)
write_json(joinpath(output_dir, "terminal_result.json"), receipt)
string(result.status) in hard_failures && error("Solver hard failure; see terminal_result.json")
tb !== nothing && Bool(tb["exists"]) ||
    error("No accepted-state TB was exported; see terminal_result.json")
packed !== nothing && Bool(packed["exists"]) ||
    error("No Hamiltonian/position bundle was exported")
checkpoint !== nothing && Bool(checkpoint["exists"]) ||
    error("No accepted-state checkpoint was exported")
readback = W.read_wannierization_checkpoint_hdf5(String(checkpoint["path"]))
readback.restart_state === nothing && error("Checkpoint has no accepted restart state")
size(readback.wannier_centers_cartesian) == (18, 3) ||
    error("Checkpoint has an unexpected Wannier-center shape")
text_tb = WannierNLQG.IO.read_wannier_tb(String(tb["path"]))
text_tb.num_orbitals == 18 || error("Exported TB does not contain 18 orbitals")
bundle = WannierNLQG.IO.read_real_space_operator_bundle(String(packed["path"]))
bundle.manifest.profile == :hamiltonian_position || error("Unexpected operator profile")
length(bundle.operators) == 2 || error("Expected Hamiltonian and position only")
for operator in values(bundle.operators)
    all(isfinite, operator.data) || error("Nonfinite operator: $(operator.spec.kind)")
end
write_json(joinpath(output_dir, "selected_model.json"), receipt)
tb_path = String(tb["path"])
println("FE_WANNIERIZATION_DONE status=$(result.status) tb=$tb_path")
