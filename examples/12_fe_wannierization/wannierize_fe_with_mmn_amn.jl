#!/usr/bin/env julia

# Optional ordinary-mode lesson: use complete same-run WIN/EIG/MMN/AMN directly.
# This is a different matrix source from the chapter's published native-PAW run.
using LinearAlgebra
using WannierNLQG
import WannierNLQG.WannierProjection as WP
import WannierNLQG.Wannierization as W
include(joinpath(@__DIR__, "fe_run_record.jl"))

Base.pkgversion(WannierNLQG) == v"1.1.0" || error("WannierNLQG 1.1.0 is required")
BLAS.set_num_threads(1)
length(ARGS) == 2 || error("usage: wannierize_fe_with_mmn_amn.jl MATRIX_DIR NEW_OUTPUT_DIR")
matrix_dir, output_dir = abspath.(ARGS)
isdir(matrix_dir) || error("Matrix directory is missing: $matrix_dir")
ispath(output_dir) && error("Output path already exists: $output_dir")
win, eig, mmn, amn = (joinpath(matrix_dir, "wannier90.$ext")
                      for ext in ("win", "eig", "mmn", "amn"))
all(isfile, (win, eig, mmn, amn)) || error("Same-run WIN/EIG/MMN/AMN are required")
run_identity = fe_matrix_identity(matrix_dir)
basis = WP.build_wannier_projection_basis(win)
basis.num_wannier == 18 || error("Expected 18 spinor Wannier functions")

input = W.WannierizationInputConfig(
    wannierization_mode=:ordinary,
    win_file=win, eig_file=eig, mmn_file=mmn, amn_file=amn,
    matrix_elements=W.ExternalWannier90Matrices(mmn, amn),
    projection_basis=basis, num_wannier=18,
    outer_min_ev=-8.0, outer_max_ev=50.0,
    frozen_min_ev=-8.0, frozen_max_ev=20.0,
    representation_tolerance=1.0e-10,
    target_center_matching_tolerance=1.0e-7,
    compatibility_policy=:strict,
)
solver = W.WannierizationSolverConfig(
    initialization=:amn, z_mix_ratio=0.1, u_mix_ratio=1.0,
    acceleration=W.WannierizationAccelerationConfig(
        strategy=:fixed, schedule=:two_stage,
        disentanglement_max_steps=1000, localization_max_steps=1000,
        constraint_operation_scope=:full,
    ),
    max_iterations=2500, convergence_tolerance=1.0e-10,
    symmetrize_z=false, parallel=:threads,
    random_seed=UInt64(0x6e6c71675f66655),
)
config = W.SymmetryAdaptedWannierizationConfig(
    input=input, solver=solver,
    checkpoint=W.WannierizationCheckpointConfig(
        checkpoint_hdf5=joinpath(output_dir, "attempt1.wannierization.h5"),
        checkpoint_interval=50,
    ),
    runtime=W.WannierizationRuntimeConfig(progress_interval=50),
    output=W.WannierizationOutputConfig(
        profile=:hamiltonian_position,
        tb_output_formats=(:packed_hdf5, :wannier90_tb),
        write_wannier90_tb=true,
    ),
)

mkdir(output_dir)
result = W.construct_symmetry_adapted_wannier_functions(config)
fe_write_attempt(result, run_identity, output_dir)
println("FE_EXTERNAL_SOLVER_FINISHED status=$(result.status); run verify_fe_model.jl next")
