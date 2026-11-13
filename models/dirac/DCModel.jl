module DCModel
using LinearAlgebra, WannierNLQG
hamiltonian(k,p) = [p.mass p.velocity*(k[1]-im*k[2]); p.velocity*(k[1]+im*k[2]) -p.mass]
function input(mass, cutoff)
 b=cutoff+0.5
 AnalyticKInput(hamiltonian=hamiltonian,num_orbitals=2,lattice=Matrix{Float64}(I,3,3),
  orbital_positions=zeros(3,2),parameters=(mass=mass,velocity=2.0),periodic=false,basis=:point_orbitals,
  derivative_method=:automatic,source_file=@__FILE__,wannier_center_convention="Convention_II",
  evaluation_bounds=((-b,-b,-0.5),(b,b,0.5)))
end
end
