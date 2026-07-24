import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "dieselpdf" / "domain"
FORBIDDEN_PREFIXES = ("tkinter","fitz","pymupdf","ezdxf","ifcopenshell","PyNite","Pynite","opensees","KratosMultiphysics","dieselpdf.ui","dieselpdf.adapters","dieselpdf.persistence")

class DomainDependencyDirectionTests(unittest.TestCase):
    def test_domain_imports_no_ui_vendor_or_persistence_modules(self):
        violations=[]
        for path in DOMAIN.rglob("*.py"):
            tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
            for node in ast.walk(tree):
                modules=[]
                if isinstance(node,ast.Import): modules.extend(alias.name for alias in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module: modules.append(node.module)
                for module in modules:
                    if module.startswith(FORBIDDEN_PREFIXES): violations.append(f"{path.relative_to(ROOT)} imports {module}")
        self.assertEqual(violations,[])

if __name__ == "__main__": unittest.main()
