#!/usr/bin/env julia

# Same-run VASP -> ordinary MLWF -> full 11-operator bundle driver.
# Each invocation performs exactly one named stage so that logs, intermediate
# artifacts, and hard failures remain independently auditable in this directory.

using Dates
using HDF5
using JSON3
using LinearAlgebra
using WannierNLQG
import WannierNLQG.SymmetryFoundation as S
import WannierNLQG.WannierProjection as WP
import WannierNLQG.Wannierization as W

length(ARGS) == 1 || error("usage: Fe_ordinary_full_driver.jl vasp-preflight|rebase-inputs|prepare|target|spn|uiu|uhu|siu|shu|solve|readback")
const STAGE = only(ARGS)
const ROOT = normpath(@__DIR__)
const PREFIX = "Fe_ordinary_full_w50"
# Immutable VASP2WANNIER90 output from the new SOC SCF.  The MMN supplies
# topology only; all numerical PAW MMN/AMN values are regenerated natively.
const RAW_OUTCAR = joinpath(ROOT, "OUTCAR")
const RAW_WAVECAR = joinpath(ROOT, "WAVECAR")
const RAW_WIN = joinpath(ROOT, "wannier90.win")
const RAW_EIG = joinpath(ROOT, "wannier90.eig")
const RAW_MMN = joinpath(ROOT, "wannier90.mmn")
const RAW_AMN = joinpath(ROOT, "wannier90.amn")

# Derived, prefixed inputs.  They never replace the raw VASP interface files.
const WIN = joinpath(ROOT, "$(PREFIX).win")
const EIG = joinpath(ROOT, "$(PREFIX).eig")
const FUTURE_INCAR = joinpath(ROOT, "$(PREFIX).INCAR")
const REBASE_JSON = joinpath(ROOT, "$(PREFIX)_rebased_input_manifest.json")
const PREFLIGHT_JSON = joinpath(ROOT, "$(PREFIX)_vasp_preflight.json")
const BAND_REPRESENTATION = joinpath(ROOT, "$(PREFIX)_identity_representation.h5")
const NATIVE_PAW = joinpath(ROOT, "$(PREFIX)_native_paw")
const TARGET_JSON = joinpath(ROOT, "$(PREFIX)_operator_target_contract.json")
const SPN = joinpath(ROOT, "$(PREFIX).spn")
const SPN_PROVENANCE = joinpath(ROOT, "$(PREFIX).spn.provenance.h5")
const UIU = joinpath(ROOT, "$(PREFIX).uIu")
const UHU = joinpath(ROOT, "$(PREFIX).uHu")
const SIU = joinpath(ROOT, "$(PREFIX).sIu")
const SHU = joinpath(ROOT, "$(PREFIX).sHu")
const CACHE_POINTS = 2
const RANDOM_SEED = UInt64(0x6e6c71675f66655)

sha256(path::AbstractString) = S.sha256_file(path)

function clean(value)
    value === nothing && return nothing
    value isa Symbol && return String(value)
    value isa Enum && return string(value)
    value isa Complex && return Dict("real" => real(value), "imag" => imag(value))
    value isa AbstractFloat && return isfinite(value) ? value : nothing
    value isa NamedTuple && return Dict(string(key) => clean(item) for (key, item) in pairs(value))
    value isa AbstractDict && return Dict(string(key) => clean(item) for (key, item) in pairs(value))
    value isa Tuple && return map(clean, value)
    value isa AbstractArray && return map(clean, value)
    value isa Union{String,Integer,Bool} && return value
    return string(value)
end

function artifact(path)
    path === nothing && return nothing
    value = String(path)
    return Dict(
        "path" => value,
        "exists" => isfile(value),
        "bytes" => isfile(value) ? filesize(value) : nothing,
        "sha256" => isfile(value) ? sha256(value) : nothing,
    )
end

function write_json(path, payload; replace=false)
    ispath(path) && !replace && error("REFUSE_OVERWRITE: $(path)")
    temporary = path * ".tmp"
    open(temporary, "w") do io
        JSON3.pretty(io, clean(payload))
        println(io)
    end
    mv(temporary, path; force=true)
    return path
end

function require_runtime()
    VERSION == v"1.11.2" || error("RUNTIME_MISMATCH: expected Julia 1.11.2, got $(VERSION)")
    Threads.nthreads() == 4 || error("THREAD_MISMATCH: expected 4 Julia threads, got $(Threads.nthreads())")
    BLAS.set_num_threads(1)
    BLAS.get_num_threads() == 1 || error("BLAS_THREAD_MISMATCH")
