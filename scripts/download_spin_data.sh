#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
destination="$root/Materials/GeS/vasp_SOC"
asset=GeS_vasp_SOC_spin_runtime_v1.tar.gz
url="https://github.com/ZhuochengLu/WannierNLQG-tutorials/releases/download/ges-vasp-soc-spin-v1/$asset"
archive=$(mktemp "${TMPDIR:-/tmp}/ges-spin-runtime.XXXXXX.tar.gz")
trap 'rm -f "$archive"' EXIT
curl -fL "$url" -o "$archive"
expected=$(awk '{print $1}' "$destination/OPTIONAL_SPIN_SHA256")
actual=$(shasum -a 256 "$archive" | awk '{print $1}')
test "$expected" = "$actual" || { echo "archive SHA-256 mismatch" >&2; exit 1; }
tar -xzf "$archive" -C "$destination"
python3 - "$destination" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
manifest = json.loads((root / "OPTIONAL_SPIN_FILES.json").read_text())
for item in manifest["files"]:
    path = root / item["path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item["sha256"] or path.stat().st_size != item["bytes"]:
        raise SystemExit(f"optional file verification failed: {path.name}")
print("OPTIONAL_SPIN_DATA_OK")
PY
