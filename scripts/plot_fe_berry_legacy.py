#!/usr/bin/env python3
"""Render total occupied Berry curvature on the Fe reference ky=0 k-slice."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def ensure_python_runtime() -> None:
    try:
        import numpy  # noqa: F401
        from PIL import Image  # noqa: F401
    except ModuleNotFoundError as error:
        raise RuntimeError("Install NumPy and Pillow in the active Python environment") from error


ensure_python_runtime()

import numpy as np
from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parent
DEFAULT_INPUT = REPOSITORY_ROOT / "examples/11_fe_oam_and_linear_response/results/reference/berry_sos_occupied_xy/Fe_bck_sum_conv.dat"
DEFAULT_TB = REPOSITORY_ROOT / "Materials/Fe/vasp_SOC/Fe_tb.dat"
DEFAULT_FIG_DIR = REPOSITORY_ROOT / "examples/11_fe_oam_and_linear_response/figures"
DEFAULT_EFERMI = 5.7156290716733436
DEFAULT_NKVEC = (200, 200, 1)
DEFAULT_KSLICE_CORNER = (0.0, 0.0, 0.0)
DEFAULT_KSLICE_B1 = (-0.5, 0.5, 0.5)
DEFAULT_KSLICE_B2 = (0.5, 0.5, -0.5)
DEFAULT_PREFACTOR = 1.0
DEFAULT_KERNEL_PREFACTOR = 1.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--tb", type=Path, default=DEFAULT_TB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_FIG_DIR)
    parser.add_argument("--efermi", type=float, default=DEFAULT_EFERMI)
    parser.add_argument("--nkvec", type=int, nargs=3, default=DEFAULT_NKVEC)
    parser.add_argument("--kslice-corner", type=float, nargs=3, default=DEFAULT_KSLICE_CORNER)
    parser.add_argument("--kslice-b1", type=float, nargs=3, default=DEFAULT_KSLICE_B1)
    parser.add_argument("--kslice-b2", type=float, nargs=3, default=DEFAULT_KSLICE_B2)
    parser.add_argument("--linthresh", type=float, default=1.0)
    parser.add_argument("--color-limit", type=float, default=None,
                        help="fixed symmetric signed-log color limit; record clipped pixels")
    parser.add_argument("--prefactor", type=float, default=DEFAULT_PREFACTOR)
    parser.add_argument("--quantity-label", type=str, default=None,
                        help="LaTex label for the colour bar; defaults to signed Omega_xy")
    parser.add_argument("--quantity-text", type=str, default=None,
                        help="Plain-text quantity name recorded in the summary")
    parser.add_argument("--negate", action="store_true", help="plot -Omega^xy instead of Omega^xy")
    parser.add_argument("--no-negate", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-fermi-contours", action="store_true")
    parser.add_argument("--no-latex", action="store_true")
    parser.add_argument("--plot-size", type=int, default=720)
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--latex-dpi", type=int, default=180)
    return parser.parse_args()


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf" if bold else "/Library/Fonts/Times New Roman.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


class LatexRenderer:
    def __init__(self, enabled: bool, dpi: int) -> None:
        self.enabled = enabled
        self.dpi = dpi
        self.latex = shutil.which("latex")
        self.dvipng = shutil.which("dvipng")
        self.cache: dict[tuple[str, int], Image.Image] = {}
        if self.enabled and (self.latex is None or self.dvipng is None):
            raise RuntimeError("LaTeX rendering requested, but latex or dvipng was not found on PATH.")

    def render(self, text: str, font_size: int) -> Image.Image | None:
        if not self.enabled:
            return None
        key = (text, font_size)
        if key in self.cache:
            return self.cache[key].copy()

        baseline_skip = int(round(font_size * 1.25))
        tex = rf"""
