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

COLEMAN_NESTED_TABLE_FIXTURE = """
<section id="content">
<table>
<tr><td>9420-391_WIFI-THERMOSTAT_IOM_Manual</td><td>Manuals</td>
<td><a href="/9420-391.pdf">Download</a></td></tr>
<tr><td>CM-160274.01_WiFi-Thermostat-Compatibility-Guide</td><td>Manuals</td>
<td><a href="/CM-160274.01.pdf">Download</a></td></tr>
</table>
</section>
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

    def test_nested_section_keeps_each_table_row_context_isolated(self):
        parser = MODULE.LinkParser()
        parser.feed(COLEMAN_NESTED_TABLE_FIXTURE)

        self.assertEqual(2, len(parser.links))
        self.assertIn("9420-391_WIFI-THERMOSTAT_IOM_Manual", parser.links[0][2])
        self.assertNotIn("CM-160274", parser.links[0][2])
        self.assertIn("CM-160274.01_WiFi-Thermostat-Compatibility-Guide", parser.links[1][2])
        self.assertNotIn("9420-391", parser.links[1][2])

    def test_keyword_bearing_html_category_is_not_a_document(self):
        url = "https://manuals.example/?man=Troubleshooting%20Guides"
        self.assertFalse(MODULE.is_document_link(url, "Troubleshooting Guides", ""))

    def test_canonicalize_preserves_query_driven_html_navigation(self):
        url = "https://manuals.example/?man=Troubleshooting%20Guides"
        self.assertEqual(url, MODULE.canonicalize(url))

    def test_canonicalize_removes_download_tracking_query(self):
        self.assertEqual(
            "https://manuals.example/files/thermostat.pdf",
            MODULE.canonicalize("https://manuals.example/files/thermostat.pdf?download=1"),
        )

    def test_coleman_numeric_first_models_are_extracted_as_hints(self):
        hint = MODULE.model_hint(
            "Download",
            "9420-391 WiFi thermostat; 7330D3371 wall thermostat; 7330 Series controls",
        )
        self.assertIn("9420-391", hint)
        self.assertIn("7330D3371", hint)
        self.assertIn("7330", hint)


if __name__ == "__main__":
    unittest.main()
