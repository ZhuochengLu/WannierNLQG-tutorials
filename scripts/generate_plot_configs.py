#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

for chapter in sorted(EXAMPLES.glob("[0-9][0-9]_*")):
    if chapter.name == "10_second_harmonic_generation":
        # SHG has native one-file-per-complex-component tables and dedicated configs.
        continue
    results = chapter / "results" / "reference"
    configs = chapter / "plot_configs"
    if not results.is_dir():
        continue
    for task in sorted(path for path in results.iterdir() if path.is_dir()):
        data = sorted(task.glob("*.dat"))
        metadata = task / "metadata.txt"
        if not data:
            continue
        output = {"stem": f"../figures/{task.name}", "formats": ["pdf", "png"]}
        if task.name == "band_structure":
            path = task / "GeS_kpath.json"
            config = {"mode": "single", "reference": {
                "type": "wanniernlqg", "id": "GeS_tb", "label": "GeS ordinary TB",
                "bands": f"../results/reference/{task.name}/{data[0].name}",
                "path": f"../results/reference/{task.name}/{path.name}"},
                "output": output, "ylabel": "$E-E_F$ (eV)"}
        elif task.name.startswith("integral_"):
            component = "yyyy" if "spin_current" in task.name else "yyy"
            config = {"mode": "single", "input": f"../results/reference/{task.name}/{data[0].name}",
                "label": task.name, "components": component, "part": "real",
                "unit": "native output units", "x_window": [0.0, 4.0],
                "panel_size_inches": [4.8, 3.4],
                "curves": {task.name: {"marker": "", "linewidth": 1.6}}, "output": output}
        else:
            real_candidates = [path for path in data if "_r_" in path.name]
            real = real_candidates[0] if real_candidates else data[0]
            panel_title = task.name.replace("kslice_", "").replace("_conventional", "").replace("_", " ").title()
            config = {"mode": "single-map", "metadata": f"../results/reference/{task.name}/metadata.txt",
                "panels": [{"id": "real_part", "real": f"../results/reference/{task.name}/{real.name}",
                    "title": panel_title, "order": 1}],
                "coordinate": "centered", "projection": "intrinsic-plane",
                "periodic_centered": True, "part": "real", "norm": "diverging",
                "percentile": 99.5, "cmap": "RdBu_r", "colorbar_label": "native output units",
                "output": output}
        write(configs / f"{task.name}.json", config)
band = EXAMPLES / "01_band_structure"
if (band / "results/reference/band_structure/GeS_bands.dat").is_file():
    write(band / "plot_configs/vasp_band.json", {
        "mode": "single",
        "reference": {
            "type": "vasp_eigenval_kpoints", "id": "vasp", "label": "VASP",
            "eigenval": "../../../Materials/GeS/vasp_SOC/EIGENVAL",
            "kpoints": "../../../Materials/GeS/vasp_SOC/KPOINTS.band_path",
            "poscar": "../../../Materials/GeS/vasp_SOC/POSCAR",
            "energy_reference_ev": -2.5, "energy_unit": "ev",
            "energy_convention": "absolute",
            "kpoint_coordinate_convention": "fractional_crystal", "spin_channel": 1},
        "energy_window": [-5.0, 5.0],
        "output": {"stem": "../figures/GeS_vasp_band", "formats": ["pdf", "png"]}})
    if (band / "derived/GeS_vasp_band_path.dat").is_file():
        write(band / "plot_configs/band_comparison.json", {
            "mode": "compare", "comparison_audit": "display_only",
            "diagnostic_banner": "DIAGNOSTIC DISPLAY ONLY",
            "reference": {
                "type": "table", "id": "vasp", "label": "VASP",
                "data": "../derived/GeS_vasp_band_path.dat",
                "path": "../derived/GeS_vasp_band_path.json", "x_column": 0,
                "energy_columns": {"start": 1, "stop": 145},
                "energy_unit": "ev", "energy_convention": "absolute"},
            "models": [{
                "type": "wanniernlqg", "id": "GeS_tb", "label": "GeS ordinary TB",
                "bands": "../results/reference/band_structure/GeS_bands.dat",
                "path": "../results/reference/band_structure/GeS_kpath.json"}],
            "energy_window": [-5.0, 5.0],
            "output": {"stem": "../figures/GeS_band_comparison", "formats": ["pdf", "png"]}})

print("PLOT_CONFIGS_OK")
