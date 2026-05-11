import pathlib
import sys
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

    def tearDown(self):
        if self._old_ipywidgets is None:
            sys.modules.pop("ipywidgets", None)
        else:
            sys.modules["ipywidgets"] = self._old_ipywidgets

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

    def test_funktion_utan_schema_ger_tydligt_fel(self):
        from an_print import Panel

        def funktion(px):
            return px

        with self.assertRaisesRegex(ValueError, "saknar panel_schema"):
            Panel(funktion)


if __name__ == "__main__":
    unittest.main()
