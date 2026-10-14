import unittest
from decimal import Decimal

from core.pricing import payment_options, round_cents


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


if __name__ == "__main__":
    unittest.main()
