import csv
import io
import json
import textwrap
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from core.models import Build, Category, Component
from core.pricing import PIX_DISCOUNT, budget_excess, payment_options
from core.validators import (
    PSU_SAFETY_MARGIN, RuleResult, Status, check_all, estimated_load_watts,
    find_issues, find_warnings, psu_headroom_percent, required_psu_wattage,
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
    Status.WARNING: "[AVISO]",
    Status.PENDING: "[ -- ]",
}


class ExportFormat(str, Enum):
    TXT = "txt"
    JSON = "json"
    CSV = "csv"


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


# aviso que aparece no menu e no resumo quando o total passa do limite
def budget_warning(build: Build, budget: Decimal | None) -> str | None:
    if budget is None:
        return None
    excess = budget_excess(build.total_price, budget)
    if excess == 0:
        return None
    return (
        f"O total passou do orçamento de {format_brl(budget)} "
        f"em {format_brl(excess)}."
    )


def _budget_lines(build: Build, budget: Decimal | None) -> list[str]:
    if budget is None:
        return []
    lines = [_row("Orçamento", "limite definido", format_brl(budget))]
    warning = budget_warning(build, budget)
    if warning is None:
        left = format_brl(budget - build.total_price)
        lines.append(_row("", f"Dentro do orçamento (sobram {left})"))
    else:
        lines += textwrap.wrap(
            f"[!] {warning}", REPORT_WIDTH,
            initial_indent="  ", subsequent_indent="      ",
        )
    return lines


def _components_section(
    build: Build, budget: Decimal | None = None
) -> list[str]:
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
    # só mostra as formas de pagamento quando tem alguma peça escolhida
    if build.total_price > 0:
        payment = payment_options(build.total_price)
        discount = f"{PIX_DISCOUNT:.0%}"
        lines.append(
            _row("À vista no PIX", f"({discount} de desconto)",
                 format_brl(payment.pix_price))
        )
        lines.append(
            _row("Ou parcelado", f"{payment.installments}x sem juros de",
                 format_brl(payment.installment_price))
        )
    lines += _budget_lines(build, budget)
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
    warnings = find_warnings(build)
    if warnings:
        return (
            f"Montagem completa e compatível, com {len(warnings)} aviso(s) "
            "no resumo. Pronta para compra!"
        )
    return "Montagem completa e compatível. Pronta para compra!"


# o orçamento máximo é opcional, só entra no resumo se a pessoa definiu
def render_summary(build: Build, budget: Decimal | None = None) -> str:
    components = "\n".join(_components_section(build, budget))
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
    # os formatos suportados pelo gabinete vêm como tupla
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
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
    payment = payment_options(build.total_price)
    total = payment.total

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
        "payment": {
            "pix_discount_percent": int(PIX_DISCOUNT * 100),
            "pix_price": str(payment.pix_price),
            "pix_price_formatted": format_brl(payment.pix_price),
            "installments": payment.installments,
            "installment_price": str(payment.installment_price),
            "installment_price_formatted": format_brl(
                payment.installment_price
            ),
        },
    }


# número no formato brasileiro sem o "R$", pra planilha entender como valor
# Ex.: 1299.9 -> "1299,90"
def format_csv_number(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",")


# Usei ponto e vírgula como separador porque no Excel em português a vírgula
# já é o separador decimal.
def render_csv(build: Build) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(["Categoria", "Peça", "Especificações", "Preço (R$)"])
    for component in build.selected():
        writer.writerow([
            component.category.label,
            component.name,
            component.specs(),
            format_csv_number(component.price),
        ])
    payment = payment_options(build.total_price)
    discount = f"{PIX_DISCOUNT:.0%}"
    writer.writerow(["Total", "", "", format_csv_number(payment.total)])
    writer.writerow([
        "À vista no PIX", "", f"{discount} de desconto",
        format_csv_number(payment.pix_price),
    ])
    writer.writerow([
        "Parcelado", "", f"{payment.installments}x sem juros de",
        format_csv_number(payment.installment_price),
    ])
    return buffer.getvalue()


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

    if fmt is ExportFormat.CSV:
        # utf-8-sig coloca o BOM no começo, senão o Excel erra os acentos
        path.write_text(render_csv(build), encoding="utf-8-sig")
        return path

    if fmt is ExportFormat.TXT:
        content = render_report(build, generated_at)
    else:
        content = json.dumps(
            to_dict(build, generated_at), ensure_ascii=False, indent=2
        )
    path.write_text(content + "\n", encoding="utf-8")
    return path
