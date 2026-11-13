module TutorialModels
using WannierNLQG, LinearAlgebra
include("haldane/HaldaneModel.jl")
include("rice_mele/RiceMeleModel.jl")
include("dirac/DiracModel.jl")
include("dirac/DCModel.jl")
include("graphene/GrapheneModel.jl")

"""Construct the chapter 17 point-orbital model; k is Cartesian in inverse Å."""
function jerk_model(route)
    lattice = Matrix(Diagonal([4.0, 3.0, 3.0]))
    centers = zeros(3, 2)
    if route == "tb"
        blocks = zeros(ComplexF64, 2, 2, 3)
        blocks[:, :, 1] = [0.5 1.0; 1.0 -0.5]
        blocks[2, 1, 2] = 0.5
        blocks[:, :, 3] = blocks[:, :, 2]'
        return RealSpaceTBInput(lattice=lattice, r_vectors=[0 1 -1; 0 0 0; 0 0 0],
            hamiltonian_r=blocks, orbital_positions=centers, source_file=@__FILE__)
    end
    route == "analytic" || error("unknown jerk route")
    h(k, p) = [0.5 1+0.5exp(-4im*k[1]); 1+0.5exp(4im*k[1]) -0.5]
    return AnalyticKInput(hamiltonian=h, num_orbitals=2, lattice=lattice,
        orbital_positions=centers, derivative_method=:automatic, source_file=@__FILE__)
end

"""Supply a native model to the existing TOML reader; identity selects a declared teaching model.

TOML describes task parameters, not executable callbacks. These identities are
local tutorial entry points, not a new WannierNLQG input schema.
"""
function model(identity)
    parts = split(identity, '/')
    family = first(parts)
    if family == "haldane"
        _, route, phase = parts
        p = only(filter(p -> p.name == phase, HaldaneModel.PHASES))
        return route == "tb" ? HaldaneModel.real_space_input(p.mass, p.phi) :
            HaldaneModel.analytic_input(p.mass, p.phi)
    elseif family == "rice_mele"
        _, route, phase = parts
        p = only(filter(p -> p.name == phase, RiceMeleModel.PHASES))
        return route == "tb" ? RiceMeleModel.real_space_input(p.delta, p.mass) :
            RiceMeleModel.analytic_input(p.delta, p.mass)
    elseif family == "dirac"
        _, mass, cutoff = parts
        return DCModel.input(parse(Float64, mass), parse(Float64, cutoff))
    elseif family == "graphene"
        return GrapheneModel.input()
    elseif family == "jerk"
        return jerk_model(parts[2])
    end
    error("unknown tutorial model identity: $identity")
end
end
