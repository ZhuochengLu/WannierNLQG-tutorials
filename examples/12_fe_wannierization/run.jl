#!/usr/bin/env julia

using DelimitedFiles
using JSON3
using SHA
using WannierNLQG

const ROOT = normpath(joinpath(@__DIR__, "..", ".."))
const MATERIAL = joinpath(ROOT, "Materials", "Fe", "vasp_SOC")
const BANDS = joinpath(MATERIAL, "bands")

length(ARGS) <= 1 || error("usage: run.jl [--profile=smoke|reference]")
profile = isempty(ARGS) ? "smoke" : replace(only(ARGS), "--profile=" => "")
profile in ("smoke", "reference") || error("unsupported profile: $(profile)")
Base.pkgversion(WannierNLQG) == v"1.1.0" || error("Fe readback requires WannierNLQG 1.1.0")

sha(path) = bytes2hex(open(SHA.sha256, path))
status = JSON3.read(read(joinpath(MATERIAL, "MODEL_STATUS.json"), String))
vasp = JSON3.read(read(joinpath(BANDS, "Fe_vasp_path_receipt.json"), String))
tb = JSON3.read(read(joinpath(BANDS, "Fe_tb_path_receipt.json"), String))
status.status == "MAX_ITERATIONS" || error("Fe terminal status changed")
status.readback_status == "PASS" || error("Fe source readback receipt failed")
status.qualification == "DIAGNOSTIC_ONLY" || error("Fe qualification changed")
!Bool(status.production_eligible) || error("Fe was incorrectly marked production eligible")
sha(joinpath(MATERIAL, "Fe_tb.dat")) == status.tb_sha256 || error("Fe TB hash mismatch")
WannierNLQG.IO.read_wannier_tb_num_orbitals(joinpath(MATERIAL, "Fe_tb.dat")) == 18 ||
    error("Fe TB orbital count mismatch")

vasp_path = joinpath(BANDS, "Fe_vasp_path_absolute.dat")
tb_path = joinpath(BANDS, "Fe_tb_path_absolute.dat")
sha(vasp_path) == vasp.table_sha256 || error("Fe VASP path hash mismatch")
sha(tb_path) == tb.table_sha256 || error("Fe TB path hash mismatch")
tb.tb_sha256 == status.tb_sha256 || error("Fe path/TB identity mismatch")
tb.vasp_table_sha256 == vasp.table_sha256 || error("Fe path/VASP identity mismatch")
vasp_data = readdlm(vasp_path, comments = true)
tb_data = readdlm(tb_path, comments = true)
size(vasp_data) == (801, 65) || error("Fe VASP path shape mismatch")
size(tb_data) == (801, 19) || error("Fe TB path shape mismatch")
all(isfinite, vasp_data) && all(isfinite, tb_data) || error("nonfinite Fe path bands")
maximum(abs, vasp_data[:, 1] - tb_data[:, 1]) <= 3e-7 ||
    error("Fe VASP/TB path coordinates differ")
vasp.scf_fermi_energy_ev == tb.scf_fermi_energy_ev ||
    error("Fe path energy references differ")

println("FE_WANNIERIZATION_READBACK_OK profile=$(profile) status=$(status.status) points=801 vasp_bands=64 tb_bands=18")
