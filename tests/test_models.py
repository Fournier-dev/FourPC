import unittest
from dataclasses import fields
from decimal import Decimal

from core.models import Build, Category, format_capacity
from tests.helpers import (
    make_complete_build, make_cpu, make_gpu, make_motherboard,
)


class CategoryTest(unittest.TestCase):
    def test_every_category_maps_to_a_build_field(self) -> None:
        build_fields = {field.name for field in fields(Build)}
        category_keys = {category.value for category in Category}
        self.assertEqual(build_fields, category_keys)

    def test_every_category_has_a_label(self) -> None:
        for category in Category:
            self.assertTrue(category.label)


class ComponentTest(unittest.TestCase):
    def test_negative_price_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_cpu(price="-1.00")

    def test_specs_summarize_technical_attributes(self) -> None:
        self.assertEqual(make_cpu("AM5", 120).specs(), "AM5 · 120 W")
        self.assertEqual(make_gpu(250).specs(), "250 W")


class FormatCapacityTest(unittest.TestCase):
    def test_formats_gigabytes_and_terabytes(self) -> None:
        self.assertEqual(format_capacity(480), "480 GB")
        self.assertEqual(format_capacity(1000), "1 TB")
        self.assertEqual(format_capacity(1500), "1,5 TB")
        self.assertEqual(format_capacity(10000), "10 TB")


class BuildTest(unittest.TestCase):
    def test_with_component_returns_new_build(self) -> None:
        empty = Build()
        cpu = make_cpu()

        build = empty.with_component(cpu)

        self.assertIs(build.cpu, cpu)
        self.assertIsNone(empty.cpu)

    def test_with_component_replaces_previous_choice(self) -> None:
        first = make_cpu(component_id="cpu-1")
        second = make_cpu(component_id="cpu-2")

        build = Build().with_component(first).with_component(second)

        self.assertIs(build.cpu, second)

    def test_missing_categories_follow_category_order(self) -> None:
        build = Build().with_component(make_motherboard())

        missing = build.missing_categories()

        self.assertNotIn(Category.MOTHERBOARD, missing)
        self.assertEqual(missing[0], Category.CPU)
        self.assertFalse(build.is_complete)

    def test_complete_build(self) -> None:
        build = make_complete_build()

        self.assertTrue(build.is_complete)
        self.assertEqual(len(build.selected()), len(Category))

    def test_total_price_uses_exact_decimal_arithmetic(self) -> None:
        build = (
            Build()
            .with_component(make_cpu(price="0.10"))
            .with_component(make_gpu(price="0.20"))
        )

        self.assertEqual(build.total_price, Decimal("0.30"))

    def test_total_price_of_empty_build_is_zero(self) -> None:
        self.assertEqual(Build().total_price, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
