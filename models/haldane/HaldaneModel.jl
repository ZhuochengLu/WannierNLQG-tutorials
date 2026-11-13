module HaldaneModel

using LinearAlgebra
using WannierNLQG

const T1 = -1.0
const T2 = 0.15
const LZ_ANGSTROM = 20.0
const LATTICE = [1.0 0.0 0.0; 0.5 sqrt(3) / 2 0.0; 0.0 0.0 LZ_ANGSTROM]
const A1 = vec(LATTICE[1, :])
const A2 = vec(LATTICE[2, :])
const CENTERS = hcat(zeros(3), (A1 + A2) / 3)
const DIRECTED_SECOND_NEIGHBORS = ((1, 0, 0), (-1, 1, 0), (0, -1, 0))
const R_VECTORS = ((0, 0, 0), (1, 0, 0), (-1, 0, 0),
                   (0, 1, 0), (0, -1, 0), (-1, 1, 0), (1, -1, 0))
const PHASES = (
    (name = "topological", mass = 0.2, phi = pi / 2, chern = 1),
    (name = "trivial", mass = 1.0, phi = pi / 2, chern = 0),
    (name = "reversed", mass = 0.2, phi = -pi / 2, chern = -1),
)

neg(r) = Tuple(-x for x in r)

"""All home-cell and Hermitian partner blocks in the R-only Bloch convention."""
function hoppings(mass, phi)
    blocks = zeros(ComplexF64, 2, 2, length(R_VECTORS))
    index = Dict(r => i for (i, r) in enumerate(R_VECTORS))
    blocks[1, 1, index[(0, 0, 0)]] = -mass
    blocks[2, 2, index[(0, 0, 0)]] = mass
    for r in ((0, 0, 0), (-1, 0, 0), (0, -1, 0))
        blocks[1, 2, index[r]] += T1
        blocks[2, 1, index[neg(r)]] += T1
    end
    for r in DIRECTED_SECOND_NEIGHBORS
        blocks[1, 1, index[r]] += T2 * cis(-phi)
        blocks[1, 1, index[neg(r)]] += T2 * cis(phi)
        blocks[2, 2, index[r]] += T2 * cis(phi)
        blocks[2, 2, index[neg(r)]] += T2 * cis(-phi)
    end
    return reduce(hcat, collect.(R_VECTORS)), blocks
end

function real_space_input(mass, phi)
    vectors, blocks = hoppings(mass, phi)
    return RealSpaceTBInput(
        lattice = LATTICE,
        r_vectors = vectors,
        hamiltonian_r = blocks,
        orbital_positions = CENTERS,
        position_model = :point_orbitals,
        wannier_center_convention = "Convention_II",
        source_file = @__FILE__,
    )
end

"""Independent closed-form H(k), with Cartesian k in inverse Angstrom."""
function analytic_hamiltonian(k, p)
    u = dot(k, p.a1)
    v = dot(k, p.a2)
    off_diagonal = p.t1 * (1 + exp(-im * u) + exp(-im * v))
    aa_sum = cos(u - p.phi) + cos(v - u - p.phi) + cos(-v - p.phi)
    bb_sum = cos(u + p.phi) + cos(v - u + p.phi) + cos(-v + p.phi)
    aa = -p.mass + 2p.t2 * aa_sum
    bb = p.mass + 2p.t2 * bb_sum
    return [aa off_diagonal; conj(off_diagonal) bb]
end

function analytic_input(mass, phi)
    p = (mass = mass, phi = phi, t1 = T1, t2 = T2, a1 = copy(A1), a2 = copy(A2))
    return AnalyticKInput(
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

function hopping_hamiltonian(k, mass, phi)
    vectors, blocks = hoppings(mass, phi)
    result = zeros(ComplexF64, 2, 2)
    for j in axes(vectors, 2)
        displacement = transpose(LATTICE) * vectors[:, j]
        result .+= blocks[:, :, j] .* exp(im * dot(k, displacement))
    end
    return result
end

function cartesian_k(u, v)
    reciprocal_rows = 2pi * transpose(inv(LATTICE))
    return transpose(reciprocal_rows) * [u, v, 0.0]
end

critical_mass(phi) = 3sqrt(3) * T2 * abs(sin(phi))

end
