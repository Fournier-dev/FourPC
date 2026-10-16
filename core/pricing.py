import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

PIX_DISCOUNT = Decimal("0.10")
MAX_INSTALLMENTS = 10

CENTS = Decimal("0.01")

# "5.000" ou "12.500" sem vírgula: os pontos são de milhar
THOUSANDS_ONLY = re.compile(r"\d{1,3}(\.\d{3})+")


# arredonda pros centavos do jeito que a gente aprende na escola
# (0,005 vira 0,01), o padrão do Decimal arredondaria pro par
def round_cents(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PaymentOptions:
    total: Decimal
    pix_price: Decimal
    pix_savings: Decimal
    installments: int
    installment_price: Decimal


def payment_options(total: Decimal) -> PaymentOptions:
    total = round_cents(total)
    pix_price = round_cents(total * (1 - PIX_DISCOUNT))
    return PaymentOptions(
        total=total,
        pix_price=pix_price,
        pix_savings=total - pix_price,
        installments=MAX_INSTALLMENTS,
        installment_price=round_cents(total / MAX_INSTALLMENTS),
    )


# Lê um valor em reais digitado pela pessoa. Aceita "5000", "5000,50",
# "5.000", "5.000,00" e "R$ 5.000,00". Dá ValueError se não for um
# valor maior que zero.
def parse_brl(text: str) -> Decimal:
    cleaned = text.strip().removeprefix("R$").strip()
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif THOUSANDS_ONLY.fullmatch(cleaned):
        cleaned = cleaned.replace(".", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"valor inválido: {text!r}") from None
    # is_finite barra "NaN" e "Infinity", que o Decimal aceita
    if not value.is_finite() or value <= 0:
        raise ValueError(f"o valor precisa ser maior que zero: {text!r}")
    return round_cents(value)


# quanto o total passou do orçamento (zero se ficou dentro)
def budget_excess(total: Decimal, budget: Decimal) -> Decimal:
    return max(total - budget, Decimal("0"))
