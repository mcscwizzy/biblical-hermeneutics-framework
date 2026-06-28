import subprocess
import sys
import unittest


class ComposeTests(unittest.TestCase):
    def run_compose(self, modules: str) -> str:
        result = subprocess.run(
            [sys.executable, "tools/compose.py", "--modules", modules],
            check=True,
            capture_output=True,
            encoding="utf-8",
        )
        return result.stdout

    def test_core_framework_includes_intertextuality(self):
        output = self.run_compose("core.core-framework")

        self.assertRegex(
            output,
            r"Modules \(2, ~\d+ tokens\): core\.core-framework, core\.intertextuality",
        )
        self.assertIn("<!-- core.intertextuality v0.2.0 -->", output)

    def test_dependency_on_core_framework_includes_intertextuality(self):
        output = self.run_compose("book.romans")

        self.assertRegex(
            output,
            r"Modules \(4, ~\d+ tokens\): core\.core-framework, core\.intertextuality, "
            r"genre\.epistle, book\.romans",
        )
        self.assertIn("<!-- core.intertextuality v0.2.0 -->", output)


if __name__ == "__main__":
    unittest.main()
