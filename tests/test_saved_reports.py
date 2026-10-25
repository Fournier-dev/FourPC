import json
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from core.report import ExportFormat, export_report
from core.saved_reports import list_saved_reports
from tests.helpers import make_complete_build


class ListSavedReportsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)

    def test_missing_folder_returns_empty_list(self) -> None:
        self.assertEqual(list_saved_reports(self.directory / "nada"), [])

    def test_groups_formats_with_same_date(self) -> None:
        build = make_complete_build()
        generated_at = datetime(2026, 10, 21, 14, 30, 0)
        for fmt in ExportFormat:
            export_report(build, self.directory, fmt, generated_at)

        reports = list_saved_reports(self.directory)

        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertEqual(report.generated_at, generated_at)
        self.assertEqual(report.formats, list(ExportFormat))
        self.assertEqual(report.total, build.total_price)
        self.assertIsNotNone(report.json_path)

    def test_newest_first(self) -> None:
        build = make_complete_build()
        old = datetime(2026, 1, 1, 8, 0, 0)
        new = datetime(2026, 5, 1, 8, 0, 0)
        export_report(build, self.directory, ExportFormat.TXT, old)
        export_report(build, self.directory, ExportFormat.TXT, new)

        reports = list_saved_reports(self.directory)

        self.assertEqual([r.generated_at for r in reports], [new, old])

    def test_report_without_json_has_no_total(self) -> None:
        export_report(
            make_complete_build(), self.directory, ExportFormat.CSV,
            datetime(2026, 1, 1),
        )

        report = list_saved_reports(self.directory)[0]

        self.assertEqual(report.formats, [ExportFormat.CSV])
        self.assertIsNone(report.total)
        self.assertIsNone(report.json_path)

    def test_ignores_other_files(self) -> None:
        (self.directory / "anotacoes.txt").write_text("oi", encoding="utf-8")
        (self.directory / "orcamento_20261399_000000.json").write_text(
            "{}", encoding="utf-8"
        )
        (self.directory / "orcamento_20260101_000000.pdf").write_text(
            "", encoding="utf-8"
        )

        self.assertEqual(list_saved_reports(self.directory), [])

    def test_broken_json_still_listed_without_total(self) -> None:
        path = self.directory / "orcamento_20260101_120000.json"
        path.write_text("{quebrado", encoding="utf-8")

        report = list_saved_reports(self.directory)[0]

        self.assertIsNone(report.total)
        self.assertEqual(report.json_path, path)

    def test_total_read_as_decimal(self) -> None:
        path = self.directory / "orcamento_20260101_120000.json"
        path.write_text(json.dumps({"total_price": "1299.90"}),
                        encoding="utf-8")

        report = list_saved_reports(self.directory)[0]

        self.assertEqual(report.total, Decimal("1299.90"))


if __name__ == "__main__":
    unittest.main()