end

function require_raw_vasp_inputs()
    for path in (
        joinpath(ROOT, "POSCAR"), joinpath(ROOT, "POTCAR"), joinpath(ROOT, "INCAR"),
        joinpath(ROOT, "KPOINTS"), RAW_OUTCAR, RAW_WAVECAR, RAW_WIN, RAW_EIG, RAW_MMN, RAW_AMN,
    )
        isfile(path) || error("SAME_RUN_VASP_INPUT_MISSING: $(path)")
    end
end

function require_rebased_inputs()
    isfile(PREFLIGHT_JSON) || error("VASP_PREFLIGHT_REQUIRED")
    occursin("\"status\": \"PASS\"", read(PREFLIGHT_JSON, String)) || error("VASP_PREFLIGHT_NOT_PASS")
    isfile(REBASE_JSON) || error("REBASED_INPUT_MANIFEST_REQUIRED")
    for path in (WIN, EIG, FUTURE_INCAR)
        isfile(path) || error("REBASED_INPUT_MISSING: $(path)")
    end
end

function source(; incar_file=joinpath(ROOT, "INCAR"))
    return S.VASPWavefunctionSource(
        joinpath(ROOT, "POSCAR"),
        RAW_WAVECAR;
        potcar_file=joinpath(ROOT, "POTCAR"),
        incar_file=incar_file,
        outcar_file=RAW_OUTCAR,
        spin_basis_saxis=(0.0, 0.0, 1.0),
        band_range=1:64,
        spin_channel=1,
        spinor=true,
        representation_cutoff_ev=nothing,
        include_time_reversal=false,
    )
end

function projection_basis()
    basis = WP.build_wannier_projection_basis(WIN)
    basis.num_wannier == 18 || error("PROJECTION_DIMENSION_MISMATCH: expected 18, got $(basis.num_wannier)")
    return basis
end

function operator_execution(label)
    serial = get(ENV, "FE_PREP_SERIAL", "0") == "1"
    return W.WavefunctionPreparationExecutionConfig(
        mode=serial ? :streaming_serial : :streaming_threads,
        max_workers=serial ? 1 : 2,
        memory_budget_bytes=(serial ? 8 : 24) * 1024^3,
        checkpoint_directory=joinpath(ROOT, "$(PREFIX)_$(label)_checkpoints"),
        resume=true,
    )
end

