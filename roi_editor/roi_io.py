from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from .core import Circle


def circle_to_legacy_row(circle: Circle) -> tuple[int, int, int, int, int, int]:
    xc = int(round(circle.x))
    yc = int(round(circle.y))
    radius = int(round(circle.radius))
    padding_radius = radius + 2
    return (
        xc - padding_radius,
        yc - padding_radius,
        padding_radius * 2,
        xc,
        yc,
        radius,
    )


def load_roi_csv(path: str | Path) -> list[Circle]:
    circles: list[Circle] = []
    for line_number, raw_line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = [field for field in re.split(r"[\s,]+", line) if field]
        if len(fields) != 6:
            raise ValueError(f"ROI row {line_number} has {len(fields)} fields; expected 6.")
        try:
            _x, _y, _width, xc, yc, radius = (int(round(float(field))) for field in fields)
        except ValueError as error:
            raise ValueError(f"ROI row {line_number} contains a non-numeric field.") from error
        circles.append(Circle(float(xc), float(yc), float(radius)))
    if not circles:
        raise ValueError("ROI file contains no circles.")
    return circles


def validate_circles(
    circles: Iterable[Circle],
    image_shape: tuple[int, ...] | None = None,
    expected_count: int = 0,
) -> list[str]:
    values = list(circles)
    errors: list[str] = []
    if not values:
        errors.append("No circles are defined.")
        return errors
    if expected_count and len(values) != expected_count:
        errors.append(f"Expected {expected_count} circles but found {len(values)}.")

    labels = [circle.label for circle in values if circle.label]
    if len(labels) != len(set(labels)):
        errors.append("Circle labels must be unique.")

    height = width = None
    if image_shape is not None:
        height, width = image_shape[:2]
    for index, circle in enumerate(values, start=1):
        name = circle.label or str(index)
        if not np.isfinite([circle.x, circle.y, circle.radius]).all():
            errors.append(f"Circle {name} contains a non-finite value.")
            continue
        if circle.radius <= 0:
            errors.append(f"Circle {name} has a non-positive radius.")
        if width is not None and height is not None:
            if not (0 <= circle.x < width and 0 <= circle.y < height):
                errors.append(f"Circle {name} has a centre outside the image.")
                continue
            x, y, crop_width, _xc, _yc, _radius = circle_to_legacy_row(circle)
            if x < 0 or y < 0 or x + crop_width > width or y + crop_width > height:
                errors.append(f"Circle {name} has a padded crop outside the image.")

    for first_index, first in enumerate(values):
        if not np.isfinite([first.x, first.y, first.radius]).all() or first.radius <= 0:
            continue
        for second_index, second in enumerate(values[first_index + 1 :], start=first_index + 1):
            if not np.isfinite([second.x, second.y, second.radius]).all() or second.radius <= 0:
                continue
            center_distance = float(np.hypot(first.x - second.x, first.y - second.y))
            near_duplicate_threshold = 0.5 * min(first.radius, second.radius)
            if center_distance < near_duplicate_threshold:
                first_name = first.label or str(first_index + 1)
                second_name = second.label or str(second_index + 1)
                errors.append(
                    f"Circles {first_name} and {second_name} have near-duplicate centres."
                )
    return errors


def render_qc_overlay(image: np.ndarray, circles: Iterable[Circle]) -> np.ndarray:
    output = image.copy()
    for index, circle in enumerate(circles, start=1):
        center = (int(round(circle.x)), int(round(circle.y)))
        radius = int(round(circle.radius))
        cv2.circle(output, center, radius, (0, 220, 0), 3, cv2.LINE_AA)
        cv2.circle(output, center, 4, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.putText(
            output,
            circle.label or str(index),
            (center[0] - 18, center[1] + 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    return output


def save_roi_bundle(
    path: str | Path,
    circles: Iterable[Circle],
    image: np.ndarray,
    source_path: str | Path | None,
    settings: dict[str, object],
    expected_count: int = 0,
) -> tuple[Path, Path, Path]:
    target = Path(path)
    values = list(circles)
    errors = validate_circles(values, image.shape, expected_count)
    if errors:
        raise ValueError("\n".join(errors))
    target.parent.mkdir(parents=True, exist_ok=True)

    rows = [circle_to_legacy_row(circle) for circle in values]
    temporary_paths: list[Path] = []
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as temporary_csv:
            csv_temporary_path = Path(temporary_csv.name)
            temporary_paths.append(csv_temporary_path)
            for row in rows:
                temporary_csv.write(",".join(str(value) for value in row) + "\n")
            temporary_csv.flush()
            os.fsync(temporary_csv.fileno())

        round_trip = [circle_to_legacy_row(circle) for circle in load_roi_csv(csv_temporary_path)]
        if round_trip != rows:
            raise RuntimeError("Staged ROI file failed round-trip verification.")

        qc_path = target.with_name(f"{target.stem}_qc.png")
        qc_descriptor, qc_name = tempfile.mkstemp(prefix=f".{qc_path.stem}.", suffix=".png", dir=target.parent)
        os.close(qc_descriptor)
        qc_temporary_path = Path(qc_name)
        temporary_paths.append(qc_temporary_path)
        if not cv2.imwrite(str(qc_temporary_path), render_qc_overlay(image, values)):
            raise RuntimeError(f"Could not stage QC image for: {qc_path}")

        metadata_path = target.with_suffix(".json")
        metadata = {
            "format_version": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_path": str(source_path) if source_path else None,
            "image_width": int(image.shape[1]),
            "image_height": int(image.shape[0]),
            "legacy_roi_path": str(target),
            "qc_image_path": str(qc_path),
            "settings": settings,
            "circles": [asdict(circle) for circle in values],
        }
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{metadata_path.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as temporary_metadata:
            metadata_temporary_path = Path(temporary_metadata.name)
            temporary_paths.append(metadata_temporary_path)
            temporary_metadata.write(json.dumps(metadata, indent=2) + "\n")
            temporary_metadata.flush()
            os.fsync(temporary_metadata.fileno())

        _replace_bundle_atomically(
            [
                (csv_temporary_path, target),
                (qc_temporary_path, qc_path),
                (metadata_temporary_path, metadata_path),
            ]
        )
        return target, qc_path, metadata_path
    finally:
        for temporary_path in temporary_paths:
            if temporary_path.exists():
                temporary_path.unlink()


def _replace_bundle_atomically(staged_files: list[tuple[Path, Path]]) -> None:
    """Install a staged bundle and restore every previous file if commit fails."""
    backups: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    try:
        for _staged, destination in staged_files:
            if not destination.exists():
                continue
            descriptor, backup_name = tempfile.mkstemp(
                prefix=f".{destination.name}.", suffix=".backup", dir=destination.parent
            )
            os.close(descriptor)
            backup = Path(backup_name)
            backup.unlink()
            os.replace(destination, backup)
            backups.append((backup, destination))

        for staged, destination in staged_files:
            os.replace(staged, destination)
            installed.append(destination)
    except Exception:
        for destination in reversed(installed):
            if destination.exists():
                destination.unlink()
        for backup, destination in reversed(backups):
            if backup.exists():
                os.replace(backup, destination)
        raise
    else:
        for backup, _destination in backups:
            if backup.exists():
                backup.unlink()
