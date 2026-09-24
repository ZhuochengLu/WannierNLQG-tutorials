#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd -P)
: "${VASP_NCL:?set VASP_NCL to your licensed vasp_ncl executable}"
: "${MPIEXEC:?set MPIEXEC to the matching MPI launcher}"
ranks=${MPI_RANKS:-4}
test -f "$root/POTCAR" || { echo "Supply your licensed POTCAR; see POTCAR.txt" >&2; exit 1; }
cd "$root"
exec env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  "$MPIEXEC" -n "$ranks" "$VASP_NCL"