function build_config(; max_iterations=2500, initialization=:amn, restart_hdf5=nothing, checkpoint_hdf5)
    require_rebased_inputs()
    isfile(BAND_REPRESENTATION) || error("IDENTITY_REPRESENTATION_NOT_PREPARED")
    input = W.WannierizationInputConfig(
        construction_policy=:standard,
        wannierization_mode=:ordinary,
        source=source(),
        sewing_backend=W.CoefficientMappingSewing(),
        wavefunction_gauge_backend=W.NativeEigenstateGauge(),
        authoritative_hamiltonian=W.NativeDFTHamiltonian(),
        win_file=WIN,
        eig_file=EIG,
        # RAW_MMN carries neighbour topology and reciprocal shifts only.  The
        # native route regenerates all numerical MMN/AMN values from VASP PAW.
        mmn_file=RAW_MMN,
        amn_file=nothing,
        matrix_elements=W.NativeVASPPAWMatrices(
            RAW_MMN;
            artifact_dir=NATIVE_PAW,
            require_oracle=false,
        ),
        projection_basis=projection_basis(),
        band_representation_hdf5=BAND_REPRESENTATION,
        outer_min_ev=-8.0,
        outer_max_ev=50.0,
        frozen_min_ev=-8.0,
        frozen_max_ev=20.0,
        num_wannier=18,
        degeneracy_tolerance_ev=0.01,
        representation_tolerance=1.0e-10,
        target_center_matching_tolerance=1.0e-7,
        compatibility_policy=:strict,
        preparation_execution=operator_execution("native_paw"),
    )
    acceleration = W.WannierizationAccelerationConfig(
        # Package-default algorithms for this campaign: SMV fixed-point
        # disentanglement and symmetry-projected-gradient localization.  Only
        # the two-stage schedule, the authorized Z/U iteration caps, and the
        # full magnetic-group constraint scope are stated explicitly.
        strategy=:fixed,
        schedule=:two_stage,
        disentanglement_max_steps=1000,
        localization_max_steps=1000,
        constraint_operation_scope=:full,
    )
    solver = W.WannierizationSolverConfig(
        algorithm_profile=:auto,
        initialization=initialization,
        initialization_backend=W.AMNExactFrozenInitialization(),
        z_mix_ratio=0.1,
        u_mix_ratio=1.0,
        acceleration=acceleration,
        max_iterations=max_iterations,
        convergence_tolerance=1.0e-10,
        convergence_window=3,
        localize=true,
        symmetrize_z=false,
        parallel=:threads,
        random_seed=RANDOM_SEED,
    )
    output = W.WannierizationOutputConfig(
        tb_output_formats=(:packed_hdf5, :wannier90_tb),
        write_wannier90_tb=true,
        profile=:full,
        spn_file=SPN,
        spn_provenance_file=SPN_PROVENANCE,
        uiu_file=UIU,
        uhu_file=UHU,
        siu_file=SIU,
        shu_file=SHU,
        uiu_provenance_json=UIU * ".provenance.json",
        uhu_provenance_json=UHU * ".provenance.json",
        siu_provenance_json=SIU * ".provenance.json",
        shu_provenance_json=SHU * ".provenance.json",
        operator_closure_tolerance=1.0e-6,
        spin_family_covariance_tolerance=1.0e-8,
        spin_family_idempotence_tolerance=1.0e-9,
    )
    return W.SymmetryAdaptedWannierizationConfig(
        input=input,
        solver=solver,
        checkpoint=W.WannierizationCheckpointConfig(
            restart_hdf5=restart_hdf5,
            checkpoint_hdf5=checkpoint_hdf5,
            checkpoint_interval=50,
        ),
        runtime=W.WannierizationRuntimeConfig(progress_interval=50),
        output=output,
    )
end

function current_target()
    target = W.prepare_wannier_operator_target_contract(
        build_config(checkpoint_hdf5=joinpath(ROOT, "$(PREFIX)_target_placeholder.h5")),
    )
    target.num_bands == 64 || error("TARGET_BAND_COUNT_MISMATCH: $(target.num_bands)")
    target.num_kpoints == 1000 || error("TARGET_KPOINT_COUNT_MISMATCH: $(target.num_kpoints)")
    sha256(target.operator_oracle_mmn_file) == target.operator_oracle_mmn_sha256 ||
        error("OPERATOR_ORACLE_MMN_DIGEST_MISMATCH")
    sha256(target.solver_mmn_file) == target.solver_mmn_sha256 || error("SOLVER_MMN_DIGEST_MISMATCH")
    return target
end

