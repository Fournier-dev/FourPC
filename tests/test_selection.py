import unittest

from core.models import Category
from core.selection import (
    EXTRA_STORAGE_GROUP, SelectionError, build_from_ids, conflicting_rules,
    conflicts_by_option,
)
from core.validators import PSU_RULE, SOCKET_RULE
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


class ConflictsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = web_catalog()

    def test_option_that_breaks_a_rule(self) -> None:
        build = build_from_ids(self.catalog, {"cpu": "cpu-am5"})

        rules = conflicting_rules(build, self.catalog.get("mb-am4"))

        self.assertEqual(rules, [SOCKET_RULE])

    def test_compatible_option_has_no_conflict(self) -> None:
        build = build_from_ids(self.catalog, {"cpu": "cpu-am5"})

        self.assertEqual(
            conflicting_rules(build, self.catalog.get("mb-am5")), []
        )

    def test_nothing_conflicts_in_an_empty_build(self) -> None:
        conflicts = conflicts_by_option(build_from_ids(self.catalog, {}),
                                        self.catalog)

        self.assertTrue(all(group == {} for group in conflicts.values()))

    def test_groups_include_the_second_disk(self) -> None:
        conflicts = conflicts_by_option(
            build_from_ids(self.catalog, GOOD_BUILD), self.catalog
        )

        self.assertIn(EXTRA_STORAGE_GROUP, conflicts)
        self.assertEqual(len(conflicts), 8)

    def test_power_conflict(self) -> None:
        # CPU de 65 W + fonte de 650 W: a GPU de 575 W pede 768 W
        build = build_from_ids(
            self.catalog, {"cpu": "cpu-am5", "psu": "psu-650"}
        )

        conflicts = conflicts_by_option(build, self.catalog)

        self.assertEqual(conflicts["gpu"], {"gpu-huge": [PSU_RULE]})


if __name__ == "__main__":
    unittest.main()
