#!/usr/bin/env python3
"""Regenerate chapter READMEs from committed case and result inventories."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
inventory = json.loads((ROOT / "manifests/task_inventory.json").read_text())["tasks"]

chapter_info = {
    "01_band_structure": ("Band structure", "TB bands on Γ-X-S-Y-Γ and a diagnostic comparison with unchanged VASP eigenvalues."),
    "02_integral_charge_responses": ("Integral charge responses", "Frequency-dependent shift and injection charge-current tensors."),
    "03_integral_spin_responses": ("Integral spin responses", "Frequency-dependent rank-4 shift and injection spin-current tensors."),
    "04_kslice_charge_responses": ("K-slice charge responses", "Momentum-resolved real and imaginary charge-response maps at 3.0 eV."),
    "05_kslice_spin_responses": ("K-slice spin responses", "Momentum-resolved rank-4 spin-current maps at 3.0 eV."),
    "06_qg_pairwise": ("Pairwise quantum geometry", "Berry curvature, quantum metric, and their ordered interband counterparts."),
    "07_qg_multipoles": ("Quantum-geometric multipoles", "First and second momentum derivatives and the quantum Christoffel symbol."),
    "08_shift_geometry": ("Shift geometry", "Shift vectors and quantum Hermitian connections from three supported constructions."),
    "09_higher_and_spin_geometry": ("Higher and spin geometry", "Hermitian curvature, triple-phase products, and Zeeman-weighted interband geometry."),
}

index_notes = {
    "03_integral_spin_responses": "Rank-4 order is `(current direction, electric-field direction 1, electric-field direction 2, spin-polarization direction)`; `(2,2,2,2)` selects y-polarized spin carried by y current under yy fields.",
    "05_kslice_spin_responses": "Rank-4 order is `(current direction, electric-field direction 1, electric-field direction 2, spin-polarization direction)`; this chapter selects `(2,2,2,2)`.",
    "07_qg_multipoles": "Derivative indices precede the underlying geometry indices: BCD `(d,a,b)`, BCQ `(d1,d2,a,b)`, QMD `(d,a,b)`, QMQ `(d1,d2,a,b)`. QCS uses `(a,b,c)`.",
    "09_higher_and_spin_geometry": "HCT selects `(2,2,1,2)` on ordered `C1,V`; TPP selects `(2,2,2)` on ordered `C1,C2,V`; Zeeman IBC/IQM select `(1,3)` on ordered `C1,V`.",
}

def metadata_value(path, key):
    if not path.is_file():
        return "n/a"
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*(.*)$", path.read_text())
    return match.group(1).strip() if match else "n/a"

for chapter, (title, description) in chapter_info.items():
    chapter_root = EXAMPLES / chapter
    tasks = [item for item in inventory if item["chapter"] == chapter]
    rows = []
    commands = []
    outputs = []
    optional = False
    for item in tasks:
        case = Path(item["case_file"]).name
        task_id = item["task_id"]
        optional |= item["optional_spin_data"]
        result = chapter_root / "results/reference" / task_id
        summary = json.loads((result / "summary.json").read_text())
        meta = result / "metadata.txt"
        quantity = metadata_value(meta, "quantity")
        method = metadata_value(meta, "method")
        mesh = "×".join(map(str, summary.get("mesh", []))) or "path"
        component = summary.get("component", summary.get("component_for_plot", "full tensor"))
        component = str(component).replace("[", "(").replace("]", ")").replace(" ", "")
        bands = json.dumps(summary.get("band_selection", "all bands"), separators=(",", ":"))
        energy = summary.get("photon_energy_ev", "0-4 (200 points)" if summary.get("calculation") == "Integral" else "n/a")
        rows.append(f"| `{case}` | `{quantity}` | `{method}` | {mesh} | {energy} | `{component}` | `{bands}` | {'yes' if item['optional_spin_data'] else 'no'} |")
        commands.append(f"julia --project=. {item['case_file']} --profile=smoke")
        outputs.append(f"- `{task_id}`: " + ", ".join(f"`{name}`" for name in summary["output_files"]))
    spin_text = ("This chapter requires the optional `GeS.spn`, `GeS.chk`, `GeS.eig`, and `GeS.mmn` release asset. "
                 "If absent, `run.jl` prints `SKIPPED_MISSING_OPTIONAL_DATA` and creates no result."
                 if optional else "This chapter needs only the committed ordinary `GeS_tb.dat` model.")
    note = index_notes.get(chapter, "The component and ordered band selection are explicit in every case file and repeated in `summary.json`.")
    readme = f"""# {title}