function stage_vasp_preflight()
    require_raw_vasp_inputs()
    outcar = read(RAW_OUTCAR, String)
    incar = read(joinpath(ROOT, "INCAR"), String)
    (occursin("reached required accuracy", outcar) ||
     occursin("aborting loop because EDIFF is reached", outcar)) ||
        error("VASP_SCF_NOT_CONVERGED")
    for pattern in (r"LNONCOLLINEAR\s*=\s*\.TRUE\.", r"LSORBIT\s*=\s*\.TRUE\.", r"LWANNIER90\s*=\s*T", r"LWRITE_MMN_AMN\s*=\s*T")
        occursin(pattern, incar) || error("INCAR_CONTRACT_MISSING: $(pattern)")
    end
    for token in ("LNONCOLLINEAR =      T", "LSORBIT =      T", "NBANDS=     64", "NKPTS =   1000")
        occursin(token, outcar) || error("OUTCAR_CONTRACT_MISSING: $(token)")
    end
    header = S.read_vasp_wavecar_header(RAW_WAVECAR)
    (header.num_bands, header.num_kpoints) == (64, 1000) || error("WAVECAR_DIMENSION_MISMATCH")
    header.cutoff_ev > 0.0 || error("WAVECAR_CUTOFF_INVALID")
    native = S.read_vasp_wavefunctions(source(; incar_file=joinpath(ROOT, "INCAR")))
    native.spinor || error("WAVECAR_SPINOR_MISSING")
    (length(native.kpoints), native.mp_grid) == (1000, (10, 10, 10)) || error("WAVECAR_GRID_MISMATCH")
    raw_win = read(RAW_WIN, String)
    occursin("begin projections\nFe:l=0;l=1;l=2\nend projections", raw_win) ||
        error("FULL_SPD_PROJECTION_MISSING")
    eig = WannierNLQG.IO.read_wannier_eig(RAW_EIG)
    mmn = WannierNLQG.IO.read_wannier_mmn(RAW_MMN)
    amn = WannierNLQG.IO.read_wannier_amn(RAW_AMN)
    size(eig.data) == (64, 1000) || error("EIG_DIMENSION_MISMATCH: $(size(eig.data))")
    (mmn.num_bands, mmn.num_kpts) == (64, 1000) || error("MMN_DIMENSION_MISMATCH")
    (amn.num_bands, amn.num_kpts, amn.num_wannier) == (64, 1000, 18) || error("AMN_DIMENSION_MISMATCH")
    filesize(RAW_WAVECAR) > 1024 || error("WAVECAR_INCOMPLETE")
    write_json(PREFLIGHT_JSON, Dict(
        "status" => "PASS",
        "route" => "converged VASP SOC noncollinear source; raw MMN topology only; raw AMN prohibited",
        "num_bands" => 64,
        "num_kpoints" => 1000,
        "raw_num_wannier" => 18,
        "spinor" => true,
        "wavecar_header" => Dict(string(name) => clean(getproperty(header, name)) for name in fieldnames(typeof(header))),
        "native_wavefunction" => Dict("mp_grid" => native.mp_grid, "spinor" => native.spinor, "kpoints" => length(native.kpoints)),
        "incar_status" => "physical SOC/spin and SCF fields cross-checked against OUTCAR; the embedded WANNIER90 input is the direct w50 SCF input",
        "raw_mmn_role" => "topology_and_reciprocal_shifts_only",
        "raw_amn_role" => "inventory_only_prohibited_as_oracle_or_solver_input",
        "inputs" => Dict(
            "INCAR_direct_w50_source" => artifact(joinpath(ROOT, "INCAR")),
            "KPOINTS" => artifact(joinpath(ROOT, "KPOINTS")),
            "POSCAR" => artifact(joinpath(ROOT, "POSCAR")),
            "POTCAR" => artifact(joinpath(ROOT, "POTCAR")),
            "OUTCAR_raw" => artifact(RAW_OUTCAR),
            "WAVECAR_raw" => artifact(RAW_WAVECAR),
            "wannier90_win_raw" => artifact(RAW_WIN),
            "wannier90_eig_raw" => artifact(RAW_EIG),
            "wannier90_mmn_raw_topology_only" => artifact(RAW_MMN),
            "wannier90_amn_raw_prohibited" => artifact(RAW_AMN),
        ),
    ))
end

function stage_rebase_inputs()
    require_raw_vasp_inputs()
    isfile(PREFLIGHT_JSON) || error("VASP_PREFLIGHT_REQUIRED")
    for path in (WIN, EIG, FUTURE_INCAR, REBASE_JSON)
        ispath(path) && error("REFUSE_OVERWRITE_REBASED_INPUT: $(path)")
    end
    raw_win = read(RAW_WIN, String)
    projection_block = r"(?ms)^begin projections\s*$.*?^end projections\s*$"
    length(collect(eachmatch(projection_block, raw_win))) == 1 || error("RAW_WIN_PROJECTION_BLOCK_AMBIGUOUS")
    occursin("Fe:l=0;l=1;l=2", raw_win) || error("FULL_SPD_PROJECTION_MISSING")
    for (field, value) in (("dis_win_min", "-8.0"), ("dis_win_max", "50.0"),
                           ("dis_froz_min", "-8.0"), ("dis_froz_max", "20.0"))
        occursin(Regex("(?m)^" * field * "\\s*=\\s*" * replace(value, "." => "\\.")), raw_win) ||
            error("DIRECT_W50_WIN_CONTRACT_MISSING: $(field)=$(value)")
    end
    cp(RAW_WIN, WIN)
    cp(RAW_EIG, EIG)
    raw_incar = read(joinpath(ROOT, "INCAR"), String)
    occursin(r"(?m)^dis_win_max\s*=\s*50\.0\s*$", raw_incar) || error("DIRECT_W50_INCAR_CONTRACT_MISSING")
    cp(joinpath(ROOT, "INCAR"), FUTURE_INCAR)
    basis = projection_basis()
    basis.num_wannier == 18 || error("REBASED_PROJECTION_WF_COUNT_MISMATCH")
    write_json(REBASE_JSON, Dict(
        "status" => "PASS",
        "projection" => "Fe:l=0;l=1;l=2",
        "spatial_orbitals" => 9,
        "spinor_num_wannier" => basis.num_wannier,
        "raw_mmn_role" => "topology_and_reciprocal_shifts_only",
        "raw_amn_role" => "prohibited; never oracle_amn_file or solver AMN",
        "native_source_incar" => artifact(joinpath(ROOT, "INCAR")),
        "direct_scf_wannier_window" => Dict(
            "dis_win_min_ev" => -8.0,
            "dis_win_max_ev" => 50.0,
            "dis_froz_min_ev" => -8.0,
            "dis_froz_max_ev" => 20.0,
        ),
        "inputs" => Dict(
            "raw_win" => artifact(RAW_WIN), "raw_eig" => artifact(RAW_EIG),
            "raw_mmn_topology_only" => artifact(RAW_MMN), "raw_amn_prohibited" => artifact(RAW_AMN),
            "copied_win" => artifact(WIN), "copied_eig" => artifact(EIG), "copied_incar" => artifact(FUTURE_INCAR),
        ),
    ))
