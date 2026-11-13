#!/usr/bin/env python3
"""Validate and render audited DFT/TB/SAWF band comparisons."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import matplotlib as mpl
import numpy as np
import scipy
from scipy.optimize import linear_sum_assignment

from nlqg_figure import DEFAULT_COLORS, configure_profile, environment_report


class ValidationError(ValueError):
    """Manifest or input data violate the band-comparison contract."""


class FormalGateBlocked(RuntimeError):
    """A formal comparison failed its qualification gate."""


FORBIDDEN_FIELDS = {
    "fit_offset",
    "fitted_offset",
    "energy_shift",
    "energy_shift_ev",
    "shift_ev",
    "dataset_shift",
    "dataset_shift_ev",
    "offset_fit",
    "model_offset",
}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def fail(message: str) -> None:
    raise ValidationError(message)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(base: Path, raw: str) -> Path:
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def artifact_path(stem: Path, suffix: str) -> Path:
    return stem.parent / f"{stem.name}{suffix}"


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def scan_forbidden_fields(value: Any, location: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).casefold()
            if (
                lowered in FORBIDDEN_FIELDS
                or ("offset" in lowered and lowered != "offset_text")
                or ("shift" in lowered and lowered != "shift_current")
            ):
                fail(f"forbidden dataset-specific energy alignment field at {location}.{key}")
            scan_forbidden_fields(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_forbidden_fields(child, f"{location}[{index}]")


def selection_indices(
    raw: Any,
    size: int,
    label: str,
    *,
    allow_all: bool = False,
) -> np.ndarray:
    if allow_all and raw == "all":
        result = np.arange(size, dtype=np.int64)
    elif isinstance(raw, list):
        if not raw:
            fail(f"{label} must not be empty")
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in raw):
            fail(f"{label} must contain integer zero-based indices")
        result = np.asarray(raw, dtype=np.int64)
    elif isinstance(raw, dict):
        permitted = {"start", "stop", "step"}
        unknown = set(raw) - permitted
        if unknown:
            fail(f"{label} has unsupported fields: {sorted(unknown)}")
        if "start" not in raw or "stop" not in raw:
            fail(f"{label} range requires start and stop")
        start, stop, step = raw["start"], raw["stop"], raw.get("step", 1)
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in (start, stop, step)):
            fail(f"{label} range values must be integers")
        if step <= 0:
            fail(f"{label}.step must be positive")
        result = np.arange(start, stop, step, dtype=np.int64)
        if result.size == 0:
            fail(f"{label} selects no indices")
    else:
        extra = " or 'all'" if allow_all else ""
        fail(f"{label} must be an integer list or half-open range{extra}")
    if np.any(result < 0) or np.any(result >= size):
        fail(f"{label} contains an index outside [0, {size})")
    if np.unique(result).size != result.size:
        fail(f"{label} contains duplicate indices")
    return result


def load_array(base: Path, raw_path: str, array_key: Any = None) -> tuple[np.ndarray, Path]:
    if not isinstance(raw_path, str) or not raw_path:
        fail("data path must be a non-empty string")
    path = resolve(base, raw_path)
    if not path.is_file():
        fail(f"input file does not exist: {path}")
    suffix = path.suffix.casefold()
    if suffix == ".npy":
        if array_key is not None:
            fail(f"array_key is not valid for .npy input: {path}")
        array = np.load(path, allow_pickle=False)
    elif suffix == ".npz":
        if not isinstance(array_key, str) or not array_key:
            fail(f".npz input requires array_key: {path}")
        with np.load(path, allow_pickle=False) as archive:
            if array_key not in archive.files:
                fail(f"array_key {array_key!r} is absent from {path}")
            array = np.array(archive[array_key], copy=True)
    else:
        if array_key is not None:
            fail(f"array_key is supported only for .npz input: {path}")
        delimiter = "," if suffix == ".csv" else None
        array = np.genfromtxt(path, delimiter=delimiter, comments="#", ndmin=2)
    return np.asarray(array), path


def load_dataset(base: Path, spec: dict[str, Any], role: str) -> dict[str, Any]:
    for field in ("id", "label", "data", "energy_columns"):
        if field not in spec:
            fail(f"{role} requires {field}")
    dataset_id = spec["id"]
    if not isinstance(dataset_id, str) or not ID_PATTERN.fullmatch(dataset_id):
        fail(f"{role}.id must match {ID_PATTERN.pattern}")
    if not isinstance(spec["label"], str) or not spec["label"]:
        fail(f"{role}.label must be a non-empty string")
    table, path = load_array(base, spec["data"], spec.get("array_key"))
    if table.ndim != 2 or table.shape[0] < 2 or table.shape[1] < 2:
        fail(f"{role} data must be a two-dimensional table with at least two rows and columns")
    if not np.issubdtype(table.dtype, np.number):
        fail(f"{role} data must be numeric")
    table = np.asarray(table, dtype=float)
    if not np.isfinite(table).all():
        fail(f"{role} data contain NaN or Inf: {path}")
    x_column = spec.get("x_column", 0)
    if not isinstance(x_column, int) or isinstance(x_column, bool):
        fail(f"{role}.x_column must be a zero-based integer")
    if x_column < 0 or x_column >= table.shape[1]:
        fail(f"{role}.x_column is outside table shape {table.shape}")
    energy_columns = selection_indices(
        spec["energy_columns"], table.shape[1], f"{role}.energy_columns"
    )
    if x_column in set(energy_columns.tolist()):
        fail(f"{role}.energy_columns must not include x_column")
    x = table[:, x_column]
    if np.any(np.diff(x) < 0):
        fail(f"{role} x grid must be nondecreasing")
    energies = table[:, energy_columns]
    return {
        "id": dataset_id,
        "label": spec["label"],
        "path": path,
        "sha256": sha256_file(path),
        "x": x,
        "energies_raw": energies,
        "energy_columns": energy_columns,
    }


def cluster_sizes(values: np.ndarray, tolerance_ev: float) -> list[int]:
    ordered = np.sort(np.asarray(values, dtype=float))
    if not ordered.size:
        return []
    sizes: list[int] = []
    start = 0
    for index in range(1, ordered.size):
        if ordered[index] - ordered[index - 1] > tolerance_ev:
            sizes.append(index - start)
            start = index
    sizes.append(ordered.size - start)
    return sizes


def degeneracy_conflicts(
    reference_matched: np.ndarray,
    model_energies: np.ndarray,
    tolerance_ev: float,
) -> list[int]:
    conflicts: list[int] = []
    for ik in range(reference_matched.shape[0]):
        if cluster_sizes(reference_matched[ik], tolerance_ev) != cluster_sizes(
            model_energies[ik], tolerance_ev
        ):
            conflicts.append(ik)
    return conflicts


def automatic_match(
    reference_energies: np.ndarray,
    fitted_indices: np.ndarray,
    model_energies: np.ndarray,
) -> np.ndarray:
    if fitted_indices.size < model_energies.shape[1]:
        fail(
            "automatic matching requires fitted reference candidate count "
            "to be at least the model band count"
        )
    result = np.empty(model_energies.shape, dtype=np.int64)
    for ik in range(model_energies.shape[0]):
        candidates = reference_energies[ik, fitted_indices]
        cost = np.abs(candidates[:, None] - model_energies[ik, None, :])
        rows, columns = linear_sum_assignment(cost)
        if columns.size != model_energies.shape[1]:
            fail(f"rectangular assignment did not cover every model band at k index {ik}")
        ordered = np.empty(model_energies.shape[1], dtype=np.int64)
        ordered[columns] = fitted_indices[rows]
        result[ik] = ordered
    return result


def load_precomputed_map(
    base: Path,
    matching: dict[str, Any],
    nk: int,
    nmodel: int,
    nreference: int,
    fitted_indices: np.ndarray,
) -> tuple[np.ndarray, Path]:
    if "index_map" not in matching:
        fail("precomputed matching requires index_map")
    raw, path = load_array(base, matching["index_map"], matching.get("array_key"))
    if raw.ndim != 2 or raw.shape != (nk, nmodel):
        fail(
            f"precomputed index map shape must be {(nk, nmodel)}, got {tuple(raw.shape)}"
        )
    if not np.issubdtype(raw.dtype, np.integer):
        fail("precomputed index map must have an integer dtype")
    index_map = np.asarray(raw, dtype=np.int64)
    if np.any(index_map < 0) or np.any(index_map >= nreference):
        fail("precomputed index map contains an out-of-range reference index")
    fitted = set(fitted_indices.tolist())
    for ik, row in enumerate(index_map):
        if np.unique(row).size != row.size:
            fail(f"precomputed index map contains duplicate matches at k index {ik}")
        if any(int(value) not in fitted for value in row):
            fail(f"precomputed index map leaves the fitted reference pool at k index {ik}")
    return index_map, path


def verify_precomputed_identity(
    matching: dict[str, Any],
    reference: dict[str, Any],
    model: dict[str, Any],
) -> dict[str, str]:
    identity = matching.get("input_identity")
    if not isinstance(identity, dict):
        fail("precomputed matching requires input_identity")
    expected = {
        "reference_id": reference["id"],
        "reference_data_sha256": reference["sha256"],
        "model_id": model["id"],
        "model_data_sha256": model["sha256"],
    }
    for field, expected_value in expected.items():
        actual = identity.get(field)
        if not isinstance(actual, str) or actual.casefold() != expected_value.casefold():
            fail(
                f"precomputed input_identity.{field} does not match the declared dataset"
            )
    return expected


def matched_reference(
    reference_energies: np.ndarray,
    index_map: np.ndarray,
) -> np.ndarray:
    return np.take_along_axis(reference_energies, index_map, axis=1)


def aggregate_errors(errors: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    selected = np.asarray(errors, dtype=float)[np.asarray(mask, dtype=bool)]
    if selected.size == 0:
        return {"count": 0, "rms_ev": None, "p95_abs_ev": None, "max_abs_ev": None}
    absolute = np.abs(selected)
    return {
        "count": int(selected.size),
        "rms_ev": float(np.sqrt(np.mean(selected * selected))),
        "p95_abs_ev": float(np.percentile(absolute, 95)),
        "max_abs_ev": float(np.max(absolute)),
    }


def per_k_errors(errors: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rms = np.full(errors.shape[0], np.nan, dtype=float)
    maximum = np.full(errors.shape[0], np.nan, dtype=float)
    for ik in range(errors.shape[0]):
        selected = errors[ik, mask[ik]]
        if selected.size:
            rms[ik] = float(np.sqrt(np.mean(selected * selected)))
            maximum[ik] = float(np.max(np.abs(selected)))
    return rms, maximum


def validate_windows(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        fail("comparison.metric_windows must contain at least one window")
    windows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            fail(f"metric_windows[{index}] must be an object")
        for field in ("id", "min_ev", "max_ev"):
            if field not in item:
                fail(f"metric_windows[{index}] requires {field}")
        window_id = item["id"]
        if not isinstance(window_id, str) or not ID_PATTERN.fullmatch(window_id):
            fail(f"metric_windows[{index}].id must match {ID_PATTERN.pattern}")
        if window_id in seen:
            fail(f"duplicate metric window id: {window_id}")
        seen.add(window_id)
        try:
            minimum, maximum = float(item["min_ev"]), float(item["max_ev"])
        except (TypeError, ValueError):
            fail(f"metric_windows[{index}] bounds must be numeric")
        if not math.isfinite(minimum) or not math.isfinite(maximum) or minimum > maximum:
            fail(f"metric_windows[{index}] requires finite min_ev <= max_ev")
        label = item.get("label", window_id)
        if not isinstance(label, str) or not label:
            fail(f"metric_windows[{index}].label must be a non-empty string")
        windows.append({"id": window_id, "label": label, "min_ev": minimum, "max_ev": maximum})
    return windows


def verify_declared_files(
    base: Path,
    raw: Any,
    role: str,
    input_records: list[dict[str, str]],
) -> list[dict[str, str]]:
    if raw is None:
        return []
    paths = raw if isinstance(raw, list) else [raw]
    records: list[dict[str, str]] = []
    for value in paths:
        if not isinstance(value, str) or not value:
            fail(f"{role} paths must be non-empty strings")
        path = resolve(base, value)
        if not path.is_file():
            fail(f"declared {role} file does not exist: {path}")
        record = {"role": role, "path": str(path), "sha256": sha256_file(path)}
        input_records.append(record)
        records.append(record)
    return records


def validate_axes(comparison: dict[str, Any], x: np.ndarray) -> tuple[list[float], list[str]]:
    if "xticks" not in comparison or "xticklabels" not in comparison:
        fail("comparison requires high-symmetry xticks and xticklabels")
    ticks_raw, labels_raw = comparison["xticks"], comparison["xticklabels"]
    if not isinstance(ticks_raw, list) or not isinstance(labels_raw, list) or not ticks_raw:
        fail("xticks and xticklabels must be non-empty lists")
    if len(ticks_raw) != len(labels_raw):
        fail("xticks and xticklabels must have equal length")
    ticks: list[float] = []
    for value in ticks_raw:
        try:
            tick = float(value)
        except (TypeError, ValueError):
            fail("xticks must be numeric")
        if not math.isfinite(tick) or tick < float(x[0]) - 1e-12 or tick > float(x[-1]) + 1e-12:
            fail("xticks must be finite and lie inside the shared x range")
        ticks.append(tick)
    if not all(isinstance(label, str) and label for label in labels_raw):
        fail("xticklabels must be non-empty strings")
    if "ylim" in comparison:
        ylim = comparison["ylim"]
        if (
            not isinstance(ylim, list)
            or len(ylim) != 2
            or not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in ylim)
            or float(ylim[0]) >= float(ylim[1])
        ):
            fail("comparison.ylim must contain two finite increasing numbers")
    return ticks, list(labels_raw)


def validate_core(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        fail(f"manifest does not exist: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read JSON manifest: {error}")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("output"), dict):
        fail("manifest requires an output object")
    if not isinstance(manifest.get("comparison"), dict):
        fail("manifest requires a comparison object")
    scan_forbidden_fields(manifest)
    output = manifest["output"]
    comparison = manifest["comparison"]
    if not isinstance(output.get("stem"), str) or not output["stem"]:
        fail("output.stem must be a non-empty string")
    base = manifest_path.parent
    stem = resolve(base, output["stem"])
    formats = output.get("formats", ["png", "pdf"])
    if not isinstance(formats, list) or not formats or any(item not in {"png", "pdf"} for item in formats):
        fail("output.formats must be a non-empty list containing only png and pdf")
    dpi = output.get("dpi", 600)
    if not isinstance(dpi, int) or isinstance(dpi, bool) or dpi <= 0:
        fail("output.dpi must be a positive integer")
    purpose = comparison.get("purpose")
    if purpose not in {"formal", "diagnostic"}:
        fail("comparison.purpose must be formal or diagnostic")
    energy_reference = comparison.get("energy_reference")
    if not isinstance(energy_reference, dict):
        fail("comparison.energy_reference must be an object")
    if set(("value_ev", "label")) - set(energy_reference):
        fail("energy_reference requires value_ev and label")
    try:
        reference_value = float(energy_reference["value_ev"])
    except (TypeError, ValueError):
        fail("energy_reference.value_ev must be numeric")
    if not math.isfinite(reference_value):
        fail("energy_reference.value_ev must be finite")
    if not isinstance(energy_reference["label"], str) or not energy_reference["label"]:
        fail("energy_reference.label must be a non-empty string")
    reference_spec = comparison.get("reference")
    if not isinstance(reference_spec, dict):
        fail("comparison.reference must be an object")
    reference = load_dataset(base, reference_spec, "reference")
    reference["energies"] = reference["energies_raw"] - reference_value
    fitted_indices = selection_indices(
        reference_spec.get("fitted_band_indices"),
        reference["energies"].shape[1],
        "reference.fitted_band_indices",
    )
    display_indices = selection_indices(
        reference_spec.get("display_band_indices"),
        reference["energies"].shape[1],
        "reference.display_band_indices",
        allow_all=True,
    )
    if not set(fitted_indices.tolist()).issubset(set(display_indices.tolist())):
        fail("reference.display_band_indices must include every fitted band")
    ticks, ticklabels = validate_axes(comparison, reference["x"])
    windows = validate_windows(comparison.get("metric_windows"))
    error_window_id = comparison.get("error_window_id", windows[0]["id"])
    window_ids = {window["id"] for window in windows}
    if error_window_id not in window_ids:
        fail("comparison.error_window_id must identify a declared metric window")
    models_spec = comparison.get("models")
    if not isinstance(models_spec, list) or not models_spec:
        fail("comparison.models must contain at least one model")
    ids = {reference["id"]}
    input_records: list[dict[str, str]] = [
        {
            "role": "manifest",
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
        },
        {
            "role": "reference_data",
            "path": str(reference["path"]),
            "sha256": reference["sha256"],
        },
    ]
    models: list[dict[str, Any]] = []
    blockers: list[str] = []
    tolerance_raw = comparison.get("degeneracy_tolerance_ev")
    tolerance: float | None = None
    if tolerance_raw is not None:
        try:
            tolerance = float(tolerance_raw)
        except (TypeError, ValueError):
            fail("degeneracy_tolerance_ev must be numeric when declared")
        if not math.isfinite(tolerance) or tolerance < 0:
            fail("degeneracy_tolerance_ev must be finite and nonnegative")
    for index, model_spec in enumerate(models_spec):
        if not isinstance(model_spec, dict):
            fail(f"models[{index}] must be an object")
        model = load_dataset(base, model_spec, f"models[{index}]")
        if model["id"] in ids:
            fail(f"duplicate dataset id: {model['id']}")
        ids.add(model["id"])
        if model["x"].shape != reference["x"].shape or not np.allclose(
            model["x"], reference["x"], rtol=0.0, atol=1e-12
        ):
            fail(f"model {model['id']} x grid differs from the reference grid")
        model["energies"] = model["energies_raw"] - reference_value
        usable = model_spec.get("usable_for_bands")
        if not isinstance(usable, bool):
            fail(f"model {model['id']} requires boolean usable_for_bands")
        qualification_label = model_spec.get("qualification_label")
        if not isinstance(qualification_label, str) or not qualification_label:
            fail(f"model {model['id']} requires qualification_label")
        matching = model_spec.get("matching")
        if not isinstance(matching, dict) or matching.get("mode") not in {
            "automatic",
            "precomputed",
        }:
            fail(f"model {model['id']} matching.mode must be automatic or precomputed")
        mode = matching["mode"]
        matching_path: Path | None = None
        precomputed_identity: dict[str, str] | None = None
        if mode == "automatic":
            if tolerance is None:
                fail("automatic matching requires comparison.degeneracy_tolerance_ev")
            index_map = automatic_match(reference["energies"], fitted_indices, model["energies"])
        else:
            precomputed_identity = verify_precomputed_identity(matching, reference, model)
            index_map, matching_path = load_precomputed_map(
                base,
                matching,
                model["energies"].shape[0],
                model["energies"].shape[1],
                reference["energies"].shape[1],
                fitted_indices,
            )
            input_records.append(
                {
                    "role": f"model:{model['id']}:index_map",
                    "path": str(matching_path),
                    "sha256": sha256_file(matching_path),
                }
            )
        matched = matched_reference(reference["energies"], index_map)
        errors = model["energies"] - matched
        if not np.isfinite(errors).all():
            fail(f"model {model['id']} produced non-finite errors")
        if tolerance is None:
            cluster_conflicts: list[int] = []
        else:
            cluster_conflicts = degeneracy_conflicts(matched, model["energies"], tolerance)
        metrics: dict[str, dict[str, Any]] = {
            "all_matched": aggregate_errors(errors, np.ones(errors.shape, dtype=bool))
        }
        masks: dict[str, np.ndarray] = {}
        per_k: dict[str, dict[str, np.ndarray]] = {}
        for window in windows:
            mask = (matched >= window["min_ev"]) & (matched <= window["max_ev"])
            masks[window["id"]] = mask
            metrics[window["id"]] = aggregate_errors(errors, mask)
            rms, maximum = per_k_errors(errors, mask)
            per_k[window["id"]] = {"rms_ev": rms, "max_abs_ev": maximum}
        evidence_records = verify_declared_files(
            base,
            model_spec.get("qualification_evidence"),
            f"model:{model['id']}:qualification_evidence",
            input_records,
        )
        upstream_evidence = verify_declared_files(
            base,
            matching.get("evidence"),
            f"model:{model['id']}:matching_evidence",
            input_records,
        )
        input_records.append(
            {
                "role": f"model:{model['id']}:data",
                "path": str(model["path"]),
                "sha256": model["sha256"],
            }
        )
        model_blockers: list[str] = []
        if not usable:
            model_blockers.append(f"{model['id']}: usable_for_bands=false ({qualification_label})")
        if purpose == "formal" and not evidence_records:
            model_blockers.append(f"{model['id']}: formal comparison lacks qualification_evidence")
        if mode == "automatic" and cluster_conflicts:
            model_blockers.append(
                f"{model['id']}: automatic matching has degeneracy-cluster conflicts "
                f"at {len(cluster_conflicts)} k points"
            )
        blockers.extend(model_blockers)
        models.append(
            {
                **model,
                "usable_for_bands": usable,
                "qualification_label": qualification_label,
                "qualification_evidence": evidence_records,
                "matching_mode": mode,
                "matching_path": matching_path,
                "precomputed_input_identity": precomputed_identity,
                "upstream_method": matching.get("upstream_method"),
                "upstream_evidence": upstream_evidence,
                "index_map": index_map,
                "matched_reference": matched,
                "errors": errors,
                "metrics": metrics,
                "masks": masks,
                "per_k": per_k,
                "cluster_conflicts": cluster_conflicts,
                "model_blockers": model_blockers,
            }
        )
    if purpose == "formal" and blockers:
        render_allowed = False
        status = "NOT_RUN"
        qualification_status = "TB_GATE_FAILED"
    else:
        render_allowed = True
        status = "PASS"
        qualification_status = "PASS" if not blockers else "TB_GATE_FAILED"
    model_reports = []
    for model in models:
        model_reports.append(
            {
                "id": model["id"],
                "label": model["label"],
                "data": str(model["path"]),
                "sha256": model["sha256"],
                "model_band_count": int(model["energies"].shape[1]),
                "matching_mode": model["matching_mode"],
                "matched_reference_indices_shape": list(model["index_map"].shape),
                "energy_set_only": model["matching_mode"] == "automatic",
                "cluster_audit_gate_applied": model["matching_mode"] == "automatic",
                "precomputed_input_identity": model["precomputed_input_identity"],
                "degeneracy_cluster_conflict_count": len(model["cluster_conflicts"]),
                "degeneracy_cluster_conflict_k_indices": model["cluster_conflicts"],
                "usable_for_bands": model["usable_for_bands"],
                "qualification_label": model["qualification_label"],
                "qualification_evidence": model["qualification_evidence"],
                "upstream_method": model["upstream_method"],
                "upstream_evidence": model["upstream_evidence"],
                "qualification_status": "PASS" if not model["model_blockers"] else "TB_GATE_FAILED",
                "blockers": model["model_blockers"],
                "metrics": model["metrics"],
            }
        )
    report = {
        "schema": "nlqg-band-validation-v1",
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "status": status,
        "qualification_status": qualification_status,
        "render_allowed": render_allowed,
        "purpose": purpose,
        "blockers": blockers,
        "energy_reference": {
            "value_ev": reference_value,
            "label": energy_reference["label"],
            "applied_identically_to_all_datasets": True,
        },
        "x_grid": {
            "count": int(reference["x"].size),
            "min": float(reference["x"][0]),
            "max": float(reference["x"][-1]),
            "shared_by_all_inputs": True,
        },
        "reference": {
            "id": reference["id"],
            "label": reference["label"],
            "data": str(reference["path"]),
            "sha256": reference["sha256"],
            "total_band_count": int(reference["energies"].shape[1]),
            "fitted_band_indices": fitted_indices.tolist(),
            "display_band_indices": display_indices.tolist(),
        },
        "degeneracy_tolerance_ev": tolerance,
        "metric_windows": windows,
        "error_window_id": error_window_id,
        "models": model_reports,
        "input_files": input_records,
        "indices_zero_based": True,
        "universal_error_thresholds_applied": False,
    }
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "base": base,
        "stem": stem,
        "formats": formats,
        "dpi": dpi,
        "comparison": comparison,
        "purpose": purpose,
        "reference": reference,
        "fitted_indices": fitted_indices,
        "display_indices": display_indices,
        "ticks": ticks,
        "ticklabels": ticklabels,
        "windows": windows,
        "error_window_id": error_window_id,
        "models": models,
        "report": report,
    }


def validation_output_for(manifest_path: Path, manifest: Any = None) -> Path:
    try:
        if manifest is None:
            manifest = json.loads(manifest_path.read_text())
        stem = resolve(manifest_path.parent, manifest["output"]["stem"])
        return artifact_path(stem, ".band-validation.json")
    except Exception:
        return manifest_path.with_suffix(".band-validation.json")


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    try:
        state = validate_core(manifest_path)
    except Exception as error:
        validation_path = validation_output_for(manifest_path)
        report = {
            "schema": "nlqg-band-validation-v1",
            "manifest": str(manifest_path),
            "status": "INVALID",
            "qualification_status": "NOT_EVALUATED",
            "render_allowed": False,
            "errors": [str(error)],
        }
        json_dump(validation_path, report)
        if isinstance(error, ValidationError):
            raise
        raise ValidationError(str(error)) from error
    validation_path = artifact_path(state["stem"], ".band-validation.json")
    json_dump(validation_path, state["report"])
    state["validation_path"] = validation_path
    return state


def latex_text(value: str) -> str:
    escaped = value
    for source, target in (
        ("\\", r"\textbackslash{}"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("&", r"\&"),
        ("#", r"\#"),
    ):
        escaped = escaped.replace(source, target)
    return escaped


def style_axis(ax: Any) -> None:
    ax.tick_params(which="both", direction="in", top=True, right=True)
    from matplotlib.ticker import FuncFormatter

    def signed_label(value: float, _position: int) -> str:
        if abs(value) < 5e-14:
            value = 0.0
        return rf"\textnormal{{{value:.6g}}}"

    ax.yaxis.set_major_formatter(FuncFormatter(signed_label))
    for spine in ax.spines.values():
        spine.set_linewidth(1.1)


def render_from_state(state: dict[str, Any]) -> dict[str, Any]:
    configure_profile()
    import matplotlib.pyplot as plt

    stem: Path = state["stem"]
    stem.parent.mkdir(parents=True, exist_ok=True)
    comparison = state["comparison"]
    reference = state["reference"]
    x = reference["x"]
    purpose = state["purpose"]
    held_labels = [
        model["qualification_label"]
        for model in state["models"]
        if model["model_blockers"]
    ]
    show_qualification_annotations = comparison.get("show_qualification_annotations", True)
    if not isinstance(show_qualification_annotations, bool):
        fail("comparison.show_qualification_annotations must be boolean")
    banner = None
    if purpose == "diagnostic" and show_qualification_annotations:
        labels = ", ".join(held_labels) if held_labels else "qualification not promoted"
        banner = f"DIAGNOSTIC ONLY -- {labels}"
    bands_fig, bands_ax = plt.subplots(
        figsize=comparison.get("figsize_bands", [6.4, 4.4]), layout="constrained"
    )
    fitted_set = set(state["fitted_indices"].tolist())
    fitted_labeled = False
    unfitted_labeled = False
    for band_index in state["display_indices"]:
        fitted = int(band_index) in fitted_set
        if fitted:
            label = f"{reference['label']} fitted" if not fitted_labeled else None
            fitted_labeled = True
            color, linewidth, zorder = "#606060", 0.8, 2
        else:
            label = f"{reference['label']} unfitted" if not unfitted_labeled else None
            unfitted_labeled = True
            color, linewidth, zorder = "#C2C2C2", 0.6, 1
        bands_ax.plot(
            x,
            reference["energies"][:, int(band_index)],
            color=color,
            linewidth=linewidth,
            linestyle="-",
            label=label,
            zorder=zorder,
        )
    linestyles = ("--", "-.", ":", (0, (5, 1)))
    for index, model in enumerate(state["models"]):
        label = model["label"]
        if purpose == "diagnostic" and show_qualification_annotations and model["model_blockers"]:
            label = f"{label} [{model['qualification_label']}]"
        for band_index in range(model["energies"].shape[1]):
            bands_ax.plot(
                x,
                model["energies"][:, band_index],
                color=DEFAULT_COLORS[index % len(DEFAULT_COLORS)],
                linewidth=1.25,
                linestyle=linestyles[index % len(linestyles)],
                label=label if band_index == 0 else None,
                zorder=3 + index,
            )
    for tick in state["ticks"]:
        bands_ax.axvline(tick, color="#808080", linewidth=0.5, linestyle="--", zorder=0)
    bands_ax.axhline(0.0, color="#606060", linewidth=0.5, linestyle=":", zorder=0)
    bands_ax.set_xlim(float(x[0]), float(x[-1]))
    bands_ax.margins(x=0)
    bands_ax.set_xticks(state["ticks"], state["ticklabels"])
    bands_ax.set_xlabel(comparison.get("xlabel", "Wave-vector path"))
    bands_ax.set_ylabel(comparison.get("ylabel", r"Energy (eV)"))
    if "ylim" in comparison:
        bands_ax.set_ylim(float(comparison["ylim"][0]), float(comparison["ylim"][1]))
    if comparison.get("title"):
        bands_ax.set_title(comparison["title"])
    bands_ax.legend(frameon=False)
    style_axis(bands_ax)
    if banner is not None:
        bands_fig.suptitle(
            latex_text(banner),
            color="#A00000",
            fontsize=9.5,
            fontweight="bold",
        )
    error_window_id = state["error_window_id"]
    errors_fig, errors_ax = plt.subplots(
        figsize=comparison.get("figsize_errors", [6.4, 3.8]), layout="constrained"
    )
    for index, model in enumerate(state["models"]):
        per_k = model["per_k"][error_window_id]
        color = DEFAULT_COLORS[index % len(DEFAULT_COLORS)]
        errors_ax.plot(
            x,
            per_k["rms_ev"],
            color=color,
            linewidth=1.4,
            linestyle="-",
            label=f"{model['label']} RMS",
        )
        errors_ax.plot(
            x,
            per_k["max_abs_ev"],
            color=color,
            linewidth=1.2,
            linestyle="--",
            label=f"{model['label']} max",
        )
    for tick in state["ticks"]:
        errors_ax.axvline(tick, color="#808080", linewidth=0.5, linestyle="--", zorder=0)
    errors_ax.set_xlim(float(x[0]), float(x[-1]))
    errors_ax.margins(x=0)
    errors_ax.set_xticks(state["ticks"], state["ticklabels"])
    errors_ax.set_xlabel(comparison.get("xlabel", "Wave-vector path"))
    errors_ax.set_ylabel(r"Energy error (eV)")
    window_label = next(
        window["label"] for window in state["windows"] if window["id"] == error_window_id
    )
    errors_ax.set_title(comparison.get("error_title", f"Matched-band errors: {window_label}"))
    errors_ax.legend(frameon=False, ncol=2)
    style_axis(errors_ax)
    if banner is not None:
        errors_fig.suptitle(
            latex_text(banner),
            color="#A00000",
            fontsize=9.5,
            fontweight="bold",
        )
    output_files: list[Path] = []
    for extension in state["formats"]:
        bands_path = artifact_path(stem, f"_bands.{extension}")
        errors_path = artifact_path(stem, f"_errors.{extension}")
        save_options: dict[str, Any] = {"dpi": state["dpi"], "bbox_inches": "tight"}
        if extension == "pdf":
            save_options["metadata"] = {
                "Creator": "nlqg_band.py",
                "Producer": "Matplotlib",
                "CreationDate": None,
                "ModDate": None,
            }
        bands_fig.savefig(bands_path, **save_options)
        errors_fig.savefig(errors_path, **save_options)
        output_files.extend((bands_path, errors_path))
    plt.close(bands_fig)
    plt.close(errors_fig)
    arrays: dict[str, np.ndarray] = {
        "x": np.asarray(x, dtype=float),
        "reference_energies_ev": np.asarray(reference["energies"], dtype=float),
        "fitted_band_indices": np.asarray(state["fitted_indices"], dtype=np.int64),
        "display_band_indices": np.asarray(state["display_indices"], dtype=np.int64),
    }
    used_keys: set[str] = set()
    for model in state["models"]:
        key = re.sub(r"[^A-Za-z0-9_]", "_", model["id"])
        if key in used_keys:
            fail("model ids collide after NPZ key normalization")
        used_keys.add(key)
        arrays[f"{key}__reference_indices"] = np.asarray(model["index_map"], dtype=np.int64)
        arrays[f"{key}__matched_reference_energies_ev"] = np.asarray(
            model["matched_reference"], dtype=float
        )
        arrays[f"{key}__model_energies_ev"] = np.asarray(model["energies"], dtype=float)
        arrays[f"{key}__signed_errors_ev"] = np.asarray(model["errors"], dtype=float)
        for window_id, per_k in model["per_k"].items():
            arrays[f"{key}__{window_id}__per_k_rms_ev"] = per_k["rms_ev"]
            arrays[f"{key}__{window_id}__per_k_max_abs_ev"] = per_k["max_abs_ev"]
    matches_path = artifact_path(stem, ".band-matches.npz")
    np.savez_compressed(matches_path, **arrays)
    output_files.append(matches_path)
    output_hashes = [
        {"path": str(path), "sha256": sha256_file(path)} for path in output_files
    ]
    summary = {
        "schema": "nlqg-band-summary-v1",
        "manifest": str(state["manifest_path"]),
        "manifest_sha256": state["report"]["manifest_sha256"],
        "status": "PASS" if purpose == "formal" else "DIAGNOSTIC_ONLY",
        "qualification_status": state["report"]["qualification_status"],
        "purpose": purpose,
        "diagnostic_banner": banner,
        "energy_reference": state["report"]["energy_reference"],
        "x_grid": state["report"]["x_grid"],
        "xlim": [float(x[0]), float(x[-1])],
        "reference": state["report"]["reference"],
        "metric_windows": state["windows"],
        "error_window_id": error_window_id,
        "models": state["report"]["models"],
        "input_files": state["report"]["input_files"],
        "outputs": output_hashes,
        "universal_error_thresholds_applied": False,
    }
    summary_path = artifact_path(stem, ".band-summary.json")
    json_dump(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    summary["matches_path"] = str(matches_path)
    return summary


def render_manifest(manifest_path: Path) -> dict[str, Any]:
    state = validate_manifest(manifest_path)
    if not state["report"]["render_allowed"]:
        raise FormalGateBlocked(
            "formal band comparison blocked: NOT_RUN / TB_GATE_FAILED; "
            f"see {state['validation_path']}"
        )
    return render_from_state(state)


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nlqg-band-self-test-") as raw_temp:
        root = Path(raw_temp)
        x = np.linspace(0.0, 3.0, 7)
        t = np.linspace(-1.0, 1.0, x.size)
        reference_energies = np.column_stack(
            (
                t,
                -t,
                0.5 + 0.02 * t,
                0.5005 + 0.02 * t,
                np.full_like(t, 3.0),
                np.full_like(t, 6.0),
            )
        )
        reference_table = np.column_stack((x, reference_energies))
        permutation = [3, 0, 2, 1]
        delta = np.asarray([0.0001, -0.0001, 0.0001, -0.0001])
        model_energies = reference_energies[:, permutation] + delta[None, :]
        model_table = np.column_stack((x, model_energies))
        np.savetxt(root / "reference.dat", reference_table)
        np.savetxt(root / "model.dat", model_table)
        json_dump(root / "qualification.json", {"status": "PASS"})
        base_manifest = {
            "output": {
                "stem": "automatic",
                "dpi": 120,
                "formats": ["png", "pdf"],
            },
            "comparison": {
                "purpose": "formal",
                "energy_reference": {"value_ev": 0.0, "label": "common synthetic zero"},
                "degeneracy_tolerance_ev": 0.001,
                "reference": {
                    "id": "dft",
                    "label": "DFT",
                    "data": "reference.dat",
                    "x_column": 0,
                    "energy_columns": {"start": 1, "stop": 7},
                    "fitted_band_indices": {"start": 0, "stop": 5},
                    "display_band_indices": "all",
                },
                "models": [
                    {
                        "id": "tb",
                        "label": "TB",
                        "data": "model.dat",
                        "x_column": 0,
                        "energy_columns": {"start": 1, "stop": 5},
                        "usable_for_bands": True,
                        "qualification_label": "USABLE_TB_FOR_BANDS",
                        "qualification_evidence": "qualification.json",
                        "matching": {"mode": "automatic"},
                    }
                ],
                "metric_windows": [
                    {"id": "fit", "label": "fit window", "min_ev": -1.2, "max_ev": 1.2}
                ],
                "error_window_id": "fit",
                "xticks": [0.0, 1.5, 3.0],
                "xticklabels": [
                    r"\textGamma",
                    r"\textnormal{X}",
                    r"\textnormal{M}",
                ],
                "ylim": [-1.5, 6.5],
            },
        }
        automatic_manifest = root / "automatic.json"
        json_dump(automatic_manifest, base_manifest)
        automatic_state = validate_manifest(automatic_manifest)
        auto_model = automatic_state["models"][0]
        if np.any(auto_model["index_map"] == 5):
            raise AssertionError("unfitted band entered automatic matching")
        np.save(root / "matches.npy", auto_model["index_map"])
        precomputed = json.loads(json.dumps(base_manifest))
        precomputed["output"]["stem"] = "precomputed"
        precomputed["comparison"]["models"][0]["matching"] = {
            "mode": "precomputed",
            "index_map": "matches.npy",
            "input_identity": {
                "reference_id": "dft",
                "reference_data_sha256": sha256_file(root / "reference.dat"),
                "model_id": "tb",
                "model_data_sha256": sha256_file(root / "model.dat"),
            },
            "upstream_method": "synthetic identity oracle",
            "evidence": ["qualification.json"],
        }
        precomputed_manifest = root / "precomputed.json"
        json_dump(precomputed_manifest, precomputed)
        precomputed_state = validate_manifest(precomputed_manifest)
        if canonical_json(auto_model["metrics"]) != canonical_json(
            precomputed_state["models"][0]["metrics"]
        ):
            raise AssertionError("automatic and precomputed metrics differ")
        if not np.array_equal(
            auto_model["index_map"], precomputed_state["models"][0]["index_map"]
        ):
            raise AssertionError("automatic and precomputed match maps differ")
        invalid_cases: dict[str, dict[str, Any]] = {}
        forbidden = json.loads(json.dumps(base_manifest))
        forbidden["output"]["stem"] = "invalid_forbidden"
        forbidden["comparison"]["models"][0]["fit_offset"] = 0.1
        invalid_cases["forbidden_shift"] = forbidden
        duplicate = json.loads(json.dumps(precomputed))
        duplicate["output"]["stem"] = "invalid_duplicate"
        duplicate_map = np.array(auto_model["index_map"], copy=True)
        duplicate_map[0, 1] = duplicate_map[0, 0]
        np.save(root / "duplicate.npy", duplicate_map)
        duplicate["comparison"]["models"][0]["matching"]["index_map"] = "duplicate.npy"
        invalid_cases["duplicate_match"] = duplicate
        outside = json.loads(json.dumps(precomputed))
        outside["output"]["stem"] = "invalid_outside"
        outside_map = np.array(auto_model["index_map"], copy=True)
        outside_map[0, 0] = 5
        np.save(root / "outside.npy", outside_map)
        outside["comparison"]["models"][0]["matching"]["index_map"] = "outside.npy"
        invalid_cases["unfitted_match"] = outside
        out_of_range = json.loads(json.dumps(precomputed))
        out_of_range["output"]["stem"] = "invalid_index"
        invalid_index_map = np.array(auto_model["index_map"], copy=True)
        invalid_index_map[0, 0] = 99
        np.save(root / "invalid_index.npy", invalid_index_map)
        out_of_range["comparison"]["models"][0]["matching"]["index_map"] = "invalid_index.npy"
        invalid_cases["out_of_range_index"] = out_of_range
        wrong_identity = json.loads(json.dumps(precomputed))
        wrong_identity["output"]["stem"] = "invalid_identity"
        wrong_identity["comparison"]["models"][0]["matching"]["input_identity"][
            "model_data_sha256"
        ] = "0" * 64
        invalid_cases["precomputed_identity_mismatch"] = wrong_identity
        mismatched = json.loads(json.dumps(base_manifest))
        mismatched["output"]["stem"] = "invalid_x"
        bad_x_table = np.array(model_table, copy=True)
        bad_x_table[2, 0] += 0.01
        np.savetxt(root / "bad_x.dat", bad_x_table)
        mismatched["comparison"]["models"][0]["data"] = "bad_x.dat"
        invalid_cases["x_grid_mismatch"] = mismatched
        nonfinite = json.loads(json.dumps(base_manifest))
        nonfinite["output"]["stem"] = "invalid_nonfinite"
        bad_table = np.array(model_table, copy=True)
        bad_table[1, 2] = np.nan
        np.savetxt(root / "nonfinite.dat", bad_table)
        nonfinite["comparison"]["models"][0]["data"] = "nonfinite.dat"
        invalid_cases["nonfinite"] = nonfinite
        invalid_results: dict[str, bool] = {}
        for name, manifest in invalid_cases.items():
            path = root / f"{name}.json"
            json_dump(path, manifest)
            try:
                validate_core(path)
            except ValidationError:
                invalid_results[name] = True
            else:
                raise AssertionError(f"invalid case did not fail-stop: {name}")
        conflict = json.loads(json.dumps(base_manifest))
        conflict["output"]["stem"] = "conflict"
        conflict_table = np.array(model_table, copy=True)
        conflict_table[:, 1] += 0.01
        np.savetxt(root / "conflict.dat", conflict_table)
        conflict["comparison"]["models"][0]["data"] = "conflict.dat"
        conflict_manifest = root / "conflict.json"
        json_dump(conflict_manifest, conflict)
        conflict_state = validate_manifest(conflict_manifest)
        if conflict_state["report"]["render_allowed"]:
            raise AssertionError("formal degeneracy conflict did not block rendering")
        held = json.loads(json.dumps(base_manifest))
        held["output"]["stem"] = "held_formal"
        held["comparison"]["models"][0]["usable_for_bands"] = False
        held["comparison"]["models"][0]["qualification_label"] = "TB_GATE_FAILED"
        held_manifest = root / "held_formal.json"
        json_dump(held_manifest, held)
        try:
            render_manifest(held_manifest)
        except FormalGateBlocked:
            pass
        else:
            raise AssertionError("formal held model unexpectedly rendered")
        if artifact_path(root / "held_formal", "_bands.png").exists():
            raise AssertionError("formal gate failure produced a PNG")
        if artifact_path(root / "held_formal", "_bands.pdf").exists():
            raise AssertionError("formal gate failure produced a PDF")
        diagnostic = json.loads(json.dumps(held))
        diagnostic["output"]["stem"] = "held_diagnostic"
        diagnostic["comparison"]["purpose"] = "diagnostic"
        diagnostic_manifest = root / "held_diagnostic.json"
        json_dump(diagnostic_manifest, diagnostic)
        diagnostic_summary = render_manifest(diagnostic_manifest)
        if (
            not diagnostic_summary["diagnostic_banner"]
            or "DIAGNOSTIC ONLY" not in diagnostic_summary["diagnostic_banner"]
        ):
            raise AssertionError("diagnostic render lacks a visible banner declaration")
        for extension in ("png", "pdf"):
            if not artifact_path(root / "held_diagnostic", f"_bands.{extension}").is_file():
                raise AssertionError(f"diagnostic render lacks bands {extension}")
        if diagnostic_summary["xlim"] != [0.0, 3.0]:
            raise AssertionError("rendered x limits do not equal the data range")
        for record in diagnostic_summary["outputs"]:
            if sha256_file(Path(record["path"])) != record["sha256"]:
                raise AssertionError("band summary contains an incorrect output hash")
        digest_payload = {
            "metrics": auto_model["metrics"],
            "matches": auto_model["index_map"].tolist(),
            "invalid_results": invalid_results,
            "conflict_count": len(conflict_state["models"][0]["cluster_conflicts"]),
            "diagnostic_status": diagnostic_summary["status"],
            "xlim": diagnostic_summary["xlim"],
        }
        digest = hashlib.sha256(canonical_json(digest_payload).encode()).hexdigest()
        return {
            "status": "PASS",
            "deterministic_digest": digest,
            "automatic_precomputed_equal": True,
            "rectangular_matching": {
                "reference_fitted_bands": 5,
                "model_bands": 4,
            },
            "crossing_and_near_degeneracy": True,
            "degeneracy_conflict_blocked": True,
            "formal_gate_no_figures": True,
            "diagnostic_rendered_with_banner": True,
            "unfitted_excluded_from_metrics": True,
            "xlim_equals_data_range": True,
            "summary_output_hashes_verified": True,
            "invalid_cases": invalid_results,
        }


def check_environment() -> dict[str, Any]:
    report = environment_report()
    report.update(
        {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": mpl.__version__,
        }
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("check-env")
    validate_parser = subcommands.add_parser("validate")
    validate_parser.add_argument("manifest", type=Path)
    render_parser = subcommands.add_parser("render")
    render_parser.add_argument("manifest", type=Path)
    subcommands.add_parser("self-test")
    args = parser.parse_args()
    try:
        if args.command == "check-env":
            report = check_environment()
            print(json.dumps(report, indent=2, ensure_ascii=False))
            raise SystemExit(0 if report.get("ready") else 1)
        if args.command == "validate":
            state = validate_manifest(args.manifest)
            print(json.dumps(state["report"], indent=2, ensure_ascii=False))
            raise SystemExit(0 if state["report"]["render_allowed"] else 2)
        if args.command == "render":
            summary = render_manifest(args.manifest)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            raise SystemExit(0)
        if args.command == "self-test":
            print(json.dumps(self_test(), indent=2, ensure_ascii=False))
            raise SystemExit(0)
    except FormalGateBlocked as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
    except ValidationError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
