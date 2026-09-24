isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "..", "ExampleSupport.jl"))

module CaseSecondHarmonicGenerationConventional
    using Main.ExampleSupport
    using Main.ExampleSupport.WannierNLQG

    function build_config(; profile="smoke", output_root=nothing, progress_enabled=false)
        Base.pkgversion(WannierNLQG) == v"1.1.0" ||
            error("GeS SHG requires WannierNLQG v1.1.0")
        return TaskConfig(
            model = ModelInput(
                case_root = ExampleSupport.REPOSITORY_ROOT,
                model_file = ExampleSupport.GES_MODEL_FILE,
                real_space_replica_policy = "input",
                wannier_center_convention = "Convention_II",
            ),
            sampling = BZMesh(
                k_mesh = ExampleSupport.integral_mesh(profile),
                spatial_dimension = 3,
            ),
            tasks = [TaskSpec(
                id = "integral_second_harmonic_generation_conventional",
                quantity = "SHG",
                method = "Conventional",
                physics = SHGParameters(
                    photon_energies = collect(range(0.0, 4.0; length=200)),
                    fermi_energy = -2.5,
                    temperature = 0.0,
                    output = :total,
                    response = :both,
                ),
                numerics = SHGNumerics(
                    broadening = 0.04,
                    broadening_type = "Gaussian",
                    low_frequency_broadening = 0.001,
                    intermediate_regularization = 0.001,
                    eta_correction = true,
                    degeneracy_threshold = 1.0e-4,
                ),
                observable = FullTensor(),
            )],
            execution = ExecutionOptions(fourier_backend="direct"),
            output = OutputOptions(
                output_root = String(output_root),
                system_name = "GeS",
                response_output_digits = 17,
                progress_enabled = progress_enabled,
                progress_percent_interval = 5,
            ),
        )
    end
end

if abspath(PROGRAM_FILE) == abspath(@__FILE__)
    Main.ExampleSupport.run_case(
        CaseSecondHarmonicGenerationConventional.build_config;
        tutorial_dir = normpath(joinpath(@__DIR__, "..")),
        task_id = "integral_second_harmonic_generation_conventional",
        args = ARGS,
        summary_fields = Dict{String, Any}(
            "calculation" => "Integral",
            "mesh" => [ExampleSupport.integral_mesh(ExampleSupport.profile_from_args(ARGS))..., 1],
            "photon_energy_ev" => [0.0, 4.0, 200],
            "fermi_energy_ev" => -2.5,
            "temperature_k" => 0.0,
            "response" => "both",
            "output" => "total",
            "broadening_ev" => 0.04,
            "low_frequency_broadening_ev" => 0.001,
            "intermediate_regularization_ev" => 0.001,
            "degeneracy_threshold_ev" => 1.0e-4,
            "component_for_plot" => [2, 2, 2],
        ),
    )
end
