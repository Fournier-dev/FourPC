import json
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from core.models import Build
from core.report import (
    BuildNotReadyError, ExportFormat, export_report, fit, format_brl,
    format_price_diff, render_report, render_summary, to_dict,
)
from tests.helpers import make_complete_build, make_cpu, make_motherboard

GENERATED_AT = datetime(2026, 10, 4, 14, 30, 0)


class FormatBrlTest(unittest.TestCase):
    def test_formats_brazilian_currency(self) -> None:
        self.assertEqual(format_brl(Decimal("0")), "R$ 0,00")
        self.assertEqual(format_brl(Decimal("699.9")), "R$ 699,90")
        self.assertEqual(format_brl(Decimal("1299.90")), "R$ 1.299,90")
        self.assertEqual(format_brl(Decimal("1234567.89")), "R$ 1.234.567,89")


class FormatPriceDiffTest(unittest.TestCase):
    def test_positive_diff_has_plus_sign(self) -> None:
        self.assertEqual(format_price_diff(Decimal("300")), "+R$ 300,00")

    def test_negative_diff_has_minus_sign(self) -> None:
        self.assertEqual(
            format_price_diff(Decimal("-1150.5")), "-R$ 1.150,50"
        )

    def test_zero_diff(self) -> None:
        self.assertEqual(format_price_diff(Decimal("0")), "mesmo preço")


class FitTest(unittest.TestCase):
    def test_keeps_short_text(self) -> None:
        self.assertEqual(fit("abc", 5), "abc")

    def test_truncates_long_text_with_ellipsis(self) -> None:
        self.assertEqual(fit("abcdefgh", 5), "abcd…")


class RenderTest(unittest.TestCase):
    def test_summary_lists_components_and_total(self) -> None:
        summary = render_summary(make_complete_build())

        self.assertIn("CPU Teste", summary)
        self.assertIn("R$ 5.400,00", summary)
        self.assertIn("216 W", summary)
        self.assertNotIn("[ERRO]", summary)

    def test_summary_of_incomplete_build_shows_pending_items(self) -> None:
        summary = render_summary(Build().with_component(make_cpu()))

        self.assertIn("(não selecionado)", summary)
        self.assertIn("[ -- ]", summary)

    def test_summary_shows_incompatibilities(self) -> None:
        build = (
            Build()
            .with_component(make_cpu("AM4"))
            .with_component(make_motherboard("AM5"))
        )

        self.assertIn("[ERRO] Soquete CPU x Placa-Mãe", render_summary(build))

    def test_report_has_header_and_date(self) -> None:
        report = render_report(make_complete_build(), GENERATED_AT)

        self.assertIn("FourPC", report)
        self.assertIn("04/10/2026 às 14:30", report)
        self.assertIn("Pronta para compra", report)


class ToDictTest(unittest.TestCase):
    def test_serializes_build_with_exact_prices(self) -> None:
        data = to_dict(make_complete_build(), GENERATED_AT)

        self.assertEqual(data["total_price"], "5400.00")
        self.assertEqual(data["total_price_formatted"], "R$ 5.400,00")
        self.assertEqual(data["generated_at"], "2026-10-04T14:30:00")
        self.assertEqual(len(data["components"]), 7)
        self.assertEqual(data["components"][0]["price"], "1000.00")
        self.assertEqual(data["components"][1]["ram_type"], "DDR5")
        self.assertEqual(data["power"]["required_psu_watts"], 216)

    def test_result_is_json_serializable(self) -> None:
        json.dumps(to_dict(make_complete_build(), GENERATED_AT))


class ExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name) / "reports"

    def test_exports_txt(self) -> None:
        path = export_report(
            make_complete_build(), self.directory, ExportFormat.TXT,
            GENERATED_AT,
        )

        self.assertEqual(path.name, "orcamento_20261004_143000.txt")
        self.assertIn("R$ 5.400,00", path.read_text(encoding="utf-8"))

    def test_exports_json(self) -> None:
        path = export_report(
            make_complete_build(), self.directory, ExportFormat.JSON,
            GENERATED_AT,
        )

        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(path.suffix, ".json")
        self.assertEqual(data["total_price"], "5400.00")

    def test_refuses_incomplete_build(self) -> None:
        with self.assertRaises(BuildNotReadyError):
            export_report(Build(), self.directory, ExportFormat.TXT)
        self.assertFalse(self.directory.exists())

    def test_refuses_incompatible_build(self) -> None:
        build = make_complete_build().with_component(make_cpu("LGA1700"))

        with self.assertRaises(BuildNotReadyError):
            export_report(build, self.directory, ExportFormat.JSON)


if __name__ == "__main__":
    unittest.main()
