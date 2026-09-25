# Provenance bookkeeping kept outside the teaching entry point.
using JSON3
using SHA

const FE_INPUTS = ("POSCAR", "POTCAR", "INCAR", "OUTCAR", "WAVECAR",
                   "wannier90.win", "wannier90.eig", "wannier90.mmn")
const FE_MATRIX_INPUTS = ("POSCAR", "OUTCAR", "wannier90.win", "wannier90.eig",
                          "wannier90.mmn", "wannier90.amn")
fe_sha(path) = bytes2hex(open(SHA.sha256, path))

function fe_run_identity(workdir, inputs, matrix_source_kind)
    for name in inputs
        isfile(joinpath(workdir, name)) || error("Same-run Fe input is missing: $name")
    end
    manifest = joinpath(dirname(Base.active_project()), "SOURCE_MANIFEST.tsv")
    isfile(manifest) || error("WannierNLQG source manifest is missing: $manifest")
    return Dict(
        "matrix_source_kind" => matrix_source_kind,
        "package_version" => string(Base.pkgversion(WannierNLQG)),
        "source_manifest_sha256" => fe_sha(manifest),
        "input_sha256" => Dict(name => fe_sha(joinpath(workdir, name)) for name in inputs),
        "julia_version" => string(VERSION), "julia_threads" => Threads.nthreads(),
    )
end
fe_run_identity(workdir) = fe_run_identity(workdir, FE_INPUTS, "native_vasp_paw")
fe_matrix_identity(workdir) = fe_run_identity(workdir, FE_MATRIX_INPUTS, "external_wannier90")

function fe_write_attempt(result, run_identity, output_dir)
    record = merge(run_identity, Dict(
        "status" => string(result.status), "history_count" => length(result.history),
        "accepted_iteration" => result.restart_state === nothing ? nothing :
                                result.restart_state.iteration,
        "artifacts" => Dict(string(name) => getproperty(result.artifacts, name)
                            for name in fieldnames(typeof(result.artifacts))),
    ))
    open(joinpath(output_dir, "attempt1.json"), "w") do io
        JSON3.pretty(io, record)
        println(io)
    end
end
