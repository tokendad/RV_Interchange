import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("vendor_discovery.py")
SPEC = importlib.util.spec_from_file_location("vendor_discovery", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

FOGATTI_MANUALS_FIXTURE = """
<table>
<tr><td>InstaShower 7</td><td><a href="https://drive.google.com/file/d/ABC123/view?usp=sharing">Download</a></td></tr>
<tr><td>HybridShower 6, 6 Pro, 10, 10 Pro</td><td><a href="https://drive.google.com/open?id=XYZ789">Download</a></td></tr>
<tr><td>RV Electric Induction Cooktop Burner-Opening Instructions</td><td><a href="/files/cooktop-opening.pdf?x=1">Download</a></td></tr>
</table>
"""


class VendorDiscoveryTests(unittest.TestCase):
    def test_fogatti_google_drive_rows_keep_model_context(self):
        parser = MODULE.LinkParser()
        parser.feed(FOGATTI_MANUALS_FIXTURE)
        self.assertEqual(3, len(parser.links))
        href, label, context = parser.links[0]
        self.assertEqual("Download", label)
        self.assertIn("InstaShower 7", context)
        self.assertTrue(MODULE.is_document_link(href, label, context))
        self.assertIn("INSTASHOWER 7", MODULE.model_hint(label, context))

    def test_google_drive_urls_are_canonicalized(self):
        self.assertEqual(
            "https://drive.google.com/file/d/ABC123",
            MODULE.canonicalize("https://drive.google.com/file/d/ABC123/view?usp=sharing"),
        )
        self.assertEqual(
            "https://drive.google.com/file/d/XYZ789",
            MODULE.canonicalize("https://drive.google.com/open?id=XYZ789"),
        )

    def test_opening_instructions_classify_as_installation(self):
        kind, score = MODULE.classify(
            "Download",
            "RV Electric Induction Cooktop Burner-Opening Instructions",
            "cooktop-opening.pdf",
        )
        self.assertEqual("installation_manual", kind)
        self.assertGreaterEqual(score, 9)


if __name__ == "__main__":
    unittest.main()
