from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}


@dataclass
class Circle:
    x: float
    y: float
    radius: float
    label: str = ""


@dataclass(frozen=True)
class DetectionSettings:
    min_radius: int = 108
    max_radius: int = 180
    sensitivity: float = 40.0
    edge_threshold: float = 80.0
    accumulator_factor: float = 1.5

    def validated(self) -> "DetectionSettings":
        if self.min_radius < 1:
            raise ValueError("Minimum radius must be at least 1 pixel.")
        if self.max_radius <= self.min_radius:
            raise ValueError("Maximum radius must be greater than minimum radius.")
        if self.sensitivity <= 0 or self.edge_threshold <= 0:
            raise ValueError("Hough thresholds must be positive.")
        if self.accumulator_factor < 1:
            raise ValueError("Accumulator factor must be at least 1.")
        return self


def read_media_frame(
    path: str | Path,
    frame_index: int = 0,
    average_frames: int = 30,
) -> tuple[np.ndarray, dict[str, int | float | str]]:
    """Read an image or median-combine consecutive video frames from *path*."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)

    if source.suffix.lower() in IMAGE_SUFFIXES:
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"OpenCV could not read image: {source}")
        height, width = image.shape[:2]
        return image, {
            "kind": "image",
            "width": width,
            "height": height,
            "frame_index": 0,
            "frames_used": 1,
        }

    if frame_index < 0:
        raise ValueError("Frame index cannot be negative.")
    if average_frames < 1:
        raise ValueError("Frames to average must be at least 1.")

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open video: {source}")
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        frames: list[np.ndarray] = []
        for _ in range(average_frames):
            ok, frame = capture.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))

        if not frames:
            raise ValueError(f"No video frame was available at index {frame_index}.")

        composite = np.median(np.stack(frames), axis=0).astype(np.uint8)
        image = cv2.cvtColor(composite, cv2.COLOR_GRAY2BGR)
        height, width = image.shape[:2]
        return image, {
            "kind": "video",
            "width": width,
            "height": height,
            "frame_index": frame_index,
            "frames_used": len(frames),
            "aggregation": "median",
            "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        }
    finally:
        capture.release()


def detect_circles(image: np.ndarray, settings: DetectionSettings) -> list[Circle]:
    """Detect circular dishes without assuming a count or grid layout."""
    settings.validated()
    if image is None or image.size == 0:
        raise ValueError("Cannot detect circles in an empty image.")

    if image.ndim == 2:
        gray = image
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)

    detected = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=settings.accumulator_factor,
        minDist=max(2, int(round(settings.min_radius * 1.5))),
        param1=settings.edge_threshold,
        param2=settings.sensitivity,
        minRadius=settings.min_radius,
        maxRadius=settings.max_radius,
    )
    if detected is None:
        return []

    return [Circle(float(x), float(y), float(radius)) for x, y, radius in detected[0]]


def label_for_index(index: int) -> str:
    """Return spreadsheet-style row labels: A..Z, AA..AZ, and so on."""
    if index < 0:
        raise ValueError("Label index cannot be negative.")
    result = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(65 + remainder) + result
    return result


def assign_labels(rows: Iterable[Iterable[Circle]]) -> list[Circle]:
    ordered: list[Circle] = []
    for row_index, row in enumerate(rows):
        row_label = label_for_index(row_index)
        for column_index, circle in enumerate(row, start=1):
            ordered.append(replace(circle, label=f"{row_label}{column_index}"))
    return ordered


def relabel_sequential(circles: Iterable[Circle]) -> list[Circle]:
    """Keep the current order and use a single A row for arbitrary layouts."""
    return [replace(circle, label=f"A{index}") for index, circle in enumerate(circles, start=1)]


def label_in_current_order(circles: Iterable[Circle], expected_columns: int = 0) -> list[Circle]:
    """Label an existing CSV sequence without changing its identity-defining order."""
    values = [replace(circle) for circle in circles]
    if expected_columns < 0:
        raise ValueError("Expected columns cannot be negative.")
    columns = expected_columns or max(1, len(values))
    rows = [values[start : start + columns] for start in range(0, len(values), columns)]
    return assign_labels(rows)


def order_circles(
    circles: Iterable[Circle],
    expected_columns: int = 0,
    row_tolerance: float | None = None,
) -> list[Circle]:
    """Order circles top-to-bottom and left-to-right.

    If *expected_columns* is positive, sorted detections are chunked into rows of
    that size. Otherwise rows are inferred from vertical proximity.
    """
    values = [replace(circle) for circle in circles]
    if not values:
        return []
    if expected_columns < 0:
        raise ValueError("Expected columns cannot be negative.")

    by_y = sorted(values, key=lambda circle: (circle.y, circle.x))
    if expected_columns:
        rows = [
            sorted(by_y[start : start + expected_columns], key=lambda circle: circle.x)
            for start in range(0, len(by_y), expected_columns)
        ]
        return assign_labels(rows)

    typical_radius = float(np.median([circle.radius for circle in values]))
    tolerance = row_tolerance if row_tolerance is not None else max(8.0, typical_radius * 0.8)
    rows: list[list[Circle]] = []
    row_centers: list[float] = []
    for circle in by_y:
        if not rows or abs(circle.y - row_centers[-1]) > tolerance:
            rows.append([circle])
            row_centers.append(circle.y)
        else:
            rows[-1].append(circle)
            row_centers[-1] = float(np.median([item.y for item in rows[-1]]))

    return assign_labels(sorted((sorted(row, key=lambda circle: circle.x) for row in rows), key=lambda row: np.median([circle.y for circle in row])))


def normalize_radii(circles: Iterable[Circle]) -> list[Circle]:
    values = [replace(circle) for circle in circles]
    if not values:
        return []
    radius = float(np.median([circle.radius for circle in values]))
    return [replace(circle, radius=radius) for circle in values]


def swap_circle_identities(circles: Iterable[Circle], first: int, second: int) -> list[Circle]:
    """Exchange which geometry occupies two output rows while preserving labels."""
    values = [replace(circle) for circle in circles]
    if not (0 <= first < len(values) and 0 <= second < len(values)):
        raise IndexError("Circle swap index is out of range.")
    labels = [circle.label for circle in values]
    values[first], values[second] = values[second], values[first]
    for circle, label in zip(values, labels):
        circle.label = label
    return values
