#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd -P)
archive=${1:?usage: install_fe_bundle.sh ARCHIVE [DESTINATION]}
destination=${2:-"$root/Materials/Fe/vasp_SOC"}
test -d "$destination" || { echo "Destination must exist: $destination" >&2; exit 1; }
test ! -e "$destination/Fe_fixed_full.h5" || { echo "Refusing to overwrite Fe_fixed_full.h5" >&2; exit 1; }
expected_archive=d3384745c0a41ee8a9336c0ad9c8dc0ce4796a4bc6e3f35599eb1e3fe41be2b9
expected_file=8afdfc64742feb920a3ebc4f49fbd571c3f91fd5a111e588db02ed9676fc0115
actual_archive=$(shasum -a 256 "$archive" | awk '{print $1}')
test "$actual_archive" = "$expected_archive" || { echo "Archive SHA-256 mismatch" >&2; exit 1; }
entries=$(tar -tzf "$archive")
test "$entries" = Fe_fixed_full.h5 || { echo "Unexpected archive members" >&2; exit 1; }
scratch=$(mktemp -d "${TMPDIR:-/tmp}/fe-bundle.XXXXXX")
trap 'rm -r "$scratch"' EXIT
tar -xzf "$archive" -C "$scratch"
actual_file=$(shasum -a 256 "$scratch/Fe_fixed_full.h5" | awk '{print $1}')
test "$actual_file" = "$expected_file" || { echo "Bundle SHA-256 mismatch" >&2; exit 1; }
mv "$scratch/Fe_fixed_full.h5" "$destination/Fe_fixed_full.h5"
echo FE_BUNDLE_OK
