import unittest

from core.models import Category
from core.selection import SelectionError, build_from_ids
from tests.web_helpers import GOOD_BUILD, web_catalog


class BuildFromIdsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = web_catalog()

    def test_builds_complete_build(self) -> None:
        build = build_from_ids(self.catalog, GOOD_BUILD)

        self.assertTrue(build.is_complete)
        self.assertEqual(build.get(Category.CPU), self.catalog.get("cpu-am5"))

    def test_empty_selection_gives_empty_build(self) -> None:
        self.assertEqual(build_from_ids(self.catalog, {}).selected(), [])

    def test_adds_second_disk(self) -> None:
        build = build_from_ids(self.catalog, GOOD_BUILD, "hd-1")

        self.assertEqual(build.extra_storage, self.catalog.get("hd-1"))

    def test_unknown_id(self) -> None:
        with self.assertRaisesRegex(SelectionError, "não existe"):
            build_from_ids(self.catalog, {"cpu": "cpu-que-nao-existe"})

    def test_unknown_category(self) -> None:
        with self.assertRaisesRegex(SelectionError, "Categoria"):
            build_from_ids(self.catalog, {"cooler": "cpu-am5"})

    def test_id_from_another_category(self) -> None:
        with self.assertRaisesRegex(SelectionError, "Placa de Vídeo"):
            build_from_ids(self.catalog, {"gpu": "cpu-am5"})

    def test_second_disk_must_be_storage(self) -> None:
        with self.assertRaisesRegex(SelectionError, "armazenamento"):
            build_from_ids(self.catalog, GOOD_BUILD, "cpu-am5")

    def test_second_disk_needs_main_disk(self) -> None:
        with self.assertRaisesRegex(SelectionError, "disco principal"):
            build_from_ids(self.catalog, {"cpu": "cpu-am5"}, "hd-1")


if __name__ == "__main__":
    unittest.main()
