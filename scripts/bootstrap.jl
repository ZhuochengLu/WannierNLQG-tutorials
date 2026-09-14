#!/usr/bin/env julia
using Pkg
const ROOT = normpath(joinpath(@__DIR__, ".."))
Pkg.activate(ROOT)
Pkg.instantiate()
using WannierNLQG
version = Base.pkgversion(WannierNLQG)
version == v"1.0.1" || error("expected WannierNLQG v1.0.1, got $(version)")
println("BOOTSTRAP_OK WannierNLQG=$(version) Julia=$(VERSION)")
