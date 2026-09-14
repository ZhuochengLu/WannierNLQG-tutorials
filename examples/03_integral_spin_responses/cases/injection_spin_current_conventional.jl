isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "..", "ExampleSupport.jl"))

    module CaseIntegralInjectionSpinCurrentConventional
    using Main.ExampleSupport
    using Main.ExampleSupport.WannierNLQG

    function build_config(; profile="smoke", output_root=nothing, progress_enabled=false)
        k_mesh = ExampleSupport.integral_mesh(profile)
        return TaskConfig(
            model = ModelInput(
    case_root = ExampleSupport.REPOSITORY_ROOT,
    model_file = ExampleSupport.GES_MODEL_FILE,
    seedname = ExampleSupport.GES_SEED_PREFIX,
    real_space_replica_policy = "input",
    wannier_center_convention = "Convention_II",
),
            sampling = BZMesh(k_mesh=k_mesh, spatial_dimension=2),
            tasks = [TaskSpec(
                id = "integral_injection_spin_current_conventional",
                quantity = "ISC",
                method = "Conventional",
                physics = OpticalParameters(
                    photon_energies=collect(range(0.0, 4.0; length=200)),
                    fermi_energy=-2.5,
                    temperature=0.0,
                ),
                numerics = OpticalNumerics(
                    broadening = 0.060,
                    broadening_type = "Gaussian",
                    transition_window_factor = 5.0,
                    denominator_regularization = 0.001,
                    degeneracy_threshold = 0.002,
                    band_window_size = -1,
                ),
                observable = FullTensor(),
            )],
            execution = ExecutionOptions(fourier_backend="direct"),
            output = OutputOptions(
                output_root=String(output_root),
                system_name="GeS",
                response_output_digits=17,
                progress_enabled=progress_enabled,
                progress_percent_interval=5,
            ),
        )
    end

    end

    if abspath(PROGRAM_FILE) == abspath(@__FILE__)
        Main.ExampleSupport.run_case(
            CaseIntegralInjectionSpinCurrentConventional.build_config;
            tutorial_dir=normpath(joinpath(@__DIR__, "..")),
            task_id="integral_injection_spin_current_conventional",
            args=ARGS,
            requires_optional=true,
            summary_fields=Dict{String, Any}("calculation" => "Integral", "mesh" => [100, 100, 1], "component_for_plot" => [2, 2, 2, 2], "fermi_energy_ev" => -2.5, "temperature_k" => 0.0),
        )
    end
