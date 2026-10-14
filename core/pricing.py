from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PIX_DISCOUNT = Decimal("0.10")
MAX_INSTALLMENTS = 10

CENTS = Decimal("0.01")


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
