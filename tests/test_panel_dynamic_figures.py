"""Dynamiska figurer är ett frivilligt tillägg utan beräknings- eller state-data."""

import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/"src"))
from an_print import Panel


class TestDynamicFigures(unittest.TestCase):
    def test_renderer_foljer_falt_lasning_och_synlighet(self):
        def calc(px):
            return {}
        calc.panel_schema = {"px":["x"], "fields":[
            {"name":"x", "type":"float", "default":3., "label":"X", "fixed_if":{"field":"fixed","equals":True,"value":10.}},
            {"name":"fixed", "type":"bool", "default":False, "label":"Lås"}],
            "sections":[{"fields":["x","fixed"]}, {"title":"Skiss", "figure":{
                "renderer":"_test_figure:render", "fields":["x"], "caption":"X < Y",
                "visible_if":{"field":"fixed","equals":True}}}]}
        module = types.ModuleType("_test_figure")
        module.render = lambda values: f'<svg><text>{values["x"]}</text></svg>'
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"_test_figure":module}):
            p = Panel(calc, state_file=pathlib.Path(tmp)/"state.json")
            record = p._figure_records[0]
            self.assertEqual(p._section_records[1]["widget"].layout.display, "none")
            self.assertIn("3.0", record["widget"].value)
            self.assertIn("X &lt; Y", record["widget"].value)
            p._field_widgets["fixed"].value = True
            self.assertIsNone(p._section_records[1]["widget"].layout.display)
            self.assertIn("10.0", record["widget"].value)
            p._apply_values({"x":7.,"fixed":False})
            self.assertIn("7.0", record["widget"].value)
            self.assertEqual(p.to_px(), [7.])
            module.render = lambda values: 1/0
            record["render"] = module.render
            p._field_widgets["x"].value = 9
            self.assertIn("Skissen kan inte visas", record["widget"].value)
            self.assertEqual(p.to_px(), [9.])


if __name__ == "__main__":
    unittest.main()
