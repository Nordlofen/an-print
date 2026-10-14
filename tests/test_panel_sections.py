"""Integration checks for the shared form layout with real ipywidgets."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec("ipywidgets"), "ipywidgets behövs")
class TestPanelSections(unittest.TestCase):
    def setUp(self):
        from an_print import Panel
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.json"
        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()

    def tearDown(self):
        self.temp.cleanup()

    def test_groups_preserve_values_calculation_and_legacy_saved_cases(self):
        import json
        from an_calcs.tra import tvarkraft_dymlingsforband
        from an_print import Panel

        function = tvarkraft_dymlingsforband
        baseline = {f["name"]: f["default"] for f in function.panel_schema["fields"]}
        # A saved case created before sections existed uses the same field keys.
        baseline.update({"l": 55.0, "rho_k_1": 550.0, "M_y_Rk": 3200.0, "f_head_k": 29.4, "l_g": 31.0, "l_p": 3.1})
        baseline["__blocks__"] = {"SR": {"visa": True, "etikett": True, "rader": 6}}
        # Use the panel's established key convention, independently of layout.
        fresh = Panel(function, key="Sparat", state_file=self.path)
        self.path.write_text(json.dumps({fresh._last_key: baseline}))
        panel = Panel(function, key="Sparat", state_file=self.path)
        expected = [baseline[name] for name in function.panel_schema["px"]]
        self.assertEqual(panel.to_px(), expected)
        self.assertEqual(set(panel._field_widgets), set(function.panel_schema["px"]))
        self.assertEqual(panel.funktion(panel.to_px()), function(expected))
        for title in ("Förband", "Anslutna delar", "Förbindare", "Placering"):
            self.assertEqual(panel._sections[title].selected_index, 0)
        self.assertIsNone(panel._sections["Kompletterande värden"].selected_index)
        diameter = panel._field_widgets["d"]
        panel._sections["Förbindare"].selected_index = None
        panel._sections["Förbindare"].selected_index = 0
        self.assertIs(panel._field_widgets["d"], diameter)
        self.assertEqual(panel.to_px(), expected)
        panel._field_widgets["forbindartyp"].value = "traskruv"
        self.assertNotIn(panel._field_rows["spiktyp"], self.visible_rows(panel))
        self.assertIn(panel._field_rows["l_gang"], self.visible_rows(panel))
        panel._field_widgets["l_ef_manuell"].value = True
        panel._field_widgets["l_ef"].value = 28.0
        self.assertIn(panel._field_rows["l_ef"], self.visible_rows(panel))
        panel._field_widgets["materialtyp_1"].value = "stal"
        self.assertNotIn(panel._field_rows["rho_k_1"], self.visible_rows(panel))
        self.assertEqual(panel._field_widgets["rho_k_1"].value, 550.0)
        panel._save_last_values()
        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()
        reopened = Panel(function, key="Sparat", state_file=self.path)
        self.assertEqual(reopened.to_px(), panel.to_px())
        self.assertIn(reopened._field_rows["l_ef"], self.visible_rows(reopened))
        self.assertNotIn(reopened._field_rows["rho_k_1"], self.visible_rows(reopened))

    @staticmethod
    def visible_rows(panel):
        return [row for group in panel._scalar_field_groups for row in group["box"].children]

    def test_soil_rows_and_locked_width_survive_layout_and_save(self):
        from an_calcs.geo import baddmodul
        from an_print import Panel

        panel = Panel(baddmodul, key="Vägg", state_file=self.path)
        table = panel._table_widgets["jordlager"]
        table.remove_row(table.rows[-1])
        self.assertEqual(len(table.rows), 1)
        self.assertTrue(table.rows[0]["remove_button"].disabled)
        table.remove_row(table.rows[0])
        self.assertEqual(len(table.rows), 1)
        table.add_row({"dz": 2, "Ek": 25, "gamma_m": 1.4})
        self.assertEqual(len(table.rows), 2)
        self.assertFalse(table.rows[0]["remove_button"].disabled)
        self.assertIn("rad 2", table.rows[1]["controls"]["dz"].description)
        panel._field_widgets["by"].value = 4.2
        panel._field_widgets["typ"].value = "VS"
        self.assertTrue(panel._field_widgets["by"].disabled)
        self.assertEqual(panel._field_widgets["F"].description, "Linjelast [kN/m]")
        panel._save_last_values()
        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()
        reopened = Panel(baddmodul, key="Vägg", state_file=self.path)
        self.assertEqual(reopened.to_px(), panel.to_px())
        reopened._field_widgets["typ"].value = "PS"
        self.assertEqual(reopened._field_widgets["by"].value, 4.2)
        self.assertEqual(reopened._table_widgets["jordlager"].rows[1]["controls"]["dz"].value, 2)

    def test_partial_sections_keep_unassigned_fields_and_reject_duplicates(self):
        from an_print import Panel

        def calc(px):
            return px
        calc.panel_schema = {
            "px": ["a", "b"],
            "fields": [{"name": "a", "default": 1.0}, {"name": "b", "default": 2.0}],
            "sections": [{"title": "Första", "fields": ["a"]}],
        }
        panel = Panel(calc, state_file=self.path)
        self.assertEqual(panel.to_px(), [1, 2])
        self.assertEqual(len(self.visible_rows(panel)), 2)
        calc.panel_schema["sections"].append({"fields": ["a"]})
        with self.assertRaisesRegex(ValueError, "upprepat fält"):
            Panel(calc, state_file=self.path)


if __name__ == "__main__":
    unittest.main()
