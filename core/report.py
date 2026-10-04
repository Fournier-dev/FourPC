"""Geração do orçamento: resumo em texto, versão JSON e exportação."""

import json
import textwrap
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from core.models import Build, Category, Component
from core.validators import (
    PSU_SAFETY_MARGIN, RuleResult, Status, check_all, estimated_load_watts,
    find_issues, required_psu_wattage,
)

REPORT_WIDTH = 72
LABEL_WIDTH = 16
PRICE_WIDTH = 16
NAME_WIDTH = REPORT_WIDTH - LABEL_WIDTH - PRICE_WIDTH

THICK_LINE = "=" * REPORT_WIDTH
THIN_LINE = "-" * REPORT_WIDTH

STATUS_TAGS: dict[Status, str] = {
    Status.OK: "[ OK ]",
    Status.FAIL: "[ERRO]",
    Status.PENDING: "[ -- ]",
}

_BRL_SEPARATORS = str.maketrans(",.", ".,")


class ExportFormat(str, Enum):
    TXT = "txt"
    JSON = "json"


class BuildNotReadyError(Exception):
    """A montagem está incompleta ou tem incompatibilidades."""


def format_brl(value: Decimal) -> str:
    """Formata um valor no padrão monetário brasileiro (ex.: R$ 1.299,90).

    Não depende do ``locale`` do sistema, que varia entre máquinas.
    """
    return "R$ " + f"{value:,.2f}".translate(_BRL_SEPARATORS)


def fit(text: str, width: int) -> str:
    """Trunca o texto com reticências caso ele exceda a largura."""
    return text if len(text) <= width else text[: width - 1] + "…"


def format_result(result: RuleResult, indent: str = "  ") -> list[str]:
    """Formata o resultado de uma regra em linhas com quebra automática."""
    tag = STATUS_TAGS[result.status]
    body_indent = indent + " " * (len(tag) + 1)
    lines = [f"{indent}{tag} {result.rule}"]
    lines += textwrap.wrap(
        result.message, REPORT_WIDTH,
        initial_indent=body_indent, subsequent_indent=body_indent,
    )
    if result.hint:
        lines += textwrap.wrap(
            f"Sugestão: {result.hint}", REPORT_WIDTH,
            initial_indent=body_indent, subsequent_indent=body_indent,
        )
    return lines


def _row(label: str, text: str, price: str = "") -> str:
    return (
        f"{label:<{LABEL_WIDTH}}"
        f"{fit(text, NAME_WIDTH):<{NAME_WIDTH}}"
        f"{price:>{PRICE_WIDTH}}"
    ).rstrip()


def _key_value(label: str, value: str) -> str:
    return f"  {label:<{REPORT_WIDTH - 2 - PRICE_WIDTH}}{value:>{PRICE_WIDTH}}"


def _components_section(build: Build) -> list[str]:
    lines = ["COMPONENTES", THIN_LINE]
    for category in Category:
        component = build.get(category)
        if component is None:
            lines.append(_row(category.label, "(não selecionado)"))
            continue
        lines.append(
            _row(category.label, component.name, format_brl(component.price))
        )
        if component.specs():
            lines.append(_row("", component.specs()))
    lines += [THIN_LINE, _row("TOTAL", "", format_brl(build.total_price))]
    return lines


def _power_section(build: Build) -> list[str]:
    lines = ["ENERGIA", THIN_LINE]
    cpu, gpu, psu = build.cpu, build.gpu, build.psu
    if cpu is None or gpu is None:
        lines.append(
            "  Selecione processador e placa de vídeo para estimar o consumo."
        )
        return lines
    lines += [
        _key_value(
            "Consumo estimado (CPU + GPU)",
            f"{estimated_load_watts(cpu, gpu)} W",
        ),
        _key_value(
            f"Fonte mínima recomendada (+{PSU_SAFETY_MARGIN:.0%})",
            f"{required_psu_wattage(cpu, gpu)} W",
        ),
        _key_value(
            "Fonte selecionada",
            f"{psu.wattage} W" if psu is not None else "-",
        ),
    ]
    return lines


