import unittest
from dataclasses import fields
from decimal import Decimal

from core.models import (
    EXTRA_STORAGE_LABEL, Build, Category, FormFactor, format_capacity,
)
from tests.helpers import (
    make_case, make_complete_build, make_cpu, make_gpu, make_motherboard,
    make_storage,
)


class CategoryTest(unittest.TestCase):
    def test_every_category_maps_to_a_build_field(self) -> None:
        build_fields = {field.name for field in fields(Build)}
        category_keys = {category.value for category in Category}
        # o segundo disco é o único campo que não é uma categoria
        self.assertEqual(build_fields, category_keys | {"extra_storage"})

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

    def test_motherboard_specs_include_form_factor(self) -> None:
        board = make_motherboard(form_factor=FormFactor.MATX)

        self.assertEqual(board.specs(), "AM5 · DDR5 · mATX")

    def test_case_specs_list_supported_form_factors(self) -> None:
        case = make_case(
            supported_form_factors=(FormFactor.MATX, FormFactor.ITX)
        )

        self.assertEqual(case.specs(), "mATX, ITX")

    def test_case_without_form_factors_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_case(supported_form_factors=())

    def test_storage_knows_if_it_is_a_hard_drive(self) -> None:
        self.assertTrue(make_storage(kind="HD").is_hdd)
        self.assertFalse(make_storage(kind="SSD NVMe").is_hdd)
        self.assertFalse(make_storage(kind="SSD SATA").is_hdd)


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

    def test_without_removes_only_that_category(self) -> None:
        cpu = make_cpu()
        board = make_motherboard()
        build = Build().with_component(cpu).with_component(board)

        new_build = build.without(Category.CPU)

        self.assertIsNone(new_build.cpu)
        self.assertIs(new_build.motherboard, board)
        # a montagem original não muda
        self.assertIs(build.cpu, cpu)
        self.assertEqual(new_build.total_price, board.price)

    def test_without_on_empty_category_keeps_build(self) -> None:
        build = Build().with_component(make_cpu())

        self.assertEqual(build.without(Category.GPU), build)

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


class ExtraStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ssd = make_storage(component_id="ssd-1", price="500.00")
        self.hd = make_storage(
            component_id="hd-1", price="400.00", kind="HD"
        )
        self.build = (
            make_complete_build()
            .with_component(self.ssd)
            .with_extra_storage(self.hd)
        )

    def test_extra_storage_is_optional(self) -> None:
        build = make_complete_build()

        self.assertIsNone(build.extra_storage)
        self.assertTrue(build.is_complete)

    def test_with_extra_storage_keeps_main_disk(self) -> None:
        self.assertIs(self.build.storage, self.ssd)
        self.assertIs(self.build.extra_storage, self.hd)
        self.assertEqual(self.build.storages(), [self.ssd, self.hd])

    def test_extra_disk_comes_right_after_the_main_one(self) -> None:
        labels = [label for label, _ in self.build.labeled_components()]

        index = labels.index(Category.STORAGE.label)
        self.assertEqual(labels[index + 1], EXTRA_STORAGE_LABEL)
        self.assertEqual(len(self.build.selected()), len(Category) + 1)

    def test_total_includes_extra_disk(self) -> None:
        # montagem completa (5.400,00) + 400,00 do HD
        self.assertEqual(self.build.total_price, Decimal("5800.00"))

    def test_removing_main_disk_promotes_extra(self) -> None:
        build = self.build.without(Category.STORAGE)

        self.assertIs(build.storage, self.hd)
        self.assertIsNone(build.extra_storage)

    def test_without_extra_storage(self) -> None:
        build = self.build.without_extra_storage()

        self.assertIs(build.storage, self.ssd)
        self.assertIsNone(build.extra_storage)


if __name__ == "__main__":
    unittest.main()
