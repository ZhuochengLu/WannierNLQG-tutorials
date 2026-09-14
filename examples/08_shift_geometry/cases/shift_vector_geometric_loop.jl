isdefined(Main, :ExampleSupport) || include(joinpath(@__DIR__, "..", "..", "ExampleSupport.jl"))

    module CaseKsliceShiftVectorGeometricLoop
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
),
            sampling = KSlice(
                k_mesh=k_mesh,
                spatial_dimension=2,
                origin=(0.0, 0.0, 0.0),
                vector_1=(1.0, 0.0, 0.0),
                vector_2=(0.0, 1.0, 0.0),
            ),
            tasks = [TaskSpec(
                id = "kslice_shift_vector_geometric_loop",
                quantity = "SVK",
                method = "Geometric_Loop",
                physics = GeometryParameters(),
                numerics = GeometryNumerics(
                    denominator_regularization = 0.001,
                    degeneracy_threshold = 0.002,
                    finite_difference_step = 0.0001,
                ),
                observable = KSliceSelection(
                    component=TensorComponent(2, 2, 2),
                    bands=Transition(conduction=[21, 22], valence=[19, 20]),
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
            CaseKsliceShiftVectorGeometricLoop.build_config;
            tutorial_dir=normpath(joinpath(@__DIR__, "..")),
            task_id="kslice_shift_vector_geometric_loop",
            args=ARGS,
            requires_optional=false,
            summary_fields=Dict{String, Any}("calculation" => "K-slice", "mesh" => [200, 200], "component" => [2, 2, 2], "band_selection" => Dict("conduction" => [21, 22], "valence" => [19, 20]), "photon_energy_ev" => nothing),
        )
    end
