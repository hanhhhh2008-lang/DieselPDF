import importlib.machinery
import importlib.util
import json
import os
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace


APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(APP_DIR, "DieselPDF.pyw")
LOADER = importlib.machinery.SourceFileLoader("dieselpdf_app_core_tests", APP_PATH)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
APP_MODULE = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(APP_MODULE)


class LineIntersectionTests(unittest.TestCase):
    def test_crossing_segments_intersect(self):
        point = APP_MODULE.line_intersection((0, 0, 10, 10), (0, 10, 10, 0))
        self.assertAlmostEqual(point[0], 5)
        self.assertAlmostEqual(point[1], 5)

    def test_segment_intersection_rejects_crossing_outside_extents(self):
        point = APP_MODULE.line_intersection((0, 0, 1, 0), (2, -1, 2, 1))
        self.assertIsNone(point)

    def test_apparent_intersection_uses_infinite_lines(self):
        point = APP_MODULE.line_intersection(
            (0, 0, 1, 0),
            (2, -1, 2, 1),
            bounded=False,
        )
        self.assertAlmostEqual(point[0], 2)
        self.assertAlmostEqual(point[1], 0)

    def test_parallel_lines_do_not_intersect(self):
        point = APP_MODULE.line_intersection((0, 0, 10, 0), (0, 2, 10, 2))
        self.assertIsNone(point)

    def test_shared_endpoint_is_an_intersection(self):
        point = APP_MODULE.line_intersection((0, 0, 5, 5), (5, 5, 10, 0))
        self.assertAlmostEqual(point[0], 5)
        self.assertAlmostEqual(point[1], 5)

    def test_intersection_snap_distinguishes_segment_and_apparent_modes(self):
        class FakeCanvas:
            def type(self, _item):
                return "line"

            def itemcget(self, _item, _option):
                return "normal"

            def coords(self, item):
                return {
                    1: [0, 0, 1, 0],
                    2: [2, -1, 2, 1],
                }[item]

        fake_app = SimpleNamespace(
            canvas=FakeCanvas(),
            _current_entries=lambda: [{"layer": "0", "items": [1, 2]}],
            _layer_visible=lambda _layer: True,
            _segment_intersection=lambda first, second: APP_MODULE.line_intersection(
                first,
                second,
                bounded=True,
            ),
            _infinite_line_intersection=lambda first, second: APP_MODULE.line_intersection(
                first,
                second,
                bounded=False,
            ),
        )

        bounded = APP_MODULE.DieselPDF._line_intersections(
            fake_app,
            {"Intersection"},
            near=(2, 0),
        )
        apparent = APP_MODULE.DieselPDF._line_intersections(
            fake_app,
            {"Apparent Intersection"},
            near=(2, 0),
        )

        self.assertEqual(bounded, [])
        self.assertEqual(apparent, [(2.0, 0.0, "Apparent Intersection")])


class AtomicJsonTests(unittest.TestCase):
    def test_atomic_write_replaces_existing_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "project.dieselpdf.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("old")

            APP_MODULE.write_json_atomic(path, {"version": 1, "pages": []})

            with open(path, "r", encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), {"version": 1, "pages": []})
            self.assertEqual(os.listdir(directory), ["project.dieselpdf.json"])

    def test_failed_serialization_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "project.dieselpdf.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("known-good")

            with self.assertRaises(TypeError):
                APP_MODULE.write_json_atomic(path, {"invalid": object()})

            with open(path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "known-good")
            self.assertEqual(os.listdir(directory), ["project.dieselpdf.json"])


class ApplicationSmokeTests(unittest.TestCase):
    def test_application_constructs_without_opening_a_document(self):
        try:
            app = APP_MODULE.DieselPDF()
        except tk.TclError as exc:
            self.skipTest(f"Tk display is unavailable: {exc}")
        try:
            app.withdraw()
            app.update_idletasks()
            self.assertEqual(app.current_tool, "hand")
            self.assertEqual(app.pages, [{"paper": "A4", "entries": []}])
            self.assertEqual(app.active_document_id, "doc_1")
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
