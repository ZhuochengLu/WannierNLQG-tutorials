#!/usr/bin/env julia
# Prepare a private tutorial environment from an explicit local WannierNLQG checkout.
# 
# No source path is built into the tutorial project. The user chooses the source;
# package installation and its manifest are confined to the selected environment.
using Pkg
const ROOT=normpath(joinpath(@__DIR__,".."))
source=isempty(ARGS) ? get(ENV,"WANNIERNLQG_SOURCE","") : only(ARGS)
isempty(source) && error("Supply an existing WannierNLQG1.2 checkout: bootstrap.jl SOURCE_DIR")
isfile(joinpath(source,"Project.toml")) || error("source Project.toml missing")
environment=abspath(get(ENV,"WANNIERNLQG_TUTORIAL_ENV",joinpath(ROOT,".runtime","env")))
mkpath(environment)
isfile(joinpath(environment,"Project.toml")) || cp(joinpath(ROOT,"Project.toml"),joinpath(environment,"Project.toml"))
Pkg.activate(environment)
Pkg.develop(PackageSpec(path=abspath(source)))
Pkg.instantiate(;allow_autoprecomp=false,update_registry=false)
using WannierNLQG
v"1.2.0" <= pkgversion(WannierNLQG) < v"1.3.0" || error("WannierNLQG1.2 required")
println("BOOTSTRAP_OK version=",pkgversion(WannierNLQG)," environment=",environment)
