import ast
import unittest
from pathlib import Path


class Phase3DependencyDirectionTests(unittest.TestCase):
    def test_domain_does_not_import_persistence_ui_or_vendor_modules(self):
        root = Path(__file__).resolve().parents[1] / "dieselpdf" / "domain"
        prohibited = (
            "dieselpdf.persistence",
            "dieselpdf.ui",
            "tkinter",
            "fitz",
            "pymupdf",
            "ezdxf",
            "ifcopenshell",
        )
        violations = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                for name in names:
                    if any(name == item or name.startswith(item + ".") for item in prohibited):
                        violations.append(f"{path.relative_to(root)} imports {name}")
        self.assertEqual(violations, [])

    def test_persistence_does_not_import_tkinter_or_vendor_sdks(self):
        root = Path(__file__).resolve().parents[1] / "dieselpdf" / "persistence"
        prohibited = ("tkinter", "fitz", "pymupdf", "ezdxf", "ifcopenshell")
        violations = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                for name in names:
                    if any(name == item or name.startswith(item + ".") for item in prohibited):
                        violations.append(f"{path.relative_to(root)} imports {name}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
