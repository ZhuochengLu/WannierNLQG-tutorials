isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "..", "ExampleSupport.jl"))

    module CaseKsliceZeemanInterbandQuantumMetricConventional
    using Main.ExampleSupport
    using Main.ExampleSupport.WannierNLQG

    function build_config(; profile="smoke", output_root=nothing, progress_enabled=false)
        k_mesh = ExampleSupport.kslice_mesh(profile)
        return TaskConfig(
            model = ModelInput(
    case_root = ExampleSupport.REPOSITORY_ROOT,
    model_file = ExampleSupport.GES_MODEL_FILE,
    real_space_replica_policy = "input",
    wannier_center_convention = "Convention_II",
    spin_enabled = true,
    spin_file = joinpath(ExampleSupport.MATERIAL_ROOT, "GeS.spn"),
    checkpoint_file = joinpath(ExampleSupport.MATERIAL_ROOT, "GeS.chk"),
    spin_file_formatted = false,
),
            sampling = KSlice(
                k_mesh=k_mesh,
                spatial_dimension=2,
                origin=(0.0, 0.0, 0.0),
                vector_1=(1.0, 0.0, 0.0),
                vector_2=(0.0, 1.0, 0.0),
            ),
            tasks = [TaskSpec(
                id = "kslice_zeeman_interband_quantum_metric_conventional",
                quantity = "ZIQMK",
                method = "Conventional",
                physics = GeometryParameters(),
                numerics = GeometryNumerics(
                    denominator_regularization = 0.001,
                    degeneracy_threshold = 0.002,
                ),
                observable = KSliceSelection(
                    component=TensorComponent(1, 3),
                    bands=InterbandGroups(first=[21, 22], second=[19, 20]),
                ),
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
            CaseKsliceZeemanInterbandQuantumMetricConventional.build_config;
            tutorial_dir=normpath(joinpath(@__DIR__, "..")),
            task_id="kslice_zeeman_interband_quantum_metric_conventional",
            args=ARGS,
            requires_optional=true,
            summary_fields=Dict{String, Any}("calculation" => "K-slice", "mesh" => [200, 200], "component" => [1, 3], "band_selection" => Dict("first" => [21, 22], "second" => [19, 20]), "photon_energy_ev" => nothing),
        )
    end
