# Scoped migration check: current parser admission, not historical numerical qualification.
using JSON3, SHA, TOML, Dates, LinearAlgebra
include(joinpath(@__DIR__,"..","scripts","tutorial_input.jl"))
const ROOT=normpath(joinpath(@__DIR__,".."))
const OUT=isempty(ARGS) ? joinpath(ROOT,".runtime","input-checks-" * Dates.format(now(),"yyyymmddTHHMMSS")) : abspath(ARGS[1])
ispath(OUT) && error("fresh validation directory required")
mkpath(OUT)
BLAS.set_num_threads(1)
const ROWS=JSON3.read(read(joinpath(ROOT,"manifests","current_inputs.json"),String))
const RESULTS=Any[]

# Save progress after each input, including exact parse/runtime failures.
function save_results()
    open(joinpath(OUT,"results.json"),"w") do io
        JSON3.pretty(io,Dict("package_version"=>string(pkgversion(TutorialInput.WannierNLQG)),
            "source_path"=>pathof(TutorialInput.WannierNLQG),"julia_version"=>string(VERSION),
            "qualification"=>"INPUT_AND_SMALL_RUN_ONLY","rows"=>RESULTS));write(io,'\n')
    end
end

for row in ROWS
    path=joinpath(ROOT,row.input)
    record=Dict{String,Any}("input"=>row.input,"chapter"=>row.chapter,"case"=>row.case,
        "profile"=>row.profile,"sha256"=>bytes2hex(sha256(read(path))))
    try
        TOML.parsefile(path)
        record["toml_syntax"]="PASS"
        input=TutorialInput.read_input(path;check_paths=false)
        isempty(input.pending)||error("pending: $(input.pending)")
        record["resolution"]="PASS"
        try
            TutorialInput.read_input(path)
            record["input_admission"]="PASS"
        catch e
            record["input_admission"]="UNAVAILABLE_INPUT"
            record["admission_error"]=sprint(showerror,e)
        end
    catch e
        record["resolution"]="FAIL"
        record["error"]=sprint(showerror,e)
    end
    push!(RESULTS,record);save_results()
    println("INPUT_CHECK ",row.input," ",get(record,"resolution","FAIL")," ",get(record,"input_admission",""));flush(stdout)
end

if "--run" in ARGS
    for chapter in sort(unique(String.(getproperty.(ROWS,:chapter))))
        # One admitted small consumer per chapter. Optional variants retain individual admission status.
        candidates=filter(r->r["chapter"]==chapter && r["profile"]=="smoke" &&
            get(r,"input_admission","")=="PASS",RESULTS)
        if isempty(candidates)
            println("NO_ADMITTED_SMOKE ",chapter);continue
        end
        selected=first(candidates)
        records=joinpath(OUT,"runs",chapter,selected["case"])
        selected["runtime_records"]=relpath(records,ROOT)
        started=time()
        try
            input=TutorialInput.read_input(joinpath(ROOT,selected["input"]);output_root=joinpath(records,"outputs"))
            result=TutorialInput.WannierNLQG.run_task_input(input;record_directory=records)
            outputs=filter(isfile,result.outputs)
            isempty(outputs)&&error("no numerical output files")
            for path in outputs
                endswith(path,".dat") || continue
                occursin(r"(?i)(^|[\s,])[+-]?(nan|inf)([\s,]|$)",read(path,String)) &&
                    error("nonfinite output token: $path")
            end
            selected["runtime_outputs"]=Dict(relpath(p,ROOT)=>bytes2hex(sha256(read(p))) for p in outputs)
            selected["runtime"]="PASS"
        catch e
            selected["runtime"]="FAIL"
            selected["runtime_error"]=sprint(showerror,e)
        end
        selected["wall_seconds"]=time()-started
        save_results();GC.gc()
        println("SMALL_RUN ",chapter," ",selected["case"]," ",selected["runtime"]);flush(stdout)
    end
end
println("CURRENT_INPUT_VALIDATION_COMPLETE ",OUT)
exit(any(r->get(r,"resolution","")=="FAIL" || get(r,"runtime","")=="FAIL",RESULTS) ? 1 : 0)
