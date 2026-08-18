from __future__ import annotations

import tempfile
import unittest
from unittest import mock
from pathlib import Path

import cv2
import numpy as np

from roi_editor.core import (
    Circle,
    DetectionSettings,
    detect_circles,
    label_for_index,
    label_in_current_order,
    order_circles,
    read_media_frame,
    swap_circle_identities,
    normalize_radii,
)
from roi_editor.roi_io import circle_to_legacy_row, load_roi_csv, save_roi_bundle, validate_circles


JULY_VIDEO = Path("/Users/ddharmap/dataProcessing/pth2_virtShoal/out_id0_30fps_20260716122351.avi")
JULY_ROI = Path("/Users/ddharmap/dataProcessing/pth2_virtShoal/ROIdef2026-07-16T12_13_33.csv")


class CoreTests(unittest.TestCase):
    def test_spreadsheet_labels(self) -> None:
        self.assertEqual(label_for_index(0), "A")
        self.assertEqual(label_for_index(25), "Z")
        self.assertEqual(label_for_index(26), "AA")

    def test_orders_fixed_columns(self) -> None:
        circles = [
            Circle(100, 100, 20),
            Circle(10, 10, 20),
            Circle(100, 10, 20),
            Circle(10, 100, 20),
        ]
        ordered = order_circles(circles, expected_columns=2)
        self.assertEqual([(circle.x, circle.y, circle.label) for circle in ordered], [
            (10, 10, "A1"),
            (100, 10, "A2"),
            (10, 100, "B1"),
            (100, 100, "B2"),
        ])

    def test_infers_rows(self) -> None:
        circles = [Circle(95, 101, 20), Circle(5, 4, 20), Circle(5, 99, 20), Circle(95, 6, 20)]
        ordered = order_circles(circles)
        self.assertEqual([circle.label for circle in ordered], ["A1", "A2", "B1", "B2"])

    def test_swaps_output_identities_without_lexicographic_label_sorting(self) -> None:
        circles = [Circle(index * 10, 0, 5, f"A{index + 1}") for index in range(12)]
        swapped = swap_circle_identities(circles, 1, 10)
        self.assertEqual([circle.label for circle in swapped], [circle.label for circle in circles])
        self.assertEqual(swapped[1].x, 100)
        self.assertEqual(swapped[10].x, 10)

    def test_labels_loaded_rows_without_reordering_identity(self) -> None:
        circles = [Circle(100, 0, 5), Circle(10, 0, 5), Circle(50, 0, 5)]
        labelled = label_in_current_order(circles, expected_columns=3)
        self.assertEqual([circle.x for circle in labelled], [100, 10, 50])
        self.assertEqual([circle.label for circle in labelled], ["A1", "A2", "A3"])

    def test_synthetic_detection(self) -> None:
        image = np.full((360, 520, 3), 220, dtype=np.uint8)
        expected = [(100, 100), (260, 100), (420, 100), (100, 260), (260, 260), (420, 260)]
        for center in expected:
            cv2.circle(image, center, 60, (20, 20, 20), 4, cv2.LINE_AA)
        circles = detect_circles(
            image,
            DetectionSettings(min_radius=50, max_radius=70, sensitivity=30, edge_threshold=80),
        )
        ordered = order_circles(circles, expected_columns=3)
        self.assertEqual(len(ordered), 6)
        for circle, center in zip(ordered, expected):
            self.assertLess(np.hypot(circle.x - center[0], circle.y - center[1]), 5)


class RoiIoTests(unittest.TestCase):
    def test_legacy_row_contract(self) -> None:
        self.assertEqual(circle_to_legacy_row(Circle(150, 170, 119, "A1")), (29, 49, 242, 150, 170, 119))

    def test_loads_comma_and_space_separators(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roi.csv"
            path.write_text("29,49,242,150,170,119\n335 35 230 450 150 113\n", encoding="utf-8")
            circles = load_roi_csv(path)
            self.assertEqual([(circle.x, circle.y, circle.radius) for circle in circles], [(150, 170, 119), (450, 150, 113)])

    def test_save_bundle_round_trip(self) -> None:
        image = np.zeros((300, 400, 3), dtype=np.uint8)
        circles = [Circle(100, 100, 40, "A1"), Circle(250, 100, 40, "A2")]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ROIdef.csv"
            roi, qc, metadata = save_roi_bundle(target, circles, image, "fixture.avi", {"test": True}, expected_count=2)
            self.assertTrue(roi.exists())
            self.assertTrue(qc.exists())
            self.assertTrue(metadata.exists())
            self.assertEqual(len(load_roi_csv(roi)), 2)

    def test_validation_checks_expected_count(self) -> None:
        errors = validate_circles([Circle(10, 10, 5, "A1")], (100, 100, 3), expected_count=2)
        self.assertIn("Expected 2 circles but found 1.", errors)

    def test_validation_rejects_crop_outside_image(self) -> None:
        errors = validate_circles([Circle(1, 1, 20, "A1")], (100, 100, 3))
        self.assertIn("Circle A1 has a padded crop outside the image.", errors)

    def test_validation_rejects_near_duplicate_centres(self) -> None:
        circles = [Circle(100, 100, 40, "A1"), Circle(110, 105, 40, "A2")]
        errors = validate_circles(circles, (300, 300, 3), expected_count=2)
        self.assertIn("Circles A1 and A2 have near-duplicate centres.", errors)

    def test_qc_failure_preserves_previous_bundle(self) -> None:
        image = np.zeros((300, 400, 3), dtype=np.uint8)
        circles = [Circle(100, 100, 40, "A1")]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ROIdef.csv"
            qc = Path(directory) / "ROIdef_qc.png"
            metadata = Path(directory) / "ROIdef.json"
            target.write_text("previous csv\n", encoding="utf-8")
            qc.write_bytes(b"previous qc")
            metadata.write_text("previous metadata\n", encoding="utf-8")
            with mock.patch("roi_editor.roi_io.cv2.imwrite", return_value=False):
                with self.assertRaises(RuntimeError):
                    save_roi_bundle(target, circles, image, "fixture.avi", {}, expected_count=1)
            self.assertEqual(target.read_text(encoding="utf-8"), "previous csv\n")
            self.assertEqual(qc.read_bytes(), b"previous qc")
            self.assertEqual(metadata.read_text(encoding="utf-8"), "previous metadata\n")


@unittest.skipUnless(JULY_VIDEO.exists() and JULY_ROI.exists(), "July PTH2 fixture is not available")
class JulyFixtureIntegrationTests(unittest.TestCase):
    def test_detects_and_orders_all_35_dishes(self) -> None:
        image, metadata = read_media_frame(JULY_VIDEO, frame_index=0, average_frames=30)
        self.assertEqual((metadata["width"], metadata["height"]), (2048, 1380))
        detected = order_circles(detect_circles(image, DetectionSettings()), expected_columns=7)
        expected = order_circles(load_roi_csv(JULY_ROI), expected_columns=7)
        self.assertEqual(len(detected), 35)
        errors = [np.hypot(circle.x - reference.x, circle.y - reference.y) for circle, reference in zip(detected, expected)]
        self.assertLess(float(np.median(errors)), 12)
        self.assertLess(max(errors), 25)
        normalized = normalize_radii(detected)
        radius_errors = [abs(circle.radius - reference.radius) for circle, reference in zip(normalized, expected)]
        self.assertLess(max(radius_errors), 16)


if __name__ == "__main__":
    unittest.main()
