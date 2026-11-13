# Single-rank chapter replay; use the exact current source pin in valley_input.toml.
# Chapter-specific adapter: one declared Cartesian region per ordinary public TaskConfig.
using WannierNLQG, TOML, JSON3, SHA, LinearAlgebra
include(joinpath(@__DIR__,"..","..","models","graphene","GrapheneModel.jl"))
"""Reject removed kernel measure options in the chapter-specific TOML before execution."""
function reject_removed_measure_options(document)
    for (key, value) in document
        key in ("response_measure", "sheet_axes", "effective_thickness_angstrom") &&
            throw(ArgumentError("$key is no longer supported; periodic responses are volume normalized. Apply any stated surface conversion in postprocessing."))
        value isa AbstractDict && reject_removed_measure_options(value)
        if value isa AbstractVector
            for item in value
                item isa AbstractDict && reject_removed_measure_options(item)
            end
        end
    end
    return nothing
end

function main(args)
    options=Dict("input"=>joinpath(@__DIR__,"valley_input.toml"),"output"=>"","batch"=>"turnover-base_new30","worker"=>"0","workers"=>"1","check"=>"false")
    for arg in args
        startswith(arg,"--")&&occursin('=',arg)||error("Use --input=FILE --batch=NAME|all --output=NEW_DIR [--check=true] [--worker=0 --workers=6]")
        key,value=split(arg[3:end],'=';limit=2);haskey(options,key)||error("Unknown option: $key");options[key]=value
    end
    config=TOML.parsefile(options["input"]);reject_removed_measure_options(config);physics=config["physics"];num=config["numerics"];integration=config["integration"]
    source=bytes2hex(sha256(read(joinpath(Base.pkgdir(WannierNLQG),"SOURCE_MANIFEST.tsv"))))
    source==config["reproduction"]["source_manifest_sha256"]||error("Loaded package source does not match the current replay source pinned in valley_input.toml; supplied data retain separate recorded identities")
    model_path=joinpath(@__DIR__,"..","..","models","graphene","GrapheneModel.jl")
    bytes2hex(sha256(read(model_path)))==config["reproduction"]["model_sha256"]||error("Model identity mismatch")
    target=Float64.(config["spectrum"]["target_energies_ev"])
    length(target)==length(unique(target))==84&&issorted(target)||error("Expected84unique ordered target frequencies")
    declared=[Float64(e) for b in config["batches"] for e in b["energies_ev"]]
    length(declared)==length(unique(declared))==99||error("Expected32disjoint vectors with99declared values")
    all(e->e in declared,target)||error("Target frequency missing from vector plan")
    length(config["batches"])==32&&length(config["regions"])==6||error("Expected32vectors and6regions")
    sum(r["max_evaluations"] for r in config["regions"][1:3])==sum(r["max_evaluations"] for r in config["regions"][4:6])==integration["per_original_valley_per_vector_max_evaluations"]||error("Per-valley vector budget mismatch")
    GrapheneModel.check_model();BLAS.set_num_threads(1)
    Threads.nthreads()==1||error("Use one Julia thread for this adaptive chapter driver")
    worker=parse(Int,options["worker"]);workers=parse(Int,options["workers"]);0<=worker<workers||error("Invalid worker index")
    batches=[b for(i,b)in enumerate(config["batches"])if (i-1)%workers==worker&&(options["batch"]=="all"||b["id"]==options["batch"])];isempty(batches)&&error("No selected batch")
    cfgs=Any[]
    for batch in batches,region in config["regions"]
        cfg=TaskConfig(model=GrapheneModel.input(),sampling=KRegion(lower=Tuple(region["lower"]),upper=Tuple(region["upper"]),k_mesh=(4,4)),
          tasks=[TaskSpec(id="thg",quantity="THG",method="Conventional",
            physics=THGParameters(photon_energies=Float64.(batch["energies_ev"]),fermi_energy=physics["fermi_energy_ev"],temperature=physics["temperature_k"],formulation=:both,response=:both,output=:both),
            numerics=Numerics(prescription=Symbol(num["prescription"]),broadening_type=num["broadening_type"],broadening=num["broadening"],low_frequency_broadening=num["low_frequency_broadening"],intermediate_regularization=num["intermediate_regularization"],eta_correction=num["eta_correction"],occupation_derivative_mode=Symbol(num["occupation_derivative_mode"])),observable=TensorComponents(TensorComponent(2,2,2,2)))],
          execution=ExecutionOptions(fourier_backend="direct",integration_algorithm=HAdaptiveCubature(atol=integration["atol"],rtol=integration["rtol"],max_evaluations=region["max_evaluations"],initial_divisions=integration["initial_divisions"])),
          output=OutputOptions(output_root=joinpath(abspath(options["output"]),batch["id"],region["id"]),system_name="mlg",response_output_digits=17,progress_enabled=false))
        push!(cfgs,(batch["id"],region["id"],cfg))
    end
    if options["check"]=="true"
        println("VALLEY_INPUT_CHECKED configs=$(length(cfgs)) source=$source target=84 declared=99; no response integration executed")
        return
    end
    isempty(options["output"])&&error("Supply --output=NEW_DIRECTORY")
    ispath(options["output"])&&error("Refusing existing output directory");mkpath(options["output"]);records=[]
    for (batch,region,cfg)in cfgs
        result=WannierNLQG.run(cfg);child=only(result.task_results)
        push!(records,Dict("batch"=>batch,"region"=>region,"outputs"=>[Dict("path"=>relpath(p,options["output"]),"sha256"=>bytes2hex(sha256(read(p)))) for p in child.outputs]))
        open(io->JSON3.pretty(io,Dict("output_normalization"=>"three_dimensional_volume","model_periodic_expected"=>true,"source_manifest_sha256"=>source,"model_sha256"=>config["reproduction"]["model_sha256"],"input_sha256"=>bytes2hex(sha256(read(options["input"]))),"records"=>records)),joinpath(options["output"],"index.json"),"w")
    end
end
main(ARGS)
