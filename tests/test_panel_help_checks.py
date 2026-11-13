"""Direkt fältåterkoppling och formaterade, storleksbegränsade figurer."""
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from an_print import Panel


def valid_length(values):
    return values["length"] >= 2*values["height"]


def drawing(values):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'


class TestPanelHelpChecks(unittest.TestCase):
    def test_direct_feedback_restored_state_and_figure_formatting(self):
        def calc(px):
            return px
        calc.panel_schema = {
            "px": ["length", "height"],
            "fields": [
                {"name": "length", "default": 5., "help": "l < 2h",
                 "help_check": {"validator": __name__+":valid_length", "fields": ["length", "height"]}},
                {"name": "height", "default": 2.}],
            "sections": [{"fields": ["length", "height"], "figure": {
                "renderer": __name__+":drawing", "fields": [], "max_width": 280,
                "caption": "F1 < limit", "caption_html": "F<sub>1</sub>"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            panel = Panel(calc, state_file=Path(tmp)/"state.json")
            helper = panel._help_checks[0]["widget"]
            self.assertIn("&lt;", helper.value)
            self.assertNotIn("anp-help-error", helper._dom_classes)
            panel._field_widgets["height"].value = 3
            self.assertIn("anp-help-error", helper._dom_classes)
            panel._field_widgets["length"].value = 6
            self.assertNotIn("anp-help-error", helper._dom_classes)
            panel._apply_values({"length": 3., "height": 2.})
            self.assertIn("anp-help-error", helper._dom_classes)
            self.assertEqual(panel._figure_records[0]["widget"].layout.max_width, "280px")
            self.assertIn("F<sub>1</sub>", panel._figure_records[0]["widget"].value)
            del calc.panel_schema["sections"][0]["figure"]["caption_html"]
            plain = Panel(calc, state_file=Path(tmp)/"other.json")
            self.assertIn("F1 &lt; limit", plain._figure_records[0]["widget"].value)


if __name__ == "__main__":
    unittest.main()
