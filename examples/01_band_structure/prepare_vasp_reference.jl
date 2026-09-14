#!/usr/bin/env julia
using JSON3
using SHA

const CHAPTER = @__DIR__
const ROOT = normpath(joinpath(CHAPTER, "..", ".."))
const INPUT = joinpath(ROOT, "Materials", "GeS", "vasp_SOC", "EIGENVAL")
const TB_BANDS = joinpath(CHAPTER, "results", "reference", "band_structure", "GeS_bands.dat")
const OUTPUT_DIR = joinpath(CHAPTER, "derived")

function sha256(path)
    return bytes2hex(open(SHA.sha256, path))
end

function parse_eigenval(path)
    lines = readlines(path)
    counts = split(strip(lines[6]))
    length(counts) == 3 || error("invalid EIGENVAL counts line")
    nk = parse(Int, counts[2])
    nb = parse(Int, counts[3])
    kpoints = Vector{Vector{Float64}}()
    energies = Vector{Vector{Float64}}()
    source_lines = Int[]
    cursor = 7
    while length(kpoints) < nk
        while cursor <= length(lines) && isempty(strip(lines[cursor]))
            cursor += 1
        end
        cursor <= length(lines) || error("truncated EIGENVAL k-point block")
        values = parse.(Float64, split(strip(lines[cursor])))
        length(values) >= 4 || error("invalid EIGENVAL k-point line $(cursor)")
        push!(kpoints, values[1:3])
        push!(source_lines, cursor)
        cursor += 1
        band_values = Float64[]
        for band in 1:nb
            fields = split(strip(lines[cursor]))
            parse(Int, fields[1]) == band || error("nonconsecutive band index")
            push!(band_values, parse(Float64, fields[2]))
            cursor += 1
        end
        push!(energies, band_values)
    end
    return kpoints, energies, source_lines, nb
end

function parse_tb_grid(path)
    rows = [parse.(Float64, split(strip(line))) for line in eachline(path) if !startswith(strip(line), "#") && !isempty(strip(line))]
    isempty(rows) && error("empty TB band table")
    distances = [row[1] for row in rows]
    kpoints = [row[2:4] for row in rows]
    return distances, kpoints
end

isfile(TB_BANDS) || error("run the reference band case before preparing the comparison")
distances, tb_kpoints = parse_tb_grid(TB_BANDS)
nk_target = length(distances)
kpoints, energies, source_lines, nb = parse_eigenval(INPUT)
length(kpoints) == 204 || error("expected 204 native VASP path points")
kept = [index for index in eachindex(kpoints) if index ∉ (52, 103, 154)]
length(kept) == nk_target || error("deduplicated VASP path does not match TB path length")
for (target_index, source_index) in enumerate(kept)
    maximum(abs.(kpoints[source_index] .- tb_kpoints[target_index])) <= 1.0e-10 ||
        error("k-point mismatch after endpoint deduplication at target $(target_index)")
end
mkpath(OUTPUT_DIR)
data_path = joinpath(OUTPUT_DIR, "GeS_vasp_band_path.dat")
open(data_path, "w") do io
    for (target_index, source_index) in enumerate(kept)
        println(io, join(vcat(distances[target_index], energies[source_index]), ' '))
    end
end
path_path = joinpath(OUTPUT_DIR, "GeS_vasp_band_path.json")
open(path_path, "w") do io
    JSON3.pretty(io, Dict(
        "schema" => "wanniernlqg.visualization-band-path",
        "schema_version" => "1.0",
        "distance_unit" => "A^-1",
        "energy_unit" => "eV",
        "kpoint_coordinate_convention" => "fractional_crystal",
        "energy_reference_ev" => -2.5,
        "fractional_kpoints" => [kpoints[index] for index in kept],
        "distances_A_inverse" => distances,
        "nodes" => [
            Dict("index_zero_based" => 0, "label" => "Γ"),
            Dict("index_zero_based" => 50, "label" => "X"),
            Dict("index_zero_based" => 100, "label" => "S"),
            Dict("index_zero_based" => 150, "label" => "Y"),
            Dict("index_zero_based" => 200, "label" => "Γ"),
        ],
    ))
    write(io, '\n')
end
manifest_path = joinpath(OUTPUT_DIR, "derivation_manifest.json")
open(manifest_path, "w") do io
    JSON3.pretty(io, Dict(
        "schema" => "wanniernlqg-tutorials.vasp-band-derivation",
        "schema_version" => "1.0",
        "source" => "Materials/GeS/vasp_SOC/EIGENVAL",
        "source_sha256" => sha256(INPUT),
        "operation" => "drop repeated segment-start endpoints only",
        "dropped_one_based_kpoint_indices" => [52, 103, 154],
        "kept_source_kpoint_indices_one_based" => kept,
        "kept_source_header_lines_one_based" => source_lines[kept],
        "energy_columns" => nb,
        "output_sha256" => sha256(data_path),
        "path_sha256" => sha256(path_path),
        "qualification" => "DIAGNOSTIC_DISPLAY_PREPARATION",
    ))
    write(io, '\n')
end
println("VASP_REFERENCE_OK points=$(length(kept)) bands=$(nb)")