def _compatibility_section(build: Build) -> list[str]:
    lines = ["COMPATIBILIDADE", THIN_LINE]
    for result in check_all(build):
        lines += format_result(result)
    return lines


def status_message(build: Build) -> str:
    """Frase curta que resume se a montagem está pronta para compra."""
    issues = find_issues(build)
    if issues:
        return (
            f"Montagem com {len(issues)} incompatibilidade(s) - "
            "corrija antes de finalizar."
        )
    missing = build.missing_categories()
    if missing:
        names = ", ".join(category.label for category in missing)
        return f"Montagem incompleta. Faltam: {names}."
    return "Montagem completa e compatível. Pronta para compra!"


def render_summary(build: Build) -> str:
    """Resumo detalhado da montagem: peças, preços, energia e regras."""
    sections = [
        _components_section(build),
        _power_section(build),
        _compatibility_section(build),
    ]
    return "\n\n".join("\n".join(section) for section in sections)


def render_report(build: Build, generated_at: datetime) -> str:
    """Relatório completo do orçamento, usado na exportação em TXT."""
    header = [
        THICK_LINE,
        "FourPC - Orçamento de Montagem de PC".center(REPORT_WIDTH).rstrip(),
        THICK_LINE,
        f"Gerado em {generated_at:%d/%m/%Y} às {generated_at:%H:%M}",
    ]
    footer = [
        THICK_LINE,
        f"Status: {status_message(build)}",
        "Preços e consumos são estimativas para fins de simulação.",
        THICK_LINE,
    ]
    return "\n\n".join([
        "\n".join(header),
        render_summary(build),
        "\n".join(footer),
    ])


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    return value


def _component_to_dict(component: Component) -> dict[str, Any]:
    data: dict[str, Any] = {
        "category": component.category.value,
        "category_label": component.category.label,
    }
    data.update(
        (key, _json_value(value)) for key, value in asdict(component).items()
    )
    return data


def to_dict(build: Build, generated_at: datetime) -> dict[str, Any]:
    """Representação serializável do orçamento, usada na exportação JSON.

    Valores monetários são gravados como texto para preservar a
    precisão decimal (ex.: "1299.90").
    """
    total = build.total_price.quantize(Decimal("0.01"))
    power: dict[str, int] | None = None
    if build.cpu is not None and build.gpu is not None:
        power = {
            "estimated_load_watts": estimated_load_watts(build.cpu, build.gpu),
            "required_psu_watts": required_psu_wattage(build.cpu, build.gpu),
        }
        if build.psu is not None:
            power["psu_watts"] = build.psu.wattage
    return {
        "project": "FourPC",
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "components": [_component_to_dict(c) for c in build.selected()],
        "power": power,
        "compatibility": [
            {
                "rule": result.rule,
                "status": result.status.value,
                "message": result.message,
            }
            for result in check_all(build)
        ],
        "total_price": str(total),
        "total_price_formatted": format_brl(total),
    }


def export_report(
    build: Build,
    directory: Path,
    fmt: ExportFormat,
    generated_at: datetime | None = None,
) -> Path:
    """Grava o orçamento em ``directory`` e retorna o caminho do arquivo.

    Só permite exportar montagens completas e sem incompatibilidades.
    """
    if not build.is_complete or find_issues(build):
        raise BuildNotReadyError(status_message(build))

    generated_at = generated_at or datetime.now()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"orcamento_{generated_at:%Y%m%d_%H%M%S}.{fmt.value}"

    if fmt is ExportFormat.TXT:
        content = render_report(build, generated_at)
    else:
        content = json.dumps(
            to_dict(build, generated_at), ensure_ascii=False, indent=2
        )
    path.write_text(content + "\n", encoding="utf-8")
    return path
