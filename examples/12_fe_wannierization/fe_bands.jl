#!/usr/bin/env julia

# Interpolate bands from the TB exported by this tutorial run, never Fe_tb.dat.
using DelimitedFiles
using JSON3
using SHA
using WannierNLQG

Base.pkgversion(WannierNLQG) == v"1.1.0" || error("WannierNLQG 1.1.0 is required")
length(ARGS) == 1 || error("usage: fe_bands.jl OUTPUT_DIR_FROM_wannierize_fe")
output_dir = abspath(only(ARGS))
root = normpath(joinpath(@__DIR__, "..", ".."))
selected = JSON3.read(read(joinpath(output_dir, "selected_model.json"), String))
selected.profile == "hamiltonian_position" || error("Unexpected solver output profile")
tb = String(selected.artifacts.wannier90_tb.path)
packed = String(selected.artifacts.packed_hdf5.path)
for (path, digest) in ((tb, selected.artifacts.wannier90_tb.sha256),
                       (packed, selected.artifacts.packed_hdf5.sha256))
    relative = relpath(path, output_dir)
    (relative == ".." || startswith(relative, "../")) &&
        error("Selected artifact is outside this run: $path")
    isfile(path) || error("Selected artifact is missing: $path")
    bytes2hex(open(SHA.sha256, path)) == digest || error("Selected artifact hash changed: $path")
end

reference_receipt = JSON3.read(read(joinpath(root, "Materials", "Fe", "vasp_SOC",
                                                "bands", "Fe_vasp_path_receipt.json"), String))
fermi_ev = Float64(reference_receipt.scf_fermi_energy_ev)
bands_root = joinpath(output_dir, "bands")
ispath(bands_root) && error("Bands output already exists: $bands_root")

cfg = TaskConfig(
    model=ModelInput(
        case_root=output_dir, model_file=tb, real_space_operator_bundle_file=packed,
        real_space_replica_policy="auto", wannier_center_convention="Convention_II",
    ),
    sampling=KPath(
        nodes=[("Γ", (0.0, 0.0, 0.0)), ("H", (0.5, -0.5, -0.5)),
               ("P", (0.75, 0.25, -0.25)), ("N", (0.5, 0.0, -0.5)),
               ("Γ", (0.0, 0.0, 0.0))],
        kpoints_per_segment=[201, 201, 201, 201], spatial_dimension=3,
    ),
    tasks=[TaskSpec(
        id="bands", quantity="Band", physics=BandParameters(fermi_energy=fermi_ev),
        numerics=BandNumerics(hermiticity_tolerance=1.0e-10),
    )],
    execution=ExecutionOptions(fourier_backend="direct"),
    output=OutputOptions(output_root=bands_root, system_name="Fe", progress_enabled=true),
)
WannierNLQG.run(cfg)

table = joinpath(bands_root, "bands", "Fe_bands.dat")
data = readdlm(table, comments=true)
size(data) == (801, 22) || error("Expected 801 points and 18 TB bands, got $(size(data))")
all(isfinite, data) || error("Nonfinite TB band value")
receipt = Dict(
    "schema" => "wanniernlqg-tutorials.fe-wannierization-bands",
    "schema_version" => "1.0", "qualification" => "DIAGNOSTIC_ONLY",
    "solver_status" => String(selected.status), "selected_attempt" => String(selected.selected_attempt),
    "tb_sha256" => String(selected.artifacts.wannier90_tb.sha256),
    "reference_table_sha256" => String(reference_receipt.table_sha256),
    "energy_reference_ev" => fermi_ev, "shape" => [801, 18],
    "table_path" => table, "table_sha256" => bytes2hex(open(SHA.sha256, table)),
)
open(joinpath(output_dir, "bands_result.json"), "w") do io
    JSON3.pretty(io, receipt)
    println(io)
end
println("FE_BANDS_DONE path=$table points=801 bands=18")
