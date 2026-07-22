from pathlib import Path
import tempfile
import unittest

from tools.bhf_lib import discover_module_paths


class BhfLibTests(unittest.TestCase):
    def test_discover_module_paths_ignores_readmes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "core" / "00-core-framework.md"
            readme = root / "lexical" / "README.md"
            template = root / "core" / "_TEMPLATE.md"
            module.parent.mkdir(parents=True)
            readme.parent.mkdir(parents=True)
            module.write_text("---\nid: core.test\n---\n", encoding="utf-8")
            readme.write_text("# Not a module\n", encoding="utf-8")
            template.write_text("---\nid: core.template\n---\n", encoding="utf-8")

            self.assertEqual(discover_module_paths(root), [module])


if __name__ == "__main__":
    unittest.main()
