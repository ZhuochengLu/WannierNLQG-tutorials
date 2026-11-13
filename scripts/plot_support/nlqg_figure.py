#!/usr/bin/env python3
"""Render and validate NLQG-style Matplotlib figures from JSON manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import matplotlib as mpl
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LogNorm, Normalize, SymLogNorm, TwoSlopeNorm
from matplotlib.ticker import FuncFormatter


PROFILE = {
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 14,
    "axes.linewidth": 1.1,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 1.0,
    "ytick.major.width": 1.0,
    "xtick.minor.width": 0.8,
    "ytick.minor.width": 0.8,
    "legend.fontsize": 11,
    "legend.frameon": False,
    "savefig.dpi": 600,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.unicode_minus": False,
    "text.usetex": True,
    "text.latex.preamble": r"\usepackage{newtxtext,newtxmath}\usepackage{bm}\usepackage{textgreek}",
}
DEFAULT_COLORS = ("#104E8B", "#FF7F24", "#3CB371", "#C71585")


def fail(message: str) -> None:
    raise ValueError(message)


def environment_report() -> dict[str, Any]:
    report: dict[str, Any] = {
        "matplotlib": mpl.__version__,
        "times_new_roman": False,
        "pdflatex": shutil.which("pdflatex"),
        "pdftoppm": shutil.which("pdftoppm"),
        "ghostscript": shutil.which("gs"),
        "latex_packages": {},
    }
    try:
        font_manager.findfont("Times New Roman", fallback_to_default=False)
        report["times_new_roman"] = True
    except ValueError:
        pass
    for package in ("newtxtext.sty", "newtxmath.sty", "bm.sty", "textgreek.sty"):
        completed = subprocess.run(
            ["kpsewhich", package], capture_output=True, text=True, check=False
        )
        report["latex_packages"][package] = completed.stdout.strip() or None
    report["ready"] = bool(
        report["times_new_roman"]
        and report["pdflatex"]
        and report["pdftoppm"]
        and all(report["latex_packages"].values())
    )
    return report


def require_environment() -> None:
    report = environment_report()
    if not report["ready"]:
        fail("NLQG Times/LaTeX profile is unavailable: " + json.dumps(report, ensure_ascii=False))


def configure_profile() -> None:
    require_environment()
    mpl.rcParams.update(PROFILE)


def resolve(base: Path, raw: str) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def load_numeric(base: Path, raw_path: str) -> np.ndarray:
    path = resolve(base, raw_path)
    if not path.is_file():
        fail(f"data file does not exist: {path}")
    if path.suffix.lower() == ".npy":
        data = np.load(path)
    else:
        delimiter = "," if path.suffix.lower() == ".csv" else None
        data = np.genfromtxt(path, delimiter=delimiter, comments="#", ndmin=2)
    array = np.asarray(data, dtype=float)
    if not array.size or not np.isfinite(array).all():
        fail(f"data are empty or contain NaN/Inf: {path}")
    return array


def series_xy(base: Path, spec: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    data = load_numeric(base, spec["data"])
    if data.ndim != 2:
        fail(f"line data must be a 2D table: {spec['data']}")
    x_column = int(spec.get("x_column", 0))
    y_column = int(spec.get("y_column", 1))
    if max(x_column, y_column) >= data.shape[1]:
        fail(f"line-column index is outside table shape {data.shape}: {spec['data']}")
    x, y = data[:, x_column], data[:, y_column]
    if "subtract" in spec:
        reference = spec["subtract"]
        ref_data = load_numeric(base, reference["data"])
        rx = ref_data[:, int(reference.get("x_column", x_column))]
        ry = ref_data[:, int(reference.get("y_column", y_column))]
        if x.shape != rx.shape or not np.allclose(x, rx, rtol=1.0e-10, atol=1.0e-12):
            fail("subtracted series must share the same x grid")
        y = y - ry
    y = y * float(spec.get("scale", 1.0))
    return x, y, {"source": str(resolve(base, spec["data"])), "min": float(y.min()), "max": float(y.max())}


def style_axis(ax: Any, spec: dict[str, Any]) -> None:
    ax.tick_params(which="both", direction="in", top=True, right=True)
    if spec.get("title"):
        ax.set_title(spec["title"], pad=7)
    if spec.get("xlabel"):
        ax.set_xlabel(spec["xlabel"])
    if spec.get("ylabel"):
        ax.set_ylabel(spec["ylabel"])
    for axis_name in ("x", "y"):
        scale = spec.get(f"{axis_name}scale", "linear")
        if scale not in ("linear", "log"):
            fail("line axis scale must be linear or log")
        getattr(ax, f"set_{axis_name}scale")(scale)
    for name in ("xlim", "ylim"):
        if name in spec:
            getattr(ax, f"set_{name}")(*spec[name])
    for name in ("xticks", "yticks"):
        if name in spec:
            getattr(ax, f"set_{name}")(spec[name])
    for axis_name in ("x", "y"):
        ticks_name = f"{axis_name}ticks"
        labels_name = f"{axis_name}ticklabels"
        if labels_name in spec:
            if ticks_name not in spec:
                fail(f"{labels_name} requires {ticks_name}")
            if len(spec[labels_name]) != len(spec[ticks_name]):
                fail(f"{labels_name} and {ticks_name} must have the same length")
            getattr(ax, f"set_{axis_name}ticklabels")(spec[labels_name])
    guide_style = {
        "zorder": 0,
        "color": "0.82",
        "linestyle": "-",
        "linewidth": 0.8,
        **dict(spec.get("guide_style", {})),
    }
    for position in spec.get("guide_x", []):
        ax.axvline(float(position), **guide_style)
    for position in spec.get("guide_y", []):
        ax.axhline(float(position), **guide_style)
    if "y_scale_power" in spec:
        power = int(spec["y_scale_power"])
        scale = 10.0**power
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value / scale:g}"))
        ax.yaxis.get_offset_text().set_visible(False)
        ax.text(0.0, 1.0, rf"$\times 10^{{{power}}}$", transform=ax.transAxes, ha="left", va="bottom", clip_on=False)


def panel_label(ax: Any, spec: dict[str, Any]) -> None:
    if spec.get("label"):
        ax.text(0.02, 0.98, spec["label"], transform=ax.transAxes, ha="left", va="top", fontsize=14, fontweight="bold")


def legend_kwargs(spec: dict[str, Any], framed: bool) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "loc": spec.get("legend_loc", "best"),
        "frameon": framed,
        "fancybox": bool(spec.get("legend_fancybox", True)),
        "fontsize": float(spec.get("legend_fontsize", PROFILE["legend.fontsize"])),
        "borderpad": float(spec.get("legend_borderpad", 0.4)),
        "handlelength": float(spec.get("legend_handlelength", 2.0)),
        "handletextpad": float(spec.get("legend_handletextpad", 0.8)),
        "labelspacing": float(spec.get("legend_labelspacing", 0.5)),
        "borderaxespad": float(spec.get("legend_borderaxespad", 0.5)),
        "columnspacing": float(spec.get("legend_columnspacing", 2.0)),
        "alignment": spec.get("legend_alignment", "center"),
        "ncol": int(spec.get("legend_ncol", 1)),
        "markerfirst": bool(spec.get("legend_markerfirst", True)),
    }
    if kwargs["ncol"] < 1:
        fail("legend_ncol must be at least one")
    if kwargs["alignment"] not in {"left", "center", "right"}:
        fail("legend_alignment must be left, center, or right")
    if kwargs["fontsize"] <= 0:
        fail("legend_fontsize must be positive")
    for name in (
        "borderpad",
        "handlelength",
        "handletextpad",
        "labelspacing",
        "borderaxespad",
        "columnspacing",
    ):
        if kwargs[name] < 0:
            fail(f"legend_{name} must be nonnegative")
    if "legend_bbox_to_anchor" in spec:
        anchor = spec["legend_bbox_to_anchor"]
        if not isinstance(anchor, list) or len(anchor) not in {2, 4}:
            fail("legend_bbox_to_anchor must be a list of two or four numbers")
        values = tuple(float(value) for value in anchor)
        if not all(math.isfinite(value) for value in values):
            fail("legend_bbox_to_anchor values must be finite")
        kwargs["bbox_to_anchor"] = values
    return kwargs


def draw_line(
    ax: Any,
    spec: dict[str, Any],
    base: Path,
    summary: list[dict[str, Any]],
    legends: list[dict[str, Any]],
) -> None:
    series = spec.get("series", [])
    if not series:
        fail("line figure requires a nonempty series list")
    labeled = False
    for index, item in enumerate(series):
        x, y, stats = series_xy(base, item)
        label = item.get("label")
        labeled = labeled or bool(label)
        ax.plot(
            x,
            y,
            color=item.get("color", DEFAULT_COLORS[index % len(DEFAULT_COLORS)]),
            linestyle=item.get("linestyle", "-"),
            linewidth=float(item.get("linewidth", 1.6)),
            marker=item.get("marker", None),
            markersize=float(item.get("markersize", 4.0)),
            label=label,
        )
        summary.append({"kind": "line", **stats})
    style_axis(ax, spec)
    if spec.get("legend", labeled):
        framed = bool(spec.get("legend_frame", False))
        legend = ax.legend(**legend_kwargs(spec, framed))
        if framed:
            frame = legend.get_frame()
            frame.set_facecolor(spec.get("legend_facecolor", "white"))
            frame.set_edgecolor(spec.get("legend_edgecolor", "0.25"))
            frame.set_alpha(float(spec.get("legend_framealpha", 0.9)))
            frame.set_linewidth(float(spec.get("legend_linewidth", 0.8)))
            if "legend_rounding_size" in spec:
                if not bool(spec.get("legend_fancybox", True)):
                    fail("legend_rounding_size requires legend_fancybox: true")
                if float(spec["legend_rounding_size"]) < 0:
                    fail("legend_rounding_size must be nonnegative")
                frame.set_boxstyle(
                    "round",
                    pad=0.0,
                    rounding_size=float(spec["legend_rounding_size"]),
                )
        legends.append({"artist": legend, "spec": spec})
    panel_label(ax, spec)


def summarize_legends(
    fig: Any,
    legends: list[dict[str, Any]],
    summary: list[dict[str, Any]],
) -> None:
    if not legends:
        return
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figure_bbox = fig.bbox
    figure_dpi = float(fig.dpi)
    for index, record in enumerate(legends):
        legend = record["artist"]
        spec = record["spec"]
        bbox = legend.get_window_extent(renderer=renderer)
        frame = legend.get_frame()
        boxstyle = frame.get_boxstyle()
        bbox_pixels = [float(bbox.x0), float(bbox.y0), float(bbox.x1), float(bbox.y1)]
        bbox_points = [value * 72.0 / figure_dpi for value in bbox_pixels]
        bbox_fraction = [
            float((bbox.x0 - figure_bbox.x0) / figure_bbox.width),
            float((bbox.y0 - figure_bbox.y0) / figure_bbox.height),
            float((bbox.x1 - figure_bbox.x0) / figure_bbox.width),
            float((bbox.y1 - figure_bbox.y0) / figure_bbox.height),
        ]
        summary.append(
            {
                "kind": "legend",
                "index": index,
                "labels": [text.get_text() for text in legend.get_texts()],
                "figure_dpi": figure_dpi,
                "bbox_canvas_pixels": bbox_pixels,
                "bbox_size_canvas_pixels": [float(bbox.width), float(bbox.height)],
                "bbox_points": bbox_points,
                "bbox_size_points": [
                    float(bbox.width * 72.0 / figure_dpi),
                    float(bbox.height * 72.0 / figure_dpi),
                ],
                "bbox_figure_fraction": bbox_fraction,
                "frame": {
                    "visible": bool(frame.get_visible()),
                    "face_rgba": [float(value) for value in frame.get_facecolor()],
                    "edge_rgba": [float(value) for value in frame.get_edgecolor()],
                    "alpha": frame.get_alpha(),
                    "linewidth_points": float(frame.get_linewidth()),
                    "boxstyle": type(boxstyle).__name__,
                    "rounding_size": (
                        None
                        if getattr(boxstyle, "rounding_size", None) is None
                        else float(boxstyle.rounding_size)
                    ),
                },
                "content": {
                    "fontsize_points": float(
                        spec.get("legend_fontsize", PROFILE["legend.fontsize"])
                    ),
                    "borderpad": float(spec.get("legend_borderpad", 0.4)),
                    "handlelength": float(spec.get("legend_handlelength", 2.0)),
                    "handletextpad": float(spec.get("legend_handletextpad", 0.8)),
                    "labelspacing": float(spec.get("legend_labelspacing", 0.5)),
                    "borderaxespad": float(spec.get("legend_borderaxespad", 0.5)),
                    "columnspacing": float(spec.get("legend_columnspacing", 2.0)),
                    "alignment": spec.get("legend_alignment", "center"),
                    "ncol": int(spec.get("legend_ncol", 1)),
                    "bbox_to_anchor": spec.get("legend_bbox_to_anchor"),
                },
            }
        )


def apply_transform(data: np.ndarray, transforms: list[str]) -> np.ndarray:
    result = data
    for transform in transforms:
        if transform == "transpose":
            result = result.T
        elif transform == "fftshift":
            result = np.fft.fftshift(result)
        elif transform == "flipud":
            result = np.flipud(result)
        elif transform == "fliplr":
            result = np.fliplr(result)
        else:
            fail(f"unsupported map transform: {transform}")
    return result


def map_norm(data: np.ndarray, color: dict[str, Any]) -> tuple[Any, str]:
    kind = color.get("kind", "diverging")
    maximum = float(np.max(np.abs(data)))
    limit = float(color.get("limit", maximum if maximum else 1.0))
    if kind == "linear":
        return Normalize(vmin=color.get("vmin"), vmax=color.get("vmax")), color.get("cmap", "viridis")
    if kind == "diverging":
        return TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit), color.get("cmap", "RdBu_r")
    if kind == "positive_log":
        positive = data[data > 0]
        if not positive.size:
            fail("positive_log requires at least one positive datum")
        return LogNorm(vmin=float(color.get("vmin", positive.min())), vmax=float(color.get("vmax", positive.max()))), color.get("cmap", "Reds")
    if kind == "signed_log":
        linthresh = float(color.get("linthresh", max(limit * 1.0e-3, 1.0e-12)))
        return SymLogNorm(linthresh=linthresh, vmin=-limit, vmax=limit), color.get("cmap", "RdBu_r")
    if kind == "phase":
        return Normalize(vmin=-math.pi, vmax=math.pi), color.get("cmap", "twilight")
    fail(f"unsupported color kind: {kind}")


def draw_map(fig: Any, ax: Any, spec: dict[str, Any], base: Path, summary: list[dict[str, Any]]) -> None:
    data = load_numeric(base, spec["data"])
    if data.ndim != 2:
        fail(f"map data must be 2D: {spec['data']}")
    data = apply_transform(data, list(spec.get("transform", [])))
    color = dict(spec.get("color", {}))
    norm, cmap = map_norm(data, color)
    image = ax.imshow(
        data,
        origin="lower",
        extent=spec.get("extent"),
        aspect=spec.get("aspect", "equal"),
        interpolation=spec.get("interpolation", "nearest"),
        cmap=cmap,
        norm=norm,
    )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    # Explicit display ticks leave the data, normalization and color limits unchanged.
    if "colorbar_ticks" in spec:
        ticks = np.asarray(spec["colorbar_ticks"], dtype=float)
        if (ticks.ndim != 1 or len(ticks) < 2 or not np.all(np.isfinite(ticks))
                or not np.all(np.diff(ticks) > 0)
                or ticks[0] < norm.vmin or ticks[-1] > norm.vmax):
            fail("colorbar_ticks must be finite, increasing and within the color range")
        colorbar.set_ticks(ticks)
    colorbar.ax.tick_params(which="both", direction="in", labelsize=11)
    colorbar.set_label(spec.get("colorbar_label", ""), fontsize=11)
    style_axis(ax, spec)
    panel_label(ax, spec)
    summary.append({"kind": "map", "source": str(resolve(base, spec["data"])), "shape": list(data.shape), "min": float(data.min()), "max": float(data.max()), "color_kind": color.get("kind", "diverging")})


def create_outlined_pdf(source: Path, destination: Path) -> None:
    ghostscript = shutil.which("gs")
    if not ghostscript:
        fail("outlined_pdf requires Ghostscript (gs)")
    if not source.is_file():
        fail(f"source PDF does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.", suffix=".pdf", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        completed = subprocess.run(
            [
                ghostscript,
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-dCompatibilityLevel=1.4",
                "-dNoOutputFonts",
                "-sDEVICE=pdfwrite",
                f"-sOutputFile={temporary}",
                str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0 or not temporary.is_file():
            fail(
                "Ghostscript failed to create outlined PDF: "
                + (completed.stderr.strip() or completed.stdout.strip())
            )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def render_figure(manifest_path: Path) -> dict[str, Any]:
    configure_profile()
    import matplotlib.pyplot as plt

    manifest = json.loads(manifest_path.read_text())
    if "figure" not in manifest or "output" not in manifest:
        fail("manifest requires figure and output objects")
    base = manifest_path.parent
    figure_spec = dict(manifest["figure"])
    output_spec = dict(manifest["output"])
    kind = figure_spec.get("kind")
    figsize = figure_spec.get("figsize", [6.0, 4.0])
    summary: list[dict[str, Any]] = []
    legends: list[dict[str, Any]] = []
    if kind == "grid":
        rows, cols = int(figure_spec["rows"]), int(figure_spec["cols"])
        panels = figure_spec.get("panels", [])
        if len(panels) > rows * cols:
            fail("grid has more panels than cells")
        fig, axes = plt.subplots(rows, cols, figsize=figsize, squeeze=False, layout="constrained")
        for index, panel in enumerate(panels):
            ax = axes.flat[index]
            if panel.get("kind") == "line":
                draw_line(ax, panel, base, summary, legends)
            elif panel.get("kind") == "map":
                draw_map(fig, ax, panel, base, summary)
            else:
                fail("grid panels must have kind line or map")
        for index in range(len(panels), rows * cols):
            axes.flat[index].set_visible(False)
    elif kind == "line":
        fig, ax = plt.subplots(figsize=figsize, layout="constrained")
        draw_line(ax, figure_spec, base, summary, legends)
    elif kind == "map":
        fig, ax = plt.subplots(figsize=figsize, layout="constrained")
        draw_map(fig, ax, figure_spec, base, summary)
    else:
        fail("figure.kind must be line, map, or grid")
    if figure_spec.get("suptitle"):
        fig.suptitle(figure_spec["suptitle"], fontsize=14)
    summarize_legends(fig, legends, summary)
    stem = resolve(base, output_spec["stem"])
    stem.parent.mkdir(parents=True, exist_ok=True)
    formats = output_spec.get("formats", ["png", "pdf"])
    dpi = int(output_spec.get("dpi", 600))
    files = []
    for extension in formats:
        if extension not in {"png", "pdf"}:
            fail(f"unsupported output format: {extension}")
        path = stem.with_suffix(f".{extension}")
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
        files.append(str(path))
    plt.close(fig)
    if output_spec.get("outlined_pdf", False):
        if "pdf" not in formats:
            fail("outlined_pdf requires pdf in output.formats")
        outlined = stem.with_name(f"{stem.name}_outlined").with_suffix(".pdf")
        create_outlined_pdf(stem.with_suffix(".pdf"), outlined)
        files.append(str(outlined))
    report = {
        "manifest": str(manifest_path),
        "profile": "Times New Roman + LaTeX/newtx/textgreek",
        "outputs": files,
        "data": summary,
    }
    report_path = stem.with_suffix(".summary.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    report["summary"] = str(report_path)
    return report


def inspect_png(path: Path) -> dict[str, Any]:
    from matplotlib import image as mpimg

    if not path.is_file():
        fail(f"PNG does not exist: {path}")
    data = np.asarray(mpimg.imread(path))
    rgb = data[..., :3] if data.ndim == 3 else data
    nonwhite = int(np.count_nonzero(np.any(rgb < 0.985, axis=-1))) if rgb.ndim == 3 else int(np.count_nonzero(rgb < 0.985))
    report = {"file": str(path), "bytes": path.stat().st_size, "shape": list(data.shape), "nonwhite_pixels": nonwhite, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if report["bytes"] == 0 or report["nonwhite_pixels"] == 0:
        fail("PNG is empty or contains no visible figure content")
    return report


def inspect_pdf(path: Path, preview: Path | None = None, dpi: int = 180) -> dict[str, Any]:
    if not path.is_file():
        fail(f"PDF does not exist: {path}")
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        fail("PDF inspection requires Poppler (pdftoppm)")
    preview = preview or path.with_name(f"{path.stem}.preview.png")
    preview.parent.mkdir(parents=True, exist_ok=True)
    prefix = preview.with_suffix("")
    completed = subprocess.run(
        [
            pdftoppm,
            "-png",
            "-r",
            str(int(dpi)),
            "-singlefile",
            str(path),
            str(prefix),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    generated = Path(f"{prefix}.png")
    if completed.returncode != 0 or not generated.is_file():
        fail(
            "pdftoppm failed to render PDF preview: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    if generated != preview:
        os.replace(generated, preview)
    return {
        "file": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "preview": inspect_png(preview),
    }


GLYPH_TEXT_FIELDS = {
    "title",
    "suptitle",
    "xlabel",
    "ylabel",
    "xticklabels",
    "yticklabels",
    "label",
    "colorbar_label",
}
BASELINE_GLYPH_LABELS = [
    r"\textnormal{A}",
    r"\textGamma",
    r"\textnormal{-1}",
]


def labels_from_manifest(manifest_path: Path) -> list[str]:
    if not manifest_path.is_file():
        fail(f"manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    labels: list[str] = []

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in GLYPH_TEXT_FIELDS:
                    if isinstance(value, str):
                        labels.append(value)
                    elif isinstance(value, list):
                        labels.extend(item for item in value if isinstance(item, str))
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    collect(manifest)
    return list(dict.fromkeys(labels))


def glyph_smoke_report(manifest_path: Path | None = None) -> dict[str, Any]:
    configure_profile()
    import matplotlib.pyplot as plt
    from matplotlib import image as mpimg

    manifest_labels = labels_from_manifest(manifest_path) if manifest_path else []
    labels = list(dict.fromkeys([*BASELINE_GLYPH_LABELS, *manifest_labels]))
    columns = min(3, len(labels))
    rows = math.ceil(len(labels) / columns)
    with tempfile.TemporaryDirectory(prefix="nlqg-glyph-smoke-") as directory:
        root = Path(directory)
        pdf = root / "glyphs.pdf"
        preview = root / "glyphs.png"
        fig = plt.figure(figsize=(4.0 * columns, max(2.0, 1.1 * rows)))
        for index, label in enumerate(labels):
            row, column = divmod(index, columns)
            fig.text(
                (column + 0.5) / columns,
                1.0 - (row + 0.5) / rows,
                label,
                ha="center",
                va="center",
                fontsize=18,
            )
        fig.savefig(pdf, dpi=180)
        plt.close(fig)
        pdf_report = inspect_pdf(pdf, preview=preview, dpi=180)
        rgb = np.asarray(mpimg.imread(preview))[..., :3]
        ink = np.any(rgb < 0.985, axis=-1)
        row_parts = np.array_split(ink, rows, axis=0)
        counts = []
        for index in range(len(labels)):
            row, column = divmod(index, columns)
            column_parts = np.array_split(row_parts[row], columns, axis=1)
            counts.append(int(column_parts[column].sum()))
        ready = all(count > 10 for count in counts)
        return {
            "ready": ready,
            "manifest": str(manifest_path) if manifest_path else None,
            "baseline_labels": BASELINE_GLYPH_LABELS,
            "manifest_labels": manifest_labels,
            "labels": labels,
            "nonwhite_pixels_by_label": dict(zip(labels, counts)),
            "pdf_bytes": pdf_report["bytes"],
            "preview_shape": pdf_report["preview"]["shape"],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("check-env")
    check_glyphs = subcommands.add_parser("check-glyphs")
    check_glyphs.add_argument("--manifest", type=Path)
    render = subcommands.add_parser("render")
    render.add_argument("manifest", type=Path)
    inspect = subcommands.add_parser("inspect")
    inspect.add_argument("png", type=Path)
    inspect_pdf_parser = subcommands.add_parser("inspect-pdf")
    inspect_pdf_parser.add_argument("pdf", type=Path)
    inspect_pdf_parser.add_argument("--preview", type=Path)
    inspect_pdf_parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args()
    if args.command == "check-env":
        report = environment_report()
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["ready"] else 1)
    if args.command == "check-glyphs":
        manifest = args.manifest.resolve() if args.manifest else None
        report = glyph_smoke_report(manifest)
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["ready"] else 1)
    if args.command == "render":
        print(json.dumps(render_figure(args.manifest.resolve()), indent=2))
    if args.command == "inspect":
        print(json.dumps(inspect_png(args.png.resolve()), indent=2))
    if args.command == "inspect-pdf":
        preview = args.preview.resolve() if args.preview else None
        print(json.dumps(inspect_pdf(args.pdf.resolve(), preview, args.dpi), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"[nlqg-plot-style] {error}", file=sys.stderr)
        sys.exit(1)