{description}

## 1. Physical quantity and method

Each row is one independently executable `TaskConfig`. Integral tasks retain the complete native tensor; the component column is the default visualization selection.

| Case | Quantity | Method | Reference mesh | Photon energy (eV) | Component | Band selection | Optional spin data |
|---|---|---|---:|---:|---|---|---|
{chr(10).join(rows)}

{note}

## 2. Inputs

- Model: `Materials/GeS/vasp_SOC/GeS_tb.dat`.
- Structure and audit inputs: `GeS.win`, `POSCAR`, `INCAR`, `KPOINTS`, and input manifests in the same material directory.
- {spin_text}
- Protected VASP files are not distributed; `POTCAR.txt` records the pseudopotential choices.

## 3. Parameter contract

| Parameter | Reference value |
|---|---|
| Fermi energy / temperature | `-2.5 eV` / `0 K` for optical tasks |
| Broadening | Gaussian, `0.060 eV` for optical tasks |
| Denominator regularization | `0.001 eV` where applicable |
| Finite-difference step | `1e-4 Å^-1` for derivative geometry |
| Degeneracy threshold | `0.002 eV` |
| Bands | `V=[19,20]`, `C1=[21,22]`, `C2=[23,24]` |
| Fourier / centers | `direct` / `Convention_II` |
| Output precision | 17 digits; no tutorial-side numerical reordering or truncation |

The case file is authoritative: parameters irrelevant to a quantity are not artificially applied. `smoke` changes only mesh/path density.

## 4. Run and visualize

```bash
julia --project=. examples/{chapter}/run.jl --profile=smoke
julia --project=. examples/{chapter}/run.jl --profile=reference
julia --project=. scripts/visualize_all.jl
```

Individual smoke commands:

```bash
{chr(10).join(commands)}
```

Existing result directories are never overwritten.

## 5. Output interpretation

{chr(10).join(outputs)}

Every task directory also contains native `metadata.txt` and a tutorial `summary.json` with input/output SHA-256 values. Complex K-slice quantities retain separate real (`_r_`) and imaginary (`_i_`) files; the default figure shows the real part. `raw/`-style quantities retain the package's native stable filenames without renaming.

## 6. Figure-reading guide

K-slice rendering uses the package's periodic-centered `fftshift + transpose` convention. Heat-map color limits use the symmetric 99.5th percentile for presentation and the sidecar records that clipping; numerical files remain unchanged. Integral figures show the declared component. All PNGs are white-background 600 dpi and each PDF/PNG pair has a `.plot.json` audit sidecar.

## 7. Relation to the manuscript

This tutorial follows quantities and parameter choices used in the manuscript workflow, but uses the released ordinary GeS model and a separately audited VASP display reference. It is not a byte-identical reconstruction of the manuscript's SAWF band bundle and is not evidence that manuscript figures were reproduced.

## 8. Qualification limits

Committed outputs are `TUTORIAL_NUMERICAL_EVIDENCE`: finite, hashed, and reproduced with WannierNLQG v1.0.1 at the stated mesh. They are not Physics PASS or Production PASS. Differences between Conventional, Geometric Loop, and Wilson Loop are displayed as method differences, not automatically classified as errors.
"""
    (chapter_root / "README.md").write_text(readme)

if not (EXAMPLES / "10_second_harmonic_generation" / "README.md").is_file():
    raise FileNotFoundError("the hand-authored SHG chapter README is missing")
if not (EXAMPLES / "11_fe_oam_and_linear_response" / "README.md").is_file():
    raise FileNotFoundError("the hand-authored Fe chapter README is missing")
print("CHAPTER_READMES_OK chapters=11 (nine legacy chapters plus SHG and Fe)")