end

function stage_prepare()
    require_rebased_inputs()
    isfile(BAND_REPRESENTATION) && error("REFUSE_EXISTING_IDENTITY_REPRESENTATION")
    config = W.BandRepresentationPreparationConfig(
        construction_policy=:standard,
        wannierization_mode=:ordinary,
        win_file=WIN,
        eig_file=EIG,
        projection_basis=projection_basis(),
        output_hdf5=BAND_REPRESENTATION,
        outer_min_ev=-8.0,
        outer_max_ev=50.0,
        frozen_min_ev=-8.0,
        frozen_max_ev=20.0,
        num_wannier=18,
        degeneracy_tolerance_ev=0.01,
        representation_tolerance=1.0e-10,
        target_center_matching_tolerance=1.0e-7,
        compatibility_policy=:strict,
    )
    result = W.prepare_band_representation(config)
    result.status in (:PASS, :PASS_WITH_WARNINGS, :STANDARD) || error("ORDINARY_PREPARATION_FAILED: $(result.status)")
    write_json(joinpath(ROOT, "$(PREFIX)_prepare.json"), Dict(
        "status" => string(result.status),
        "requested_wannierization_mode" => "ordinary",
        "representation_source" => "identity",
        "symmetry_constraints_applied" => false,
        "representation" => artifact(BAND_REPRESENTATION),
    ))
end

function stage_target()
    target = current_target()
    provenance_file = joinpath(NATIVE_PAW, "native_paw.provenance.h5")
    isfile(provenance_file) || error("NATIVE_PAW_PROVENANCE_MISSING")
    qualification = HDF5.h5open(provenance_file, "r") do handle
        attributes = HDF5.attributes(handle)
        parent = handle["parent_audit"]
        parent_attributes = HDF5.attributes(parent)
        (
            target_passed=Bool(read(attributes["passed"])),
            authority=String(read(attributes["qualification_authority"])),
            parent_policy=String(read(attributes["parent_audit_policy"])),
            target_generalized_norm_max_absolute=Float64(read(attributes["generalized_norm_max_absolute"])),
            parent_audit_status=String(read(parent_attributes["status"])),
            parent_generalized_norm_max_absolute=Float64(read(parent_attributes["generalized_norm_max_absolute"])),
        )
    end
    qualification.target_passed || error("NATIVE_PAW_TARGET_QUALIFICATION_FAILED")
    qualification.authority == "outer_window" ||
        error("NATIVE_PAW_TARGET_AUTHORITY_MISMATCH: $(qualification.authority)")
    qualification.parent_policy == "audit_only" ||
        error("NATIVE_PAW_PARENT_AUDIT_POLICY_MISMATCH: $(qualification.parent_policy)")
    target.target_authority == qualification.authority || error("TARGET_AUTHORITY_BINDING_MISMATCH")
    target.parent_audit_policy == qualification.parent_policy ||
        error("TARGET_PARENT_AUDIT_POLICY_BINDING_MISMATCH")
    write_json(TARGET_JSON, Dict(
        "status" => qualification.target_passed ? "PASS" : "FAIL",
        "target_passed" => qualification.target_passed,
        "target_generalized_norm_max_absolute" => qualification.target_generalized_norm_max_absolute,
        "parent_audit_status" => qualification.parent_audit_status,
        "parent_generalized_norm_max_absolute" => qualification.parent_generalized_norm_max_absolute,
        "target_authority" => qualification.authority,
        "parent_audit_policy" => qualification.parent_policy,
        "construction_policy" => "standard",
        "wannierization_mode" => "ordinary",
        "contract" => Dict(string(name) => clean(getproperty(target, name)) for name in fieldnames(typeof(target))),
        "native_paw_artifacts" => Dict(
            name => artifact(joinpath(NATIVE_PAW, name)) for
            name in ("native_paw.mmn", "native_paw.amn", "native_paw.wannierization.amn", "native_paw.provenance.h5")
        ),
    ))
