import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "an-print" / "src"))

from an_print.calcblock import CalcBlock


class TestCalcBlock(unittest.TestCase):
    def test_valbar_potensform_med_decimalstyrning(self):
        cb = CalcBlock({})
        item = {"namn": "k", "value": 81945.514, "unit": "kN/m^2/m", "format": "scientific", "decimals": 2}
        self.assertTrue(cb._format_value(item).startswith(r"8.19 \cdot 10^{4}"))
        self.assertTrue(cb._format_value_html(item).startswith("8.19 &middot; 10<sup>4</sup>"))
        self.assertTrue(cb._format_value(item, {"k": 3}).startswith(r"8.195 \cdot 10^{4}"))
        self.assertTrue(cb._format_value_html(item, {"k": 3}).startswith("8.195 &middot; 10<sup>4</sup>"))
        # Vanlig decimalform för poster utan uttryckligt formatval.
        del item["format"]
        self.assertTrue(cb._format_value(item).startswith("81945.51"))
        self.assertTrue(cb._format_value_html(item).startswith("81945.51"))

    def test_potensform_normaliseras_vid_avrundning(self):
        cb = CalcBlock({})
        for value, mantissa, exponent in [(81995.514, "8.20", 4), (99999, "1.00", 5), (0.00099999, "1.00", -3), (-99999, "-1.00", 5)]:
            with self.subTest(value=value):
                self.assertEqual(cb._format_scientific(value, 2), mantissa + r" \cdot 10^{" + str(exponent) + "}")
                self.assertEqual(cb._format_scientific_html(value, 2), f"{mantissa} &middot; 10<sup>{exponent}</sup>")
        self.assertEqual(cb._format_scientific(0, 2), "0")
        self.assertEqual(cb._format_scientific_html(0, 2), "0")
        # Tidigare automatisk potensform för tröghetsmoment behålls.
        self.assertTrue(cb._format_value({"value": 1234567, "unit": "mm^4"}).startswith(r"1.235 \cdot 10^{6}"))

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
