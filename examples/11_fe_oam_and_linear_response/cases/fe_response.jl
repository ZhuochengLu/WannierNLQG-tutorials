isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "..", "ExampleSupport.jl"))
using Main.ExampleSupport
using Main.ExampleSupport.WannierNLQG

const FE_ROOT = joinpath(ExampleSupport.REPOSITORY_ROOT, "Materials", "Fe", "vasp_SOC")
const FE_TB = joinpath(FE_ROOT, "Fe_tb.dat")
const FE_BUNDLE = get(ENV, "FE_OPERATOR_BUNDLE", joinpath(FE_ROOT, "Fe_fixed_full.h5"))
const FERMI_EV = 5.7156290716733436
const BUNDLE_SHA = "8afdfc64742feb920a3ebc4f49fbd571c3f91fd5a111e588db02ed9676fc0115"
const TB_SHA = "5e19a8258741f4c4555bb47d2dedc597673972f4f1faf683c44c1ce034949714"
const TERMS = ("conventional", "projector")
const TEMPS = ("T000", "T300")
const TASKS = vcat(
    ["$(family)_$(method)_$(temp)" for family in ("oam", "linear_transport", "linear_optical") for method in TERMS for temp in TEMPS],
    ["berry_sos_occupied_xy", "berry_transport_equivalent_xy"],
)

function build_config(task_id; profile="smoke", output_root=nothing, progress_enabled=false)
    Base.pkgversion(WannierNLQG) == v"1.1.0" || error("Fe tutorial requires WannierNLQG v1.1.0")
    ExampleSupport.file_sha256(FE_TB) == TB_SHA || error("FE_TB_IDENTITY_MISMATCH")
    isfile(FE_BUNDLE) || error("FE_BUNDLE_MISSING: see Materials/Fe/vasp_SOC/README.md")
    ExampleSupport.file_sha256(FE_BUNDLE) == BUNDLE_SHA || error("FE_BUNDLE_IDENTITY_MISMATCH")
    task_id in TASKS || error("unknown Fe task $(task_id)")
    berry = startswith(task_id, "berry_")
    method = occursin("_projector_", task_id) ? "Projector" : "Conventional"
    temp = occursin("_T300", task_id) ? 300.0 : 0.0
    rates = SeparateRelaxation(gamma_intra_ev=0.05, gamma_inter_ev=0.05)
    numerics = temp == 0.0 ? LinearResponseNumerics(
        fermi_surface=FermiSurfaceBroadening(kind=:gaussian, eta_fs_ev=0.05),
        gap_tolerance=1.0e-10,
    ) : nothing
    if startswith(task_id, "oam_")
        quantity = "orbital_magnetization"
        physics = OrbitalMagnetizationParameters(
            fermi_energies=[FERMI_EV], temperature=temp,
            input_semantics=:projected_energy_overlap,
        )
        numerics = OrbitalNumerics(gap_tolerance=1.0e-10)
        observable = FullTensor()
    elseif startswith(task_id, "linear_transport_") || task_id == "berry_transport_equivalent_xy"
        quantity = "linear_transport"
        physics = LinearTransportParameters(
            fermi_energies=[FERMI_EV], temperature=temp, relaxation=rates,
        )
        observable = berry ? KSliceSelection(component=TensorComponent(1, 2), bands=AllBands()) : FullTensor()
    elseif startswith(task_id, "linear_optical_")
        quantity = "linear_optical_response"
        physics = LinearOpticalResponseParameters(
            photon_energies=collect(0.0:0.02:8.0),
            fermi_energy=FERMI_EV, temperature=temp, relaxation=rates,
        )
        observable = FullTensor()
    else
        quantity = "berry_curvature"
        physics = GeometryParameters(fermi_energy=FERMI_EV, temperature=0.0)
        numerics = GeometryNumerics(denominator_regularization=0.001)
        observable = KSliceSelection(component=TensorComponent(1, 2), bands=OccupiedBands())
    end
    sampling = berry ? KSlice(
        k_mesh=profile == "reference" ? (200, 200) : (4, 4),
        spatial_dimension=3,
        origin=(0.0, 0.0, 0.0),
        vector_1=(-0.5, 0.5, 0.5),
        vector_2=(0.5, 0.5, -0.5),
    ) : BZMesh(
        k_mesh=profile == "reference" ? (40, 40, 40) : (2, 2, 2),
        spatial_dimension=3,
    )
    return TaskConfig(
        model=ModelInput(
            case_root=FE_ROOT, model_file=FE_TB,
            real_space_operator_bundle_file=FE_BUNDLE,
            real_space_replica_policy="auto",
            wannier_center_convention="Convention_II",
        ),
        sampling=sampling,
        tasks=[TaskSpec(
            id=task_id, quantity=quantity, method=method,
            physics=physics, numerics=numerics, observable=observable,
        )],
        execution=ExecutionOptions(fourier_backend="direct"),
        output=OutputOptions(
            output_root=String(output_root), system_name="Fe",
            response_output_digits=14, progress_enabled=progress_enabled,
        ),
    )
end

function main(args)
    task_args = filter(arg -> startswith(arg, "--task="), args)
    length(task_args) == 1 || error("usage: fe_response.jl --task=TASK --profile=smoke|reference")
    task_id = split(only(task_args), "="; limit=2)[2]
    profile_args = filter(arg -> !startswith(arg, "--task="), args)
    profile = ExampleSupport.profile_from_args(profile_args)
    ExampleSupport.run_case(
        (; kwargs...) -> build_config(task_id; kwargs...);
        tutorial_dir=normpath(joinpath(@__DIR__, "..")),
        task_id=task_id, args=profile_args,
        input_files=Dict("Fe_tb.dat" => FE_TB, "Fe_fixed_full.h5" => FE_BUNDLE),
        retain_outputs=startswith(task_id, "linear_optical_") ?
            Set("linear_optical_response_$(term).dat" for term in
                ("drude", "quantum_metric", "berry_curvature", "total")) : nothing,
        qualification="DIAGNOSTIC_ONLY",
        summary_fields=Dict{String, Any}(
            "source_tree_sha256" => WannierNLQG.IO.release_tree_sha256(),
            "mesh" => startswith(task_id, "berry_") ?
                [profile == "reference" ? 200 : 4, profile == "reference" ? 200 : 4] :
                fill(profile == "reference" ? 40 : 2, 3),
            "fermi_energy_ev" => FERMI_EV,
            "physics_status" => "HOLD",
            "production_eligible" => false,
            "wannierization_status" => "MAX_ITERATIONS",
        ),
    )
end

abspath(PROGRAM_FILE) == abspath(@__FILE__) && main(ARGS)