end

function stage_spn()
    target = current_target()
    result = W.generate_vasp_paw_spn(
        source();
        output_spn_file=SPN,
        provenance_hdf5=SPN_PROVENANCE,
        spin_channel=1,
        require_oracle=false,
        formatted=false,
        execution=operator_execution("spn"),
        target_contract=target,
    )
    result.passed || error("SPN_PHYSICAL_METRIC_QUALITY_FAILURE")
    header = WannierNLQG.IO.read_wannier_spn(SPN; formatted=false)
    (header.num_bands, header.num_kpts) == (64, 1000) || error("SPN_DIMENSION_MISMATCH")
    W.read_vasp_paw_spn_provenance(SPN_PROVENANCE; verify_spn=true)
    write_json(joinpath(ROOT, "$(PREFIX)_spn.json"), Dict(
        "status" => result.passed ? "PASS" : "STANDARD_WARNING",
        "target_contract_sha256" => target.contract_sha256,
        "spn" => artifact(SPN),
        "provenance" => artifact(SPN_PROVENANCE),
    ))
end

function stage_uiu()
    target = current_target()
    result = W.generate_wannier_uiu(W.WannierUIUGenerationConfig(
        construction_policy=:standard,
        source=source(),
        topology_file=target.operator_oracle_mmn_file,
        output_file=UIU,
        scratch_directory=joinpath(ROOT, "$(PREFIX)_uiu_scratch"),
        provenance_json=UIU * ".provenance.json",
        resume=true,
        overwrite=true,
        oracle_mmn_file=target.operator_oracle_mmn_file,
        authoritative_mmn_file=target.operator_oracle_mmn_file,
        require_mmn_oracle=true,
        target_contract=target,
        authoritative_hamiltonian=W.NativeDFTHamiltonian(),
        max_cached_wavefunction_kpoints=CACHE_POINTS,
        execution=operator_execution("uiu"),
    ))
    header = WannierNLQG.IO.read_wannier_uiu_header(UIU; formatted=false)
    (header.num_bands, header.num_kpts) == (64, 1000) || error("UIU_DIMENSION_MISMATCH")
    write_json(joinpath(ROOT, "$(PREFIX)_uiu.json"), Dict(
        "status" => result.passed ? "PASS" : "STANDARD_WARNING",
        "target_contract_sha256" => target.contract_sha256,
        "operator" => artifact(UIU),
        "provenance" => artifact(UIU * ".provenance.json"),
    ); replace=true)
end

function stage_hamiltonian_operator(kind)
    target = current_target()
    output = Dict("uhu" => UHU, "siu" => SIU, "shu" => SHU)[kind]
    generator = getproperty(W, Symbol("generate_wannier_" * kind))
    result = generator(W.WannierHamiltonianOperatorGenerationConfig(
        construction_policy=:standard,
        source=source(),
        topology_file=target.operator_oracle_mmn_file,
        authoritative_mmn_file=target.operator_oracle_mmn_file,
        target_contract=target,
        eig_file=EIG,
        output_file=output,
        provenance_json=output * ".provenance.json",
        spn_file=kind in ("siu", "shu") ? SPN : nothing,
        spn_provenance_file=kind in ("siu", "shu") ? SPN_PROVENANCE : nothing,
        authoritative_hamiltonian=W.NativeDFTHamiltonian(),
        closure_tolerance=1.0e-6,
        formatted=false,
        overwrite=false,
        max_cached_wavefunction_kpoints=CACHE_POINTS,
        execution=operator_execution(kind),
    ))
    result.artifact_published || error("OPERATOR_NOT_PUBLISHED: $(kind)")
    reader = Dict(
        "uhu" => WannierNLQG.IO.read_wannier_uhu_header,
        "siu" => WannierNLQG.IO.read_wannier_siu_header,
        "shu" => WannierNLQG.IO.read_wannier_shu_header,
    )[kind]
    header = reader(output; formatted=false)
    (header.num_bands, header.num_kpts) == (64, 1000) || error("OPERATOR_DIMENSION_MISMATCH: $(kind)")
    write_json(joinpath(ROOT, "$(PREFIX)_$(kind).json"), Dict(
        "status" => result.passed ? "PASS" : "STANDARD_WARNING",
        "target_contract_sha256" => target.contract_sha256,
        "operator" => artifact(output),
        "provenance" => artifact(output * ".provenance.json"),
    ))