\documentclass{{article}}
\usepackage{{amsmath,bm}}
\pagestyle{{empty}}
\begin{{document}}
\fontsize{{{font_size}}}{{{baseline_skip}}}\selectfont
{text}
\end{{document}}
"""
        with tempfile.TemporaryDirectory(prefix="fe-ahe-latex-") as tmp:
            tmp_path = Path(tmp)
            tex_path = tmp_path / "label.tex"
            tex_path.write_text(tex, encoding="utf-8")
            subprocess.run(
                [self.latex, "-interaction=nonstopmode", tex_path.name],
                cwd=tmp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=30,
            )
            subprocess.run(
                [
                    self.dvipng,
                    "-q",
                    "-T",
                    "tight",
                    "-D",
                    str(self.dpi),
                    "-bg",
                    "Transparent",
                    "-o",
                    "label.png",
                    "label.dvi",
                ],
                cwd=tmp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=30,
            )
            image = Image.open(tmp_path / "label.png").convert("RGBA")
            self.cache[key] = image.copy()
            return image


def fallback_text(text: str) -> str:
    replacements = {
        "$": "",
        "\\Gamma": "Gamma",
        "\\Omega": "Omega",
        "\\bm": "",
        "\\textbf": "",
        "{": "",
        "}": "",
        "^": "",
        "_": "",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def paste_label(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    renderer: LatexRenderer,
    xy: tuple[float, float],
    text: str,
    font_size: int,
    anchor: str,
    fallback_font: ImageFont.ImageFont,
) -> None:
    label = renderer.render(text, font_size)
    if label is None:
        draw.text(xy, fallback_text(text), fill=(0, 0, 0), font=fallback_font, anchor=anchor if len(anchor) == 2 else None)
        return

    x, y = xy
    horizontal = anchor[0] if anchor else "l"
    vertical = anchor[1] if len(anchor) > 1 else "t"
    if horizontal == "r":
        x -= label.width
    elif horizontal == "m":
        x -= label.width / 2
    if vertical == "b":
        y -= label.height
    elif vertical == "m":
        y -= label.height / 2
    canvas.alpha_composite(label, (int(round(x)), int(round(y))))


def label_size(renderer: LatexRenderer, text: str, font_size: int, fallback_font: ImageFont.ImageFont) -> tuple[int, int]:
    label = renderer.render(text, font_size)
    if label is not None:
        return label.size
    bbox = fallback_font.getbbox(fallback_text(text))
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def parse_wannier_tb(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    lattice = np.asarray([[float(x) for x in lines[i].split()[:3]] for i in range(1, 4)], dtype=float)
    num_wann = int(lines[4].split()[0])
    nrpts = int(lines[5].split()[0])
    skip_lines = int(math.ceil(nrpts / 15.0))

    degeneracies = []
    for line in lines[6 : 6 + skip_lines]:
        degeneracies.extend(int(token) for token in line.split())
    deg = np.asarray(degeneracies[:nrpts], dtype=float)

    idx = 6 + skip_lines
    r_latt = np.zeros((nrpts, 3), dtype=float)
    hoppings = np.zeros((nrpts, num_wann, num_wann), dtype=np.complex128)
    for ir in range(nrpts):
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        r_latt[ir] = [float(x) for x in lines[idx].split()[:3]]
        idx += 1
        count = 0
        while count < num_wann * num_wann:
            fields = lines[idx].split()
            idx += 1
            if len(fields) < 4:
                continue
            m = int(fields[0]) - 1
            n = int(fields[1]) - 1
            hoppings[ir, m, n] = complex(float(fields[2]), float(fields[3]))
            count += 1
    hoppings = hoppings / deg[:, None, None]
    return lattice, r_latt, hoppings


def solve_bands_on_plane(
    r_latt: np.ndarray,
    hoppings: np.ndarray,
    n_u: int,
    n_v: int,
    corner: np.ndarray,
    b1: np.ndarray,
    b2: np.ndarray,
    chunk: int = 256,
) -> np.ndarray:
    u_vals = np.arange(n_u, dtype=float) / float(n_u)
    v_vals = np.arange(n_v, dtype=float) / float(n_v)
    uu, vv = np.meshgrid(u_vals, v_vals, indexing="ij")
    kpoints = corner[None, :] + uu.ravel()[:, None] * b1[None, :] + vv.ravel()[:, None] * b2[None, :]

    num_wann = hoppings.shape[1]
    bands = np.empty((kpoints.shape[0], num_wann), dtype=float)
    for start in range(0, kpoints.shape[0], chunk):
        stop = min(start + chunk, kpoints.shape[0])
        phase_arg = np.einsum("ka,ra->kr", kpoints[start:stop], r_latt, optimize=True)
        phases = np.exp(2j * np.pi * phase_arg)
        hams = np.einsum("kr,rij->kij", phases, hoppings, optimize=True)
        hams = 0.5 * (hams + np.conjugate(np.swapaxes(hams, 1, 2)))
        bands[start:stop] = np.linalg.eigvalsh(hams)
    return bands.reshape(n_u, n_v, num_wann)


def signed_log_exponent(values: np.ndarray, linthresh: float) -> np.ndarray:
    abs_values = np.abs(values)
    out = np.zeros_like(values, dtype=float)
    linear = abs_values <= linthresh
    out[linear] = np.sign(values[linear]) * (abs_values[linear] / linthresh)
    log_region = ~linear
    out[log_region] = np.sign(values[log_region]) * (np.log10(abs_values[log_region] / linthresh) + 1.0)
    return out


def outward_power(values: np.ndarray, positive: bool, linthresh: float) -> int:
    if positive:
        finite = values[np.isfinite(values) & (values > 0)]
    else:
        finite = -values[np.isfinite(values) & (values < 0)]
    if finite.size == 0:
        return 0
    vmax = max(float(np.nanmax(finite)), linthresh)
    return max(0, int(math.ceil(math.log10(vmax / linthresh))))


def palette(t: np.ndarray | float, zero_pos: float):
    stops = [
        (0.0, (18, 38, 170)),
        (max(0.0, zero_pos * 0.55), (0, 145, 205)),
        (zero_pos, (48, 238, 43)),
        (min(1.0, zero_pos + (1.0 - zero_pos) * 0.42), (255, 240, 55)),
        (min(1.0, zero_pos + (1.0 - zero_pos) * 0.70), (255, 135, 20)),
        (1.0, (230, 30, 10)),
    ]
    arr = np.asarray(t, dtype=float)
    out = np.zeros(arr.shape + (3,), dtype=float)
    for (x0, c0), (x1, c1) in zip(stops[:-1], stops[1:]):
        mask = (arr >= x0) & (arr <= x1)
        if x1 <= x0:
            continue
        weight = (arr[mask] - x0) / (x1 - x0)
        out[mask] = (1 - weight)[:, None] * np.asarray(c0) + weight[:, None] * np.asarray(c1)
    out[arr < 0] = stops[0][1]
    out[arr > 1] = stops[-1][1]
    if np.isscalar(t):
        return tuple(int(x) for x in out.reshape(3))
    return np.clip(out, 0, 255).astype(np.uint8)


def render_heatmap(values: np.ndarray, plot_size: int, linthresh: float, color_limit: float | None):
    if color_limit is None:
        pos_power = outward_power(values, True, linthresh)
        neg_power = outward_power(values, False, linthresh)
    else:
        if color_limit < linthresh or not math.isclose(math.log10(color_limit / linthresh) % 1, 0.0, abs_tol=1e-10):
            raise ValueError("--color-limit must be a power of ten times linthresh")
        pos_power = neg_power = int(round(math.log10(color_limit / linthresh)))
    tmin = -(neg_power + 1.0)
    tmax = pos_power + 1.0
    zero_pos = (0.0 - tmin) / (tmax - tmin)
    transformed = signed_log_exponent(values, linthresh)
    norm = np.clip((transformed - tmin) / (tmax - tmin), 0.0, 1.0)
    rgb = palette(norm, zero_pos)
    resampling = getattr(Image, "Resampling", Image).BILINEAR
    image = Image.fromarray(np.flipud(rgb), "RGB").resize((plot_size, plot_size), resampling)
    neg_limit = linthresh * (10.0 ** neg_power)
    pos_limit = linthresh * (10.0 ** pos_power)
    return image, tmin, tmax, zero_pos, neg_limit, pos_limit, neg_power, pos_power


def draw_fermi_contours(draw: ImageDraw.ImageDraw, bands: np.ndarray, efermi: float, box, colors):
    left, top, size = box
    n_u, n_v, num_wann = bands.shape
    sx = size / max(n_u - 1, 1)
    sy = size / max(n_v - 1, 1)

    def point_to_xy(p):
        u, v = p
        return (left + u * sx, top + (n_v - 1 - v) * sy)

    def crossing(p1, z1, p2, z2):
        if z1 == z2:
            return None
        t = z1 / (z1 - z2)
        if t < 0.0 or t > 1.0:
            return None
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))

    for band in range(num_wann):
        z = bands[:, :, band] - efermi
        color = colors[band % len(colors)]
        for i in range(n_u - 1):
            for j in range(n_v - 1):
                corners = [
                    ((i, j), z[i, j], (i + 1, j), z[i + 1, j]),
                    ((i + 1, j), z[i + 1, j], (i + 1, j + 1), z[i + 1, j + 1]),
                    ((i + 1, j + 1), z[i + 1, j + 1], (i, j + 1), z[i, j + 1]),
                    ((i, j + 1), z[i, j + 1], (i, j), z[i, j]),
                ]
                pts = []
                for p1, z1, p2, z2 in corners:
                    if (z1 <= 0.0 <= z2) or (z2 <= 0.0 <= z1):
                        p = crossing(p1, z1, p2, z2)
                        if p is not None:
                            pts.append(p)
                if len(pts) == 2:
                    draw.line([point_to_xy(pts[0]), point_to_xy(pts[1])], fill=color, width=2)
                elif len(pts) == 4:
                    draw.line([point_to_xy(pts[0]), point_to_xy(pts[1])], fill=color, width=2)
                    draw.line([point_to_xy(pts[2]), point_to_xy(pts[3])], fill=color, width=2)


def tick_label(tick: float, linthresh: float) -> str:
    if tick == 0:
        return r"$0$"
    sign = "-" if tick < 0 else ""
    power = int(round(math.log10(abs(tick) / linthresh)))
    if abs(linthresh - 1.0) < 1.0e-12:
        return rf"${sign}10^{{{power}}}$"
    return rf"${sign}{linthresh:g}\times 10^{{{power}}}$"


def draw_colorbar(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    renderer: LatexRenderer,
    x: int,
    y: int,
    width: int,
    height: int,
    tmin: float,
    tmax: float,
    zero_pos: float,
    neg_power: int,
    pos_power: int,
    linthresh: float,
    quantity_label: str,
    font: ImageFont.ImageFont,
) -> None:
    for row in range(height):
        norm = 1.0 - row / max(height - 1, 1)
        color = palette(norm, zero_pos)
        draw.line([(x, y + row), (x + width, y + row)], fill=color)
    draw.rectangle([x, y, x + width, y + height], outline=(0, 0, 0), width=1)

    ticks = [-(linthresh * 10.0**p) for p in range(neg_power, -1, -1)]
    ticks += [0.0]
    ticks += [linthresh * 10.0**p for p in range(0, pos_power + 1)]
    for tick in ticks:
        transformed = signed_log_exponent(np.asarray([tick], dtype=float), linthresh)[0]
        pos = (transformed - tmin) / (tmax - tmin)
        if pos < -0.02 or pos > 1.02:
            continue
        yy = int(round(y + (1.0 - pos) * height))
        draw.line([(x + width, yy), (x + width + 7, yy)], fill=(0, 0, 0), width=1)
        paste_label(canvas, draw, renderer, (x + width + 13, yy), tick_label(tick, linthresh), 12, "lm", font)

    paste_label(canvas, draw, renderer, (x + width / 2, y - 28), quantity_label, 14, "mm", font)


def main() -> None:
    args = parse_args()
    if args.linthresh <= 0:
        raise ValueError("--linthresh must be positive")
    data = np.loadtxt(args.input, comments="#")
    if data.ndim != 2:
        raise ValueError(f"Expected a 2D matrix in {args.input}, got shape={data.shape}")
    if not np.all(np.isfinite(data)):
        raise ValueError(f"{args.input} contains NaN or Inf values")

    corner = np.asarray(args.kslice_corner, dtype=float)
    b1 = np.asarray(args.kslice_b1, dtype=float)
    b2 = np.asarray(args.kslice_b2, dtype=float)
    negate = args.negate and not args.no_negate
    quantity_label = args.quantity_label or (r"$-\Omega^{xy}$" if negate else r"$\Omega^{xy}$")
    quantity_text = args.quantity_text or ("-Omega_xy" if negate else "Omega_xy")
    values = args.prefactor * data
    values = -values if negate else values
    n_u, n_v = values.shape
    heatmap_values = values.T

    fallback_label_font = load_font(24, bold=True)
    fallback_small_font = load_font(18)
    renderer = LatexRenderer(enabled=not args.no_latex, dpi=args.latex_dpi)

    plot_size = args.plot_size
    label_gap = 16
    corner_font_size = 16
    top_labels = [r"$\mathrm{H}(001)$", r"$\Gamma(101)$"]
    bottom_labels = [r"$\Gamma(000)$", r"$\mathrm{H}(100)$"]
    top_label_h = max(label_size(renderer, text, corner_font_size, fallback_label_font)[1] for text in top_labels)
    bottom_label_h = max(label_size(renderer, text, corner_font_size, fallback_label_font)[1] for text in bottom_labels)

    left = 76
    top = max(76, top_label_h + label_gap + 18)
    cbar_x = left + plot_size + 58
    cbar_y = top + 170
    cbar_w = 30
    cbar_h = 430
    width = cbar_x + 178
    bottom_margin = label_gap + bottom_label_h + 34
    height = top + plot_size + bottom_margin

    canvas = Image.new("RGBA", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    heatmap, tmin, tmax, zero_pos, neg_limit, pos_limit, neg_power, pos_power = render_heatmap(
        heatmap_values,
        plot_size,
        args.linthresh,
        args.color_limit,
    )
    canvas.paste(heatmap.convert("RGBA"), (left, top))
    draw.rectangle([left, top, left + plot_size, top + plot_size], outline=(0, 0, 0), width=1)

    if not args.no_fermi_contours:
        _, r_latt, hoppings = parse_wannier_tb(args.tb)
        bands = solve_bands_on_plane(r_latt, hoppings, n_u, n_v, corner, b1, b2)
        draw_fermi_contours(draw, bands, args.efermi, (left, top, plot_size), [(230, 20, 20), (30, 60, 230)])

    box_right = left + plot_size
    box_bottom = top + plot_size
    paste_label(canvas, draw, renderer, (left, top - label_gap), r"$\mathrm{H}(001)$", corner_font_size, "lb", fallback_label_font)
    paste_label(canvas, draw, renderer, (box_right, top - label_gap), r"$\Gamma(101)$", corner_font_size, "rb", fallback_label_font)
    paste_label(canvas, draw, renderer, (left, box_bottom + label_gap), r"$\Gamma(000)$", corner_font_size, "lt", fallback_label_font)
    paste_label(canvas, draw, renderer, (box_right, box_bottom + label_gap), r"$\mathrm{H}(100)$", corner_font_size, "rt", fallback_label_font)

    draw_colorbar(
        canvas,
        draw,
        renderer,
        cbar_x,
        cbar_y,
        cbar_w,
        cbar_h,
        tmin,
        tmax,
        zero_pos,
        neg_power,
        pos_power,
        args.linthresh,
        quantity_label,
        fallback_small_font,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "Fe_total_berry_curvature_ky0_log"
    png_path = args.output_dir / f"{stem}.png"
    pdf_path = args.output_dir / f"{stem}.pdf"
    summary_path = args.output_dir / f"{stem}_summary.txt"
    canvas.convert("RGB").save(png_path, dpi=(args.dpi, args.dpi))
    canvas.convert("RGB").save(pdf_path, resolution=float(args.dpi))

    with summary_path.open("w", encoding="utf-8") as fh:
        fh.write(f"input={args.input.resolve()}\n")
        fh.write(f"tb={args.tb.resolve()}\n")
        fh.write(f"python={sys.executable}\n")
        fh.write(f"latex_enabled={renderer.enabled}\n")
        fh.write(f"shape={data.shape}\n")
        fh.write(f"nkvec={tuple(args.nkvec)}\n")
        fh.write(f"Efermi={args.efermi:.16e}\n")
        fh.write(f"kslice_corner={tuple(float(x) for x in corner)}\n")
        fh.write(f"kslice_b1={tuple(float(x) for x in b1)}\n")
        fh.write(f"kslice_b2={tuple(float(x) for x in b2)}\n")
        fh.write(f"kernel_prefactor={DEFAULT_KERNEL_PREFACTOR:.16e}\n")
        fh.write(f"prefactor={args.prefactor:.16e}\n")
        fh.write(f"plot_quantity={quantity_text}\n")
        fh.write("log_mapping=signed-log-exponent with linear core; powers of ten are uniformly spaced on the colorbar\n")
        fh.write(f"raw_min={float(np.min(data)):.16e}\n")
        fh.write(f"raw_max={float(np.max(data)):.16e}\n")
        fh.write(f"plot_min={float(np.min(values)):.16e}\n")
        fh.write(f"plot_max={float(np.max(values)):.16e}\n")
        fh.write(f"finite_count={int(np.isfinite(data).sum())}\n")
        fh.write(f"negative_limit={neg_limit:.16e}\n")
        fh.write(f"positive_limit={pos_limit:.16e}\n")
        fh.write(f"negative_power={neg_power}\n")
        fh.write(f"positive_power={pos_power}\n")
        fh.write(f"fixed_color_limit={args.color_limit}\n")
        fh.write(f"clipped_negative_count={int(np.count_nonzero(values < -neg_limit))}\n")
        fh.write(f"clipped_positive_count={int(np.count_nonzero(values > pos_limit))}\n")
        fh.write(f"linthresh={args.linthresh:.16e}\n")
        fh.write(f"image_size={canvas.width}x{canvas.height}\n")

    print(f"wrote {png_path}")
    print(f"wrote {pdf_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
