# GeS VASP-SOC inputs

This directory contains the redistributable inputs used by the tutorials. `GeS_tb.dat`
is the ordinary 32-orbital spinor tight-binding model used at runtime. `GeS.win` records
the 14 x 10 x 1 source mesh, projections, windows, lattice, atoms, and k points.

`EIGENVAL`, `KPOINTS.band_path`, and `POSCAR` provide the native VASP band reference.
The supplied `KPOINTS` belongs to the 14 x 10 x 1 uniform source calculation; the band
path is stored separately as `KPOINTS.band_path`.

POTCAR, WAVECAR, construction intermediates, and OUTCAR are not distributed. OUTCAR is
excluded because its k-point inventory does not correspond to the supplied line-mode
EIGENVAL. See `POTCAR.txt` for the licensed dataset identifiers.