end

function result_summary(result)
    artifacts = Dict(
        string(name) => artifact(getproperty(result.artifacts, name)) for name in fieldnames(typeof(result.artifacts))
    )
    restart = result.restart_state
    return Dict(
        "status" => string(result.status),
        "history_count" => length(result.history),
        "steps" => restart === nothing ? nothing : Dict(
            "iteration" => restart.iteration,
            "z_steps" => restart.optimizer_state.z_steps,
            "u_steps" => restart.optimizer_state.u_steps,
        ),
        "input_summary" => clean(result.input_summary),
        "diagnostics" => clean(result.diagnostics),
        "artifacts" => artifacts,
    )
end

function stage_solve()
    for path in (SPN, SPN_PROVENANCE, UIU, UHU, SIU, SHU, UIU * ".provenance.json", UHU * ".provenance.json", SIU * ".provenance.json", SHU * ".provenance.json")
        isfile(path) || error("FULL_PROFILE_INPUT_MISSING: $(path)")
    end
    isfile(TARGET_JSON) || error("TARGET_CONTRACT_MISSING")
    checkpoint1 = joinpath(ROOT, "$(PREFIX)_attempt1_checkpoint.wannierization.h5")
    result1 = W.construct_symmetry_adapted_wannier_functions(build_config(
        max_iterations=2500,
        initialization=:amn,
        checkpoint_hdf5=checkpoint1,
    ))
    summary1 = result_summary(result1)
    write_json(joinpath(ROOT, "$(PREFIX)_attempt1_summary.json"), summary1; replace=true)
    selected = summary1
    selected_attempt = "attempt1"
    if string(result1.status) == "MAX_ITERATIONS"
        result1.restart_state === nothing && error("MAX_ITERATIONS_WITHOUT_RESTART_STATE")
        checkpoint2 = joinpath(ROOT, "$(PREFIX)_attempt2_checkpoint.wannierization.h5")
        result2 = W.construct_symmetry_adapted_wannier_functions(build_config(
            max_iterations=5000,
            initialization=:restart,
            restart_hdf5=checkpoint1,
            checkpoint_hdf5=checkpoint2,
        ))
        selected = result_summary(result2)
        selected_attempt = "attempt2"
        write_json(joinpath(ROOT, "$(PREFIX)_attempt2_summary.json"), selected; replace=true)
    end
    if selected["status"] in ("IO_FAILURE", "INVALID_INPUT", "REPRESENTATION_INCOMPATIBLE", "REPRESENTATION_UNDETERMINED", "SINGULAR_LOCALIZATION", "LOCALIZATION_FAILED")
        terminal_status = selected["status"]
        terminal_diagnostics = JSON3.write(selected["diagnostics"])
        error("SOLVER_TERMINAL_FAILURE: status=$(terminal_status); diagnostics=$(terminal_diagnostics)")
    end
    artifacts = selected["artifacts"]
    for name in ("packed_hdf5", "wannier90_tb", "checkpoint_hdf5")
        haskey(artifacts, name) || error("SOLVER_ARTIFACT_MISSING: $(name)")
        artifacts[name]["exists"] || error("SOLVER_ARTIFACT_NOT_PUBLISHED: $(name)")
    end
    write_json(joinpath(ROOT, "$(PREFIX)_selected_model.json"), Dict(
        "status" => selected["status"],
        "selected_attempt" => selected_attempt,
        "production_eligible" => false,
        "operator_target_contract_sha256" => current_target().contract_sha256,
        "artifacts" => artifacts,
        "numerical_diagnostics" => selected["diagnostics"],
    ))
