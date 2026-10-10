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
    find_issues, psu_headroom_percent, required_psu_wattage,
)

# larguras das colunas do relatório
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


class ExportFormat(str, Enum):
    TXT = "txt"
    JSON = "json"


class BuildNotReadyError(Exception):
    pass


# Fiz a formatação na mão em vez de usar o módulo locale, porque o locale
# depende da configuração de cada computador.
# Ex.: 1299.9 -> "R$ 1.299,90"
def format_brl(value: Decimal) -> str:
    us_format = f"{value:,.2f}"  # 1,299.90
    br_format = us_format.replace(",", "_").replace(".", ",")
    return "R$ " + br_format.replace("_", ".")


# diferença de preço com sinal na frente
# Ex.: 300 -> "+R$ 300,00", -150 -> "-R$ 150,00"
def format_price_diff(diff: Decimal) -> str:
    if diff == 0:
        return "mesmo preço"
    sign = "+" if diff > 0 else "-"
    return sign + format_brl(abs(diff))


# corta o texto se ele não couber na coluna
def fit(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def format_result(result: RuleResult, indent: str = "  ") -> list[str]:
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
    line = (
        f"{label:<{LABEL_WIDTH}}"
        f"{fit(text, NAME_WIDTH):<{NAME_WIDTH}}"
        f"{price:>{PRICE_WIDTH}}"
    )
    return line.rstrip()


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
    lines.append(THIN_LINE)
    lines.append(_row("TOTAL", "", format_brl(build.total_price)))
    return lines


def _power_section(build: Build) -> list[str]:
    lines = ["ENERGIA", THIN_LINE]
    cpu, gpu, psu = build.cpu, build.gpu, build.psu
    if cpu is None or gpu is None:
        lines.append(
            "  Selecione processador e placa de vídeo para estimar o consumo."
        )
        return lines

    load = estimated_load_watts(cpu, gpu)
    required = required_psu_wattage(cpu, gpu)
    margin = f"{PSU_SAFETY_MARGIN:.0%}"
    lines.append(_key_value("Consumo estimado (CPU + GPU)", f"{load} W"))
    lines.append(
        _key_value(f"Fonte mínima recomendada (+{margin})", f"{required} W")
    )
    if psu is not None:
        headroom = psu_headroom_percent(cpu, gpu, psu)
        lines.append(_key_value("Fonte selecionada", f"{psu.wattage} W"))
        lines.append(_key_value("Folga da fonte", f"{headroom}%"))
    else:
        lines.append(_key_value("Fonte selecionada", "-"))
    return lines


def _compatibility_section(build: Build) -> list[str]:
    lines = ["COMPATIBILIDADE", THIN_LINE]
    for result in check_all(build):
        lines += format_result(result)
    return lines


def status_message(build: Build) -> str:
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
    components = "\n".join(_components_section(build))
    power = "\n".join(_power_section(build))
    compatibility = "\n".join(_compatibility_section(build))
    return f"{components}\n\n{power}\n\n{compatibility}"


# relatório completo, é o que vai pro arquivo .txt
def render_report(build: Build, generated_at: datetime) -> str:
    title = "FourPC - Orçamento de Montagem de PC".center(REPORT_WIDTH)
    header = [
        THICK_LINE,
        title.rstrip(),
        THICK_LINE,
        f"Gerado em {generated_at:%d/%m/%Y} às {generated_at:%H:%M}",
    ]
    footer = [
        THICK_LINE,
        f"Status: {status_message(build)}",
        "Preços e consumos são estimativas para fins de simulação.",
        THICK_LINE,
    ]
    return (
        "\n".join(header) + "\n\n"
        + render_summary(build) + "\n\n"
        + "\n".join(footer)
    )


# o json não sabe salvar Decimal nem Enum, então converto antes
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
    for key, value in asdict(component).items():
        data[key] = _json_value(value)
    return data


# os preços vão como texto ("1299.90") pra não perder as casas decimais
def to_dict(build: Build, generated_at: datetime) -> dict[str, Any]:
    total = build.total_price.quantize(Decimal("0.01"))

    power: dict[str, int] | None = None
    if build.cpu is not None and build.gpu is not None:
        power = {
            "estimated_load_watts": estimated_load_watts(build.cpu, build.gpu),
            "required_psu_watts": required_psu_wattage(build.cpu, build.gpu),
        }
        if build.psu is not None:
            power["psu_watts"] = build.psu.wattage
            power["psu_headroom_percent"] = psu_headroom_percent(
                build.cpu, build.gpu, build.psu
            )

    compatibility: list[dict[str, str]] = []
    for result in check_all(build):
        compatibility.append({
            "rule": result.rule,
            "status": result.status.value,
            "message": result.message,
        })

    return {
        "project": "FourPC",
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "components": [_component_to_dict(c) for c in build.selected()],
        "power": power,
        "compatibility": compatibility,
        "total_price": str(total),
        "total_price_formatted": format_brl(total),
    }


def export_report(
    build: Build,
    directory: Path,
    fmt: ExportFormat,
    generated_at: datetime | None = None,
) -> Path:
    # não deixa exportar montagem incompleta ou com incompatibilidade
    if not build.is_complete or find_issues(build):
        raise BuildNotReadyError(status_message(build))

    if generated_at is None:
        generated_at = datetime.now()
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
