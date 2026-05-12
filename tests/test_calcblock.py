import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "an-print" / "src"))

from an_print.calcblock import CalcBlock


class TestCalcBlock(unittest.TestCase):
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
