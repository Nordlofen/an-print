import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "an-print" / "src"))

from an_print.calcblock import CalcBlock


class TestCalcBlock(unittest.TestCase):
    def test_etiketter_med_enhetspotens_ar_saker_latextext(self):
        cb = CalcBlock({"ekvationer": {"title": "Ekvationer", "items": [
            {"latex": r"k = \frac{q}{s_m}", "etikett": "bäddmodul i kN/m^2/m"},
        ]}})
        cb.EKV(etikett=True)
        self.assertIn(r"\text{bäddmodul i kN/m$\hat{}$2/m}", cb.latex_ekv)
        self.assertIn(r"\frac{q}{s_m}", cb.latex_ekv)
        self.assertIn("bäddmodul i kN/m^2/m", cb.html_ekv)
        cb.EKV(etikett=False)
        self.assertNotIn("bäddmodul", cb.latex_ekv)

    def test_escapar_originaltecken_utan_att_escapa_insatta_kommandon(self):
        cb = CalcBlock({})
        self.assertEqual(
            cb._escape_text(r"\{A_B\} & 50% $ # ^ ~ ·"),
            r"$\backslash$\{A\_B$\backslash$\} \& 50\% \$ \# $\hat{}$ $\sim$ $\cdot$",
        )

    def test_enhet_med_potens_och_efterfoljande_division(self):
        cb = CalcBlock({})
        self.assertEqual(cb._format_unit("kN/m^2/m"), r"\tiny{[\mathrm{kN/m}^{2}\mathrm{/m}]} ")
        self.assertEqual(
            cb._format_unit_html("kN/m^2/m"),
            '<span class="anp-data-block__unit">[kN/m<sup>2</sup>/m]</span>',
        )
        # Även själva resultatblocket använder den rättade enheten.
        cb.details = {"slutresultat": {"title": "Slutresultat", "items": [
            {"namn": "k", "latex": "k", "value": 20607.203, "unit": "kN/m^2/m", "etikett": "bäddmodul"},
        ]}}
        cb.SR(etikett=True)
        self.assertIn(r"^{2}\mathrm{/m}", cb.latex_sr)
        self.assertIn("<sup>2</sup>/m", cb.html_sr)

    def test_enkla_och_sammansatta_enheter(self):
        cb = CalcBlock({})
        for unit, latex, html in [
            ("mm", r"\mathrm{mm}", "mm"),
            ("mm^4", r"\mathrm{mm}^{4}", "mm<sup>4</sup>"),
            ("kN*m^2", r"\mathrm{kN*m}^{2}", "kN*m<sup>2</sup>"),
            ("m^2/s^2", r"\mathrm{m}^{2}\mathrm{/s}^{2}", "m<sup>2</sup>/s<sup>2</sup>"),
            ("m^-2", r"\mathrm{m}^{-2}", "m<sup>-2</sup>"),
            ("m^{2}/m", r"\mathrm{m}^{2}\mathrm{/m}", "m<sup>2</sup>/m"),
            ("m^0.5/s", r"\mathrm{m}^{0.5}\mathrm{/s}", "m<sup>0.5</sup>/s"),
        ]:
            with self.subTest(unit=unit):
                self.assertEqual(cb._format_unit(unit), r"\tiny{[" + latex + "]} ")
                self.assertEqual(cb._format_unit_html(unit), '<span class="anp-data-block__unit">[' + html + ']</span>')
        self.assertEqual(cb._format_unit(""), "")
        self.assertEqual(cb._format_unit_html(""), "")

    def test_formaterar_mpa_och_kn_med_tre_signifikanta_siffror(self):
        cb = CalcBlock({})

        self.assertIn("0.246", cb._format_value({"value": 0.246153846, "unit": "MPa"}))
        self.assertIn("2.46", cb._format_value({"value": 2.46153846, "unit": "MPa"}))
        self.assertIn("16.2", cb._format_value({"value": 16.2461538, "unit": "MPa"}))
        self.assertIn("0.400", cb._format_value({"value": 0.4, "unit": "kN"}))
        self.assertIn("3.30", cb._format_value({"value": 3.3, "unit": "kN"}))

        self.assertIn("0.246", cb._format_value_html({"value": 0.246153846, "unit": "MPa"}))
        self.assertIn("0.400", cb._format_value_html({"value": 0.4, "unit": "kN"}))


if __name__ == "__main__":
    unittest.main()
