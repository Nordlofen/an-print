import os
import pathlib
import re
import sys
import tempfile
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "an-print" / "src"))
sys.path.insert(0, str(ROOT / "an-calcs" / "src"))


class _Widget:
    def __init__(self, value=None, description="", children=None, **kwargs):
        self.value = value
        self.description = description
        self.children = list(children or [])
        self.kwargs = kwargs
        self.layout = kwargs.get("layout", {})
        self._observers = []

    def observe(self, callback, names=None):
        self._observers.append((callback, names))

    def set_value(self, value):
        old = self.value
        self.value = value
        change = {"name": "value", "old": old, "new": value, "owner": self}
        for callback, names in self._observers:
            if names in (None, "value") or (isinstance(names, (list, tuple, set)) and "value" in names):
                callback(change)


class _Button(_Widget):
    def __init__(self, description="", button_style="", **kwargs):
        super().__init__(description=description, button_style=button_style, **kwargs)
        self._callbacks = []

    def on_click(self, callback):
        self._callbacks.append(callback)

    def click(self):
        for callback in self._callbacks:
            callback(self)


class _Output(_Widget):
    def clear_output(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _Dropdown(_Widget):
    def __init__(self, options=None, value=None, description="", **kwargs):
        super().__init__(value=value, description=description, options=options or [], **kwargs)
        self.options = options or []


class FakeWidgets(types.SimpleNamespace):
    def __init__(self):
        super().__init__(
            HTML=lambda value="", **kwargs: _Widget(value=value, **kwargs),
            Label=lambda value="", **kwargs: _Widget(value=value, **kwargs),
            VBox=lambda children=None, **kwargs: _Widget(children=children, **kwargs),
            HBox=lambda children=None, **kwargs: _Widget(children=children, **kwargs),
            Button=_Button,
            FloatText=lambda value=0.0, description="", **kwargs: _Widget(
                value=value, description=description, **kwargs
            ),
            IntText=lambda value=0, description="", **kwargs: _Widget(
                value=value, description=description, **kwargs
            ),
            Text=lambda value="", description="", **kwargs: _Widget(
                value=value, description=description, **kwargs
            ),
            Checkbox=lambda value=False, description="", **kwargs: _Widget(
                value=value, description=description, **kwargs
            ),
            Dropdown=_Dropdown,
            Output=_Output,
            Layout=lambda **kwargs: kwargs,
        )


class TestPanel(unittest.TestCase):
    def setUp(self):
        self._old_ipywidgets = sys.modules.get("ipywidgets")
        sys.modules["ipywidgets"] = FakeWidgets()
        self._old_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        from an_print import Panel

        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()
        Panel._STATE_FILE = None

    def tearDown(self):
        from an_print import Panel

        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()
        Panel._STATE_FILE = None
        os.chdir(self._old_cwd)
        self._tmpdir.cleanup()
        if self._old_ipywidgets is None:
            sys.modules.pop("ipywidgets", None)
        else:
            sys.modules["ipywidgets"] = self._old_ipywidgets

    def _label_text(self, field_row):
        return re.sub("<[^>]+>", "", field_row.children[0].value)

    def test_bygger_px_for_allmanna_barighetsekvationen(self):
        from an_calcs.geo import allmanna_barighetsekvationen
        from an_print import Panel

        panel = Panel(allmanna_barighetsekvationen)

        self.assertEqual(len(panel.to_px()), 25)
        self.assertEqual(panel.to_px()[0], 1.4)
        self.assertEqual(panel.to_px()[2], 1)

        panel._field_widgets["lang"].value = 0
        self.assertEqual(panel.to_px()[2], 0)

    def test_tabellfalt_bygger_parallella_listor(self):
        from an_calcs.geo import sattning
        from an_print import Panel

        panel = Panel(sattning)
        px = panel.to_px()

        self.assertEqual(px[0], "PS")
        self.assertEqual(px[2], [1.0, 1.0])
        self.assertEqual(px[3], [10.0, 15.0])
        self.assertEqual(px[4], [1.0, 1.0])

    def test_calculate_sparar_resultat_och_anropar_calcblock(self):
        import an_print.calcblock as calcblock_module
        from an_print import Panel

        calls = []

        def funktion(px):
            return {
                "metodbeskrivning": {"title": "MB", "items": []},
                "indata": {"title": "ID", "items": []},
                "delresultat": {"title": "DR", "items": []},
                "slutresultat": {"title": "SR", "items": []},
                "ekvationer": {"title": "EKV", "items": []},
            }

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a", "flag", "val"],
            "fields": [
                {"name": "a", "type": "float", "default": 2.0},
                {"name": "flag", "type": "bool", "default": True},
                {
                    "name": "val",
                    "type": "choice",
                    "default": "x",
                    "options": [{"label": "X", "value": "x"}],
                },
            ],
        }

        class FakeCalcBlock:
            def __init__(self, details):
                self.details = details

            def MB(self, **kwargs):
                calls.append(("MB", kwargs))

            def ID(self, **kwargs):
                calls.append(("ID", kwargs))

            def DR(self, **kwargs):
                calls.append(("DR", kwargs))

            def EKV(self, **kwargs):
                calls.append(("EKV", kwargs))

            def SR(self, **kwargs):
                calls.append(("SR", kwargs))

        original = calcblock_module.CalcBlock
        calcblock_module.CalcBlock = FakeCalcBlock
        try:
            panel = Panel(funktion)
            details = panel.calculate()
        finally:
            calcblock_module.CalcBlock = original

        self.assertEqual(panel.px, [2.0, True, "x"])
        self.assertIs(panel.details, details)
        self.assertIsInstance(panel.cb, FakeCalcBlock)
        self.assertEqual([name for name, _kwargs in calls], ["MB", "ID", "DR", "EKV", "SR"])
        self.assertEqual(calls[1][1], {"visa": True, "etikett": True, "rader": 15})
        self.assertEqual(calls[3][1], {"visa": False, "etikett": True, "rader": 15})

    def test_scalarfalt_laggs_ut_kolumnvis_i_schemaordning(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a", "b", "c", "d", "e"],
            "fields": [
                {"name": "a", "type": "float", "label": "A", "default": 1.0},
                {"name": "b", "type": "float", "label": "B", "default": 2.0},
                {"name": "c", "type": "float", "label": "C", "default": 3.0},
                {"name": "d", "type": "float", "label": "D", "default": 4.0},
                {"name": "e", "type": "float", "label": "E", "default": 5.0},
            ],
        }

        panel = Panel(funktion)
        field_rows = panel.widget.children[1].children[0].children
        row_labels = []
        for row in field_rows:
            row_labels.append([self._label_text(field_row) for field_row in row.children if field_row.children])

        self.assertEqual(row_labels, [["A", "D"], ["B", "E"], ["C"]])
        self.assertEqual(panel.to_px(), [1.0, 2.0, 3.0, 4.0, 5.0])
        first_label = field_rows[0].children[0].children[0]
        self.assertIn("white-space: normal", first_label.value)
        self.assertEqual(first_label.layout.get("width"), "210px")
        self.assertEqual(field_rows[0].children[1].layout.get("width"), "80px")
        self.assertEqual(field_rows[0].children[0].layout.get("width"), "380px")
        self.assertEqual(field_rows[0].children[0].children[1].layout.get("width"), "70px")

    def test_visible_if_styr_faltrad(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["direkt", "last", "M_Ed"],
            "fields": [
                {"name": "direkt", "type": "bool", "label": "Direkt", "default": False},
                {"name": "last", "type": "float", "label": "Last", "default": 1.0, "visible_if": {"field": "direkt", "equals": False}},
                {"name": "M_Ed", "type": "float", "label": "Moment", "default": 2.0, "visible_if": {"field": "direkt", "equals": True}},
            ],
        }

        panel = Panel(funktion)

        self.assertEqual(panel._field_widgets["direkt"].kwargs.get("indent"), False)
        self.assertEqual(panel._field_widgets["direkt"].layout.get("width"), "70px")
        field_rows = panel.widget.children[1].children[0].children
        row_labels = [[self._label_text(field_row) for field_row in row.children if field_row.children] for row in field_rows]
        self.assertEqual(row_labels, [["Direkt", "Last"]])

        panel._field_widgets["direkt"].set_value(True)

        field_rows = panel.widget.children[1].children[0].children
        row_labels = [[self._label_text(field_row) for field_row in row.children if field_row.children] for row in field_rows]
        self.assertEqual(row_labels, [["Direkt", "Moment"]])

    def test_tom_symbol_visar_inte_faltnamn(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["flag"],
            "fields": [
                {"name": "flag", "type": "bool", "label": "Flagga", "symbol": "", "default": True},
            ],
        }

        panel = Panel(funktion)
        field_row = panel.widget.children[1].children[0].children[0].children[0]

        self.assertEqual(field_row.children[1].value, "<span style='display: inline-block; padding-left: 8px;'></span>")

    def test_funktion_utan_schema_ger_tydligt_fel(self):
        from an_print import Panel

        def funktion(px):
            return px

        with self.assertRaisesRegex(ValueError, "saknar panel_schema"):
            Panel(funktion)

    def test_ny_panel_arver_senaste_varden_for_samma_funktion(self):
        import an_print.calcblock as calcblock_module
        from an_print import Panel

        Panel._LAST_VALUES.clear()

        def funktion(px):
            return {
                "metodbeskrivning": {"title": "MB", "items": []},
                "indata": {"title": "ID", "items": []},
                "delresultat": {"title": "DR", "items": []},
                "slutresultat": {"title": "SR", "items": []},
                "ekvationer": {"title": "EKV", "items": []},
            }

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        class FakeCalcBlock:
            def __init__(self, details):
                self.details = details

            def MB(self, **kwargs):
                pass

            def ID(self, **kwargs):
                pass

            def DR(self, **kwargs):
                pass

            def EKV(self, **kwargs):
                pass

            def SR(self, **kwargs):
                pass

        original = calcblock_module.CalcBlock
        calcblock_module.CalcBlock = FakeCalcBlock
        try:
            panel = Panel(funktion)
            panel._field_widgets["a"].value = 9.0
            panel.calculate()

            panel2 = Panel(funktion)
        finally:
            calcblock_module.CalcBlock = original
            Panel._LAST_VALUES.clear()
            Panel._LAST_BY_FUNCTION.clear()

        self.assertEqual(panel2._field_widgets["a"].value, 9.0)

    def test_key_separerar_state_for_samma_funktion(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        panel_a = Panel(funktion, key="fall_a")
        panel_a._field_widgets["a"].set_value(10.0)
        panel_b = Panel(funktion, key="fall_b")
        panel_b._field_widgets["a"].set_value(20.0)
        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()

        self.assertEqual(Panel(funktion, key="fall_a")._field_widgets["a"].value, 10.0)
        self.assertEqual(Panel(funktion, key="fall_b")._field_widgets["a"].value, 20.0)

    def test_ny_key_startar_fran_senaste_panel_for_samma_funktion(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        panel_a = Panel(funktion, key="fall_a")
        panel_a._field_widgets["a"].set_value(10.0)

        panel_b = Panel(funktion, key="fall_b")

        self.assertEqual(panel_b._field_widgets["a"].value, 10.0)

    def test_befintlig_key_vinner_over_senaste_panel_for_samma_funktion(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        panel_a = Panel(funktion, key="fall_a")
        panel_a._field_widgets["a"].set_value(10.0)
        panel_b = Panel(funktion, key="fall_b")
        panel_b._field_widgets["a"].set_value(20.0)

        panel_a_again = Panel(funktion, key="fall_a")

        self.assertEqual(panel_a_again._field_widgets["a"].value, 10.0)

    def test_ny_key_startar_fran_senaste_panel_efter_kernel_restart(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        panel_a = Panel(funktion, key="fall_a")
        panel_a._field_widgets["a"].set_value(10.0)
        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()

        panel_b = Panel(funktion, key="fall_b")

        self.assertEqual(panel_b._field_widgets["a"].value, 10.0)

    def test_utan_key_ar_bakatkompatibelt_och_deler_state_per_funktion(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        panel = Panel(funktion)
        panel._field_widgets["a"].set_value(12.0)
        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()

        self.assertEqual(Panel(funktion)._field_widgets["a"].value, 12.0)

    def test_configure_state_file_styr_filnamn(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        Panel.configure_state_file("projekt.panel_state.json")
        panel = Panel(funktion)
        panel._field_widgets["a"].set_value(13.0)

        self.assertTrue((pathlib.Path.cwd() / "projekt.panel_state.json").exists())
        self.assertFalse((pathlib.Path.cwd() / ".an_print_panel_state.json").exists())

        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()
        self.assertEqual(Panel(funktion)._field_widgets["a"].value, 13.0)

    def test_state_file_i_panel_gar_fore_global_konfiguration(self):
        from an_print import Panel

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        Panel.configure_state_file("global.panel_state.json")
        panel = Panel(funktion, state_file="lokal.panel_state.json")
        panel._field_widgets["a"].set_value(14.0)

        self.assertTrue((pathlib.Path.cwd() / "lokal.panel_state.json").exists())
        self.assertFalse((pathlib.Path.cwd() / "global.panel_state.json").exists())

        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()
        self.assertEqual(
            Panel(funktion, state_file="lokal.panel_state.json")._field_widgets["a"].value,
            14.0,
        )

    def test_faltandring_sparas_till_disk_utan_berakning(self):
        from an_print import Panel

        Panel._LAST_VALUES.clear()
        Panel._LAST_BY_FUNCTION.clear()

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        panel = Panel(funktion)
        panel._field_widgets["a"].set_value(11.0)
        Panel._LAST_VALUES.clear()

        panel2 = Panel(funktion)

        self.assertEqual(panel2._field_widgets["a"].value, 11.0)

    def test_redovisningsinstallningar_sparas_till_disk(self):
        from an_print import Panel

        Panel._LAST_VALUES.clear()

        def funktion(px):
            return px

        funktion.panel_schema = {
            "title": "Test",
            "px": ["a"],
            "fields": [{"name": "a", "type": "float", "default": 2.0}],
        }

        panel = Panel(funktion)
        panel._block_widgets["DR"]["rader"].set_value(12)
        panel._block_widgets["EKV"]["visa"].set_value(True)
        panel._block_widgets["SR"]["etikett"].set_value(False)
        Panel._LAST_VALUES.clear()

        panel2 = Panel(funktion)

        self.assertEqual(panel2._block_widgets["DR"]["rader"].value, 12)
        self.assertEqual(panel2._block_widgets["EKV"]["visa"].value, True)
        self.assertEqual(panel2._block_widgets["SR"]["etikett"].value, False)

    def test_ny_panel_arver_senaste_tabellrader(self):
        import an_print.calcblock as calcblock_module
        from an_calcs.geo import sattning
        from an_print import Panel

        Panel._LAST_VALUES.clear()

        class FakeCalcBlock:
            def __init__(self, details):
                self.details = details

            def MB(self, **kwargs):
                pass

            def ID(self, **kwargs):
                pass

            def DR(self, **kwargs):
                pass

            def EKV(self, **kwargs):
                pass

            def SR(self, **kwargs):
                pass

        original = calcblock_module.CalcBlock
        calcblock_module.CalcBlock = FakeCalcBlock
        try:
            panel = Panel(sattning)
            table = panel._table_widgets["jordlager"]
            table.rows[0]["controls"]["dz"].value = 2.5
            panel.calculate()

            panel2 = Panel(sattning)
        finally:
            calcblock_module.CalcBlock = original
            Panel._LAST_VALUES.clear()
            Panel._LAST_BY_FUNCTION.clear()

        self.assertEqual(panel2._table_widgets["jordlager"].rows[0]["controls"]["dz"].value, 2.5)


if __name__ == "__main__":
    unittest.main()
