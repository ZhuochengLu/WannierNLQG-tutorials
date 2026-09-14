isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "..", "ExampleSupport.jl"))

    module CaseBandStructure
    using Main.ExampleSupport
    using Main.ExampleSupport.WannierNLQG

    function build_config(; profile="smoke", output_root=nothing, progress_enabled=false)
        segments = ExampleSupport.band_segments(profile)
    return TaskConfig(
        model = ModelInput(
    case_root = ExampleSupport.REPOSITORY_ROOT,
    model_file = ExampleSupport.GES_MODEL_FILE,
    real_space_replica_policy = "input",
    wannier_center_convention = "Convention_II",
),
        sampling = KPath(
            nodes=[
                ("Γ", (0.0, 0.0, 0.0)),
                ("X", (0.5, 0.0, 0.0)),
                ("S", (0.5, 0.5, 0.0)),
                ("Y", (0.0, 0.5, 0.0)),
                ("Γ", (0.0, 0.0, 0.0)),
            ],
            kpoints_per_segment=segments,
            spatial_dimension=2,
        ),
        tasks=[TaskSpec(
            id="band_structure",
            quantity="Band",
            physics=BandParameters(fermi_energy=-2.5),
            numerics=BandNumerics(hermiticity_tolerance=1.0e-10),
        )],
        execution=ExecutionOptions(fourier_backend="direct"),
        output=OutputOptions(
            output_root=String(output_root), system_name="GeS",
            response_output_digits=17, progress_enabled=progress_enabled,
        ),
    )
    end

    end

    if abspath(PROGRAM_FILE) == abspath(@__FILE__)
        Main.ExampleSupport.run_case(
            CaseBandStructure.build_config;
            tutorial_dir=normpath(joinpath(@__DIR__, "..")),
            task_id="band_structure",
            args=ARGS,
            requires_optional=false,
            summary_fields=Dict{String, Any}("calculation" => "K-path", "segments" => [51, 51, 51, 51], "fermi_energy_ev" => -2.5),
        )
    end
