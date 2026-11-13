module RiceMeleModel

using LinearAlgebra
using WannierNLQG

const T = -1.0
const A_ANGSTROM = 4.0
const AREA_ANGSTROM2 = 9.37
const LATTICE = Matrix(Diagonal([A_ANGSTROM, sqrt(AREA_ANGSTROM2), sqrt(AREA_ANGSTROM2)]))
const CENTERS = [0.0 A_ANGSTROM / 2; 0.0 0.0; 0.0 0.0]
const R_VECTORS = [0 -1 1; 0 0 0; 0 0 0]
const PHASES = (
    (name = "polar", delta = -0.83, mass = -0.45),
    (name = "reversed", delta = -0.83, mass = 0.45),
    (name = "ssh", delta = -0.83, mass = 0.0),
    (name = "ionic", delta = 0.0, mass = -0.45),
)

intra(delta) = (T + delta) / 2
inter(delta) = (T - delta) / 2

"""R-only hopping blocks for two orthogonal point orbitals."""
function hopping_blocks(delta, mass)
    h = zeros(ComplexF64, 2, 2, 3)
    h[:, :, 1] = [mass intra(delta); intra(delta) -mass]
    h[1, 2, 2] = inter(delta)
    h[2, 1, 3] = inter(delta)
    return h
end

function real_space_input(delta, mass)
    RealSpaceTBInput(
        lattice = LATTICE,
        r_vectors = R_VECTORS,
        hamiltonian_r = hopping_blocks(delta, mass),
        orbital_positions = CENTERS,
        position_model = :point_orbitals,
        wannier_center_convention = "Convention_II",
        source_file = @__FILE__,
    )
end

"""Direct closed-form Convention-II matrix; k is Cartesian in inverse Angstrom."""
function analytic_hamiltonian(k, p)
    phase = k[1] * p.a
    off = (p.t + p.delta) / 2 + (p.t - p.delta) / 2 * exp(-im * phase)
    return [p.mass off; conj(off) -p.mass]
end

function analytic_input(delta, mass)
    p = (t = T, delta = delta, mass = mass, a = A_ANGSTROM)
    AnalyticKInput(
        hamiltonian = analytic_hamiltonian,
        num_orbitals = 2,
        lattice = LATTICE,
        orbital_positions = CENTERS,
        parameters = p,
        periodic = true,
        basis = :point_orbitals,
        derivative_method = :automatic,
        source_file = @__FILE__,
        wannier_center_convention = "Convention_II",
    )
end

function hopping_hamiltonian(k, delta, mass)
    h = hopping_blocks(delta, mass)
    result = zeros(ComplexF64, 2, 2)
    for j in axes(R_VECTORS, 2)
        displacement = transpose(LATTICE) * R_VECTORS[:, j]
        result .+= h[:, :, j] .* exp(im * dot(k, displacement))
    end
    return result
end

energy(k, delta, mass) = sqrt(T^2 * cos(k * A_ANGSTROM / 2)^2 +
                              delta^2 * sin(k * A_ANGSTROM / 2)^2 + mass^2)

end
