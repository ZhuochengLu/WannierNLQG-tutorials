#!/usr/bin/env python3
"""Build the committed inventory of reference numerical evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
entries = []
for path in sorted(ROOT.glob("examples/*/results/reference/*/summary.json")):
    summary = json.loads(path.read_text())
    entries.append({
        "chapter": path.parents[3].name,
        "task_id": summary["task_id"],
        "summary": str(path.relative_to(ROOT)),
        "summary_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "package_version": summary["package_version"],
        "package_commit": summary.get("package_commit"),
        "source_manifest_sha256": summary.get("source_manifest_sha256"),
        "finite_values": summary["finite_values"],
        "output_sha256": summary["output_sha256"],
        "qualification": summary["qualification"],
    })
manifest = {
    "schema": "wanniernlqg-tutorials.reference-results",
    "schema_version": "1.1",
    "package_versions": sorted({entry["package_version"] for entry in entries}),
    "count": len(entries),
    "entries": entries,
}
out = ROOT / "manifests" / "results_manifest.json"
out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(f"RESULTS_MANIFEST_OK count={len(entries)}")
