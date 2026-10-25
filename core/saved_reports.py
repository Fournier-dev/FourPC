import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from core.report import ExportFormat

# mesmo padrão de nome que o export_report usa
# Ex.: orcamento_20261021_143000.json
REPORT_NAME = re.compile(r"^orcamento_(\d{8}_\d{6})\.(txt|json|csv)$")


# Um orçamento salvo pode ter até 3 arquivos (TXT, JSON e CSV) com a mesma
# data/hora no nome, então junto todos eles numa coisa só.
@dataclass(frozen=True)
class SavedReport:
    generated_at: datetime
    paths: dict[ExportFormat, Path]
    # o total só dá pra saber quando tem o JSON
    total: Decimal | None = None

    @property
    def formats(self) -> list[ExportFormat]:
        return [fmt for fmt in ExportFormat if fmt in self.paths]

    @property
    def json_path(self) -> Path | None:
        return self.paths.get(ExportFormat.JSON)


# se o JSON estiver corrompido não tem problema, só fica sem o total
def _read_total(path: Path) -> Decimal | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Decimal(str(data["total_price"]))
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError,
            InvalidOperation):
        return None


# lista os orçamentos da pasta, do mais novo pro mais antigo
def list_saved_reports(directory: Path) -> list[SavedReport]:
    if not directory.is_dir():
        return []

    grouped: dict[datetime, dict[ExportFormat, Path]] = {}
    for path in directory.iterdir():
        match = REPORT_NAME.match(path.name)
        if match is None or not path.is_file():
            continue
        try:
            generated_at = datetime.strptime(match[1], "%Y%m%d_%H%M%S")
        except ValueError:
            # nome no formato certo mas com data impossível (mês 13 etc.)
            continue
        grouped.setdefault(generated_at, {})[ExportFormat(match[2])] = path

    reports: list[SavedReport] = []
    for generated_at, paths in grouped.items():
        json_path = paths.get(ExportFormat.JSON)
        total = None if json_path is None else _read_total(json_path)
        reports.append(SavedReport(generated_at, paths, total))
    reports.sort(key=lambda report: report.generated_at, reverse=True)
    return reports
