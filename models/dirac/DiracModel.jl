module DiracModel
using LinearAlgebra
using WannierNLQG

const VELOCITY = 2.0 # eV Angstrom: this is hbar times a physical velocity.
const MASSES = (positive = 0.2, negative = -0.2)
const EVALUATION_BOUNDS = ((-2.5, -2.5, -0.5), (2.5, 2.5, 0.5))

"""Single cone in a fixed orthogonal basis; Cartesian k is in inverse Angstrom."""
hamiltonian(k, p) = [p.mass p.velocity * (k[1] - im * k[2]);
                     p.velocity * (k[1] + im * k[2]) -p.mass]

function input(mass; lattice = Matrix{Float64}(I, 3, 3))
    AnalyticKInput(
        hamiltonian = hamiltonian, num_orbitals = 2,
        lattice = lattice, orbital_positions = zeros(3, 2),
        parameters = (mass = mass, velocity = VELOCITY),
        periodic = false, basis = :point_orbitals,
        derivative_method = :automatic, source_file = @__FILE__,
        wannier_center_convention = "Convention_II",
        evaluation_bounds = EVALUATION_BOUNDS,
    )
end

const MAIN_CASES = [
    (id = "$(family)_$(phase)", family = family, mass = mass,
     cutoff = 1.0, mesh = 401, gamma = 0.02)
    for (phase, mass) in pairs(MASSES) for family in ("hall", "optical")
]
const SCAN_CASES = vcat(
    [(id = "$(family)_positive_n$(n)", family = family, mass = 0.2,
      cutoff = 1.0, mesh = n, gamma = 0.02)
     for n in (201, 801) for family in ("hall", "optical")],
    [(id = "$(family)_positive_k$(tag)", family = family, mass = 0.2,
      cutoff = k, mesh = n, gamma = 0.02)
     for (tag, k, n) in (("025", 0.25, 101), ("050", 0.5, 201), ("200", 2.0, 801))
     for family in ("hall", "optical")],
    [(id = "$(family)_positive_g001", family = family, mass = 0.2,
      cutoff = 1.0, mesh = 801, gamma = 0.01)
     for family in ("hall", "optical")],
)
end