end

function stage_readback()
    selected_path = joinpath(ROOT, "$(PREFIX)_selected_model.json")
    isfile(selected_path) || error("SELECTED_MODEL_MISSING")
    selected = JSON3.read(read(selected_path, String), Dict{String,Any})
    artifacts = Dict{String,Any}(selected["artifacts"])
    packed = String(artifacts["packed_hdf5"]["path"])
    text_tb = String(artifacts["wannier90_tb"]["path"])
    checkpoint_path = String(artifacts["checkpoint_hdf5"]["path"])
    all(isfile, (packed, text_tb, checkpoint_path)) || error("READBACK_ARTIFACT_MISSING")
    for (name, path) in (("packed_hdf5", packed), ("wannier90_tb", text_tb), ("checkpoint_hdf5", checkpoint_path))
        String(artifacts[name]["sha256"]) == sha256(path) || error("ARTIFACT_HASH_BINDING_MISMATCH: $(name)")
    end
    target = current_target()
    String(selected["operator_target_contract_sha256"]) == target.contract_sha256 ||
        error("SELECTED_TARGET_CONTRACT_HASH_MISMATCH")
    target_json = JSON3.read(read(TARGET_JSON, String), Dict{String,Any})
    String(target_json["contract"]["contract_sha256"]) == target.contract_sha256 ||
        error("FROZEN_TARGET_CONTRACT_HASH_MISMATCH")
    checkpoint = W.read_wannierization_checkpoint_hdf5(checkpoint_path)
    checkpoint.restart_state === nothing && error("CHECKPOINT_ACCEPTED_STATE_MISSING")
    size(checkpoint.wannier_centers_cartesian) == (18, 3) || error("WANNIER_CENTER_SHAPE_MISMATCH")
    bundle = WannierNLQG.IO.read_real_space_operator_bundle(packed)
    bundle.manifest.profile == :full || error("FULL_PROFILE_NOT_PERSISTED")
    length(bundle.operators) == 11 || error("FULL_OPERATOR_INVENTORY_INCOMPLETE")
    for operator in values(bundle.operators)
        all(isfinite, operator.data) || error("NONFINITE_OPERATOR: $(operator.spec.kind)")
    end
    text = WannierNLQG.IO.read_wannier_tb(text_tb)
    text.num_orbitals == 18 || error("TEXT_TB_ORBITAL_COUNT_MISMATCH")
    write_json(joinpath(ROOT, "$(PREFIX)_fresh_readback.json"), Dict(
        "status" => "PASS",
        "profile" => "full",
        "operator_count" => length(bundle.operators),
        "operator_inventory" => sort!(string.(collect(keys(bundle.operators)))),
        "orbitals" => text.num_orbitals,
        "target_contract_sha256" => target.contract_sha256,
        "checkpoint_status" => string(checkpoint.status),
        "packed_hdf5" => artifact(packed),
        "wannier90_tb" => artifact(text_tb),
        "checkpoint" => artifact(checkpoint_path),
    ))
end

function main()
    require_runtime()
    if STAGE == "vasp-preflight"
        stage_vasp_preflight()
    elseif STAGE == "rebase-inputs"
        stage_rebase_inputs()
    elseif STAGE == "prepare"
        stage_prepare()
    elseif STAGE == "target"
        stage_target()
    elseif STAGE == "spn"
        stage_spn()
    elseif STAGE == "uiu"
        stage_uiu()
    elseif STAGE in ("uhu", "siu", "shu")
        stage_hamiltonian_operator(STAGE)
    elseif STAGE == "solve"
        stage_solve()
    elseif STAGE == "readback"
        stage_readback()
    else
        error("UNKNOWN_STAGE: $(STAGE)")
    end
    println(JSON3.write(Dict("stage" => STAGE, "status" => "FINISHED", "time_utc" => string(now(UTC)))))
end

try
    main()
catch exception
    failure = joinpath(ROOT, "$(PREFIX)_failure_$(STAGE)_" * Dates.format(now(UTC), "yyyymmdd_HHMMSS") * ".json")
    write_json(failure, Dict(
        "status" => "HARD_FAILURE",
        "stage" => STAGE,
        "error" => sprint(showerror, exception),
        "backtrace" => sprint(Base.show_backtrace, catch_backtrace()),
        "time_utc" => string(now(UTC)),
    ))
    rethrow()
end
