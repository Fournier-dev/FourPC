import json
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from core.models import Build
from core.report import (
    BuildNotReadyError, ExportFormat, budget_warning, export_report, fit,
    format_brl, format_price_diff, render_report, render_summary,
    status_message, to_dict,
)
from tests.helpers import (
    make_complete_build, make_cpu, make_gpu, make_motherboard, make_ram,
    make_storage,
)

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

    def test_summary_shows_psu_headroom(self) -> None:
        # consumo de 180 W numa fonte de 650 W: sobram 72%
        summary = render_summary(make_complete_build())

        self.assertRegex(summary, r"Folga da fonte\s+72%")

    def test_summary_without_psu_has_no_headroom(self) -> None:
        build = Build().with_component(make_cpu()).with_component(make_gpu())

        self.assertNotIn("Folga da fonte", render_summary(build))

    def test_summary_shows_payment_options(self) -> None:
        summary = render_summary(make_complete_build())

        self.assertRegex(summary, r"À vista no PIX.*R\$ 4\.860,00")
        self.assertRegex(summary, r"10x sem juros de\s+R\$ 540,00")

    def test_summary_without_budget_has_no_budget_line(self) -> None:
        self.assertNotIn("Orçamento", render_summary(make_complete_build()))

    def test_summary_warns_when_over_budget(self) -> None:
        summary = render_summary(make_complete_build(), Decimal("5000"))

        self.assertRegex(summary, r"Orçamento\s+limite definido\s+R\$ 5\.000")
        self.assertIn(
            "[!] O total passou do orçamento de R$ 5.000,00 em R$ 400,00.",
            summary,
        )

    def test_summary_within_budget_shows_what_is_left(self) -> None:
        summary = render_summary(make_complete_build(), Decimal("5400"))

        self.assertIn("Dentro do orçamento (sobram R$ 0,00)", summary)
        self.assertNotIn("passou do orçamento", summary)

    def test_budget_warning(self) -> None:
        build = make_complete_build()

        self.assertIsNone(budget_warning(build, None))
        self.assertIsNone(budget_warning(build, Decimal("6000")))
        self.assertEqual(
            budget_warning(build, Decimal("5399.99")),
            "O total passou do orçamento de R$ 5.399,99 em R$ 0,01.",
        )

    def test_empty_build_has_no_payment_options(self) -> None:
        self.assertNotIn("PIX", render_summary(Build()))

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

    def test_summary_shows_warning_tag(self) -> None:
        build = make_complete_build().with_component(make_ram(capacity_gb=8))

        summary = render_summary(build)

        self.assertIn("[AVISO] Quantidade de Memória RAM", summary)
        self.assertIn("Sugestão: prefira uma memória", summary)
        self.assertNotIn("[ERRO]", summary)

    def test_summary_warns_about_hard_drive(self) -> None:
        build = make_complete_build().with_component(
            make_storage(kind="HD")
        )

        summary = render_summary(build)

        self.assertIn("[AVISO] Tipo de Armazenamento", summary)
        self.assertIn("Sugestão: prefira um SSD", summary)

    def test_status_message_mentions_warnings(self) -> None:
        build = make_complete_build().with_component(make_ram(capacity_gb=8))

        message = status_message(build)

        self.assertIn("com 1 aviso(s)", message)
        self.assertIn("Pronta para compra", message)

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
        self.assertEqual(data["components"][1]["form_factor"], "ATX")
        self.assertEqual(
            data["components"][6]["supported_form_factors"],
            ["ATX", "mATX", "ITX"],
        )
        self.assertEqual(data["power"]["required_psu_watts"], 216)
        self.assertEqual(data["power"]["psu_headroom_percent"], 72)

    def test_serializes_payment_options(self) -> None:
        payment = to_dict(make_complete_build(), GENERATED_AT)["payment"]

        self.assertEqual(payment["pix_discount_percent"], 10)
        self.assertEqual(payment["pix_price"], "4860.00")
        self.assertEqual(payment["pix_price_formatted"], "R$ 4.860,00")
        self.assertEqual(payment["installments"], 10)
        self.assertEqual(payment["installment_price"], "540.00")
        self.assertEqual(
            payment["installment_price_formatted"], "R$ 540,00"
        )

    def test_power_has_no_headroom_without_psu(self) -> None:
        build = Build().with_component(make_cpu()).with_component(make_gpu())

        power = to_dict(build, GENERATED_AT)["power"]

        self.assertNotIn("psu_headroom_percent", power)

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
        content = path.read_text(encoding="utf-8")
        self.assertIn("R$ 5.400,00", content)
        self.assertIn("À vista no PIX", content)

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

    def test_warning_does_not_block_export(self) -> None:
        build = make_complete_build().with_component(make_ram(capacity_gb=8))

        path = export_report(
            build, self.directory, ExportFormat.JSON, GENERATED_AT
        )

        data = json.loads(path.read_text(encoding="utf-8"))
        statuses = [rule["status"] for rule in data["compatibility"]]
        self.assertIn("warning", statuses)

    def test_refuses_incompatible_build(self) -> None:
        build = make_complete_build().with_component(make_cpu("LGA1700"))

        with self.assertRaises(BuildNotReadyError):
            export_report(build, self.directory, ExportFormat.JSON)


if __name__ == "__main__":
    unittest.main()
