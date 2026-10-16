import unittest
from decimal import Decimal

from core.pricing import (
    budget_excess, parse_brl, payment_options, round_cents,
)


class RoundCentsTest(unittest.TestCase):
    def test_rounds_half_up(self) -> None:
        self.assertEqual(round_cents(Decimal("0.125")), Decimal("0.13"))
        self.assertEqual(round_cents(Decimal("0.124")), Decimal("0.12"))


class PaymentOptionsTest(unittest.TestCase):
    def test_pix_has_ten_percent_discount(self) -> None:
        payment = payment_options(Decimal("5400"))

        self.assertEqual(payment.total, Decimal("5400.00"))
        self.assertEqual(payment.pix_price, Decimal("4860.00"))
        self.assertEqual(payment.pix_savings, Decimal("540.00"))

    def test_splits_in_ten_installments(self) -> None:
        payment = payment_options(Decimal("10979.30"))

        self.assertEqual(payment.installments, 10)
        self.assertEqual(payment.installment_price, Decimal("1097.93"))

    def test_rounds_to_cents(self) -> None:
        # 999,99 com 10% de desconto dá 899,991
        payment = payment_options(Decimal("999.99"))

        self.assertEqual(payment.pix_price, Decimal("899.99"))
        self.assertEqual(payment.installment_price, Decimal("100.00"))

    def test_zero_total(self) -> None:
        payment = payment_options(Decimal("0"))

        self.assertEqual(payment.pix_price, Decimal("0.00"))
        self.assertEqual(payment.installment_price, Decimal("0.00"))


class ParseBrlTest(unittest.TestCase):
    def test_accepts_common_formats(self) -> None:
        cases = {
            "5000": Decimal("5000.00"),
            "5000,5": Decimal("5000.50"),
            "5.000": Decimal("5000.00"),
            "5.000,00": Decimal("5000.00"),
            "R$ 12.500,90": Decimal("12500.90"),
            "  1500.75 ": Decimal("1500.75"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_brl(text), expected)

    def test_rejects_invalid_values(self) -> None:
        for text in ("", "abc", "0", "-100", "NaN", "Infinity", "1,2,3"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_brl(text)


class BudgetExcessTest(unittest.TestCase):
    def test_returns_amount_over_budget(self) -> None:
        excess = budget_excess(Decimal("5400.00"), Decimal("5000.00"))

        self.assertEqual(excess, Decimal("400.00"))

    def test_zero_when_within_budget(self) -> None:
        self.assertEqual(
            budget_excess(Decimal("4000"), Decimal("5000")), Decimal("0")
        )
        self.assertEqual(
            budget_excess(Decimal("5000"), Decimal("5000")), Decimal("0")
        )


if __name__ == "__main__":
    unittest.main()
