module GrapheneModel

using LinearAlgebra
using WannierNLQG

const BOND_ANGSTROM = 1.42
const HOPPING_EV = -3.0
const HEIGHT_ANGSTROM = 10.0 # Auxiliary cell height; cancels in sheet responses.
const LATTICE = [sqrt(3)*BOND_ANGSTROM/2 3BOND_ANGSTROM/2 0.0;
                -sqrt(3)*BOND_ANGSTROM/2 3BOND_ANGSTROM/2 0.0;
                0.0 0.0 HEIGHT_ANGSTROM]
const CENTERS = [0.0 0.0; 0.0 BOND_ANGSTROM; 0.0 0.0]
const R_VECTORS = [0 -1 0 1 0; 0 0 -1 0 1; 0 0 0 0 0]

"""One spin copy of the two-site, nearest-neighbor pristine MLG model."""
function input()
    h = zeros(ComplexF64, 2, 2, 5)
    h[1, 2, 1] = h[2, 1, 1] = HOPPING_EV
    h[1, 2, 2] = h[1, 2, 3] = HOPPING_EV
    h[2, 1, 4] = h[2, 1, 5] = HOPPING_EV
    RealSpaceTBInput(lattice=LATTICE, r_vectors=R_VECTORS, hamiltonian_r=h,
                    orbital_positions=CENTERS, position_model=:point_orbitals,
                    wannier_center_convention="Convention_II", source_file=@__FILE__)
end

"""Paper Eq. (6a) in its embedded orbital gauge; Cartesian k is in inverse Angstrom."""
function paper_hamiltonian(k)
    a = BOND_ANGSTROM
    f = exp(im*k[2]*a) + 2exp(-im*k[2]*a/2)*cos(sqrt(3)*k[1]*a/2)
    [0.0 HOPPING_EV*f; HOPPING_EV*conj(f) 0.0]
end

"""Periodic Convention-II Hamiltonian used by the runtime, before orbital embedding."""
function periodic_hamiltonian(k)
    off = HOPPING_EV*(1 + exp(-im*dot(k, LATTICE[1, :])) +
                          exp(-im*dot(k, LATTICE[2, :])))
    [0.0 off; conj(off) 0.0]
end

"""Check the gauge conversion, Hermiticity, and known Gamma/M/K energies."""
function check_model()
    for k in ([0.17, -0.23, 0.0], [0.8, 0.31, 0.0])
        p = Diagonal(exp.(im .* (transpose(CENTERS)*k)))
        @assert norm(p' * periodic_hamiltonian(k) * p - paper_hamiltonian(k)) < 1e-13
        @assert ishermitian(periodic_hamiltonian(k))
    end
    b = 2pi*inv(LATTICE)
    for (q, energy) in (([0.0,0.0,0.0],9.0), ([0.5,0.0,0.0],3.0),
                        ([1/3,2/3,0.0],0.0))
        @assert abs(maximum(eigvals(Hermitian(periodic_hamiltonian(b*q))))-energy) < 1e-12
    end
    return true
end

end
