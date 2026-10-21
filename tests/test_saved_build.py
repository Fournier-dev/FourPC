import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

from core.catalog import Catalog
from core.models import Category
from core.report import to_dict
from core.saved_build import SavedBuildError, build_from_dict, load_build
from tests.helpers import make_complete_build, make_cpu


def catalog_of_complete_build() -> Catalog:
    build = make_complete_build()
    return Catalog({c.category: [c] for c in build.selected()})


class BuildFromDictTest(unittest.TestCase):
    def test_round_trip_with_exported_dict(self) -> None:
        build = make_complete_build()
        # passo pelo json pra ficar igual ao arquivo de verdade
        data = json.loads(json.dumps(to_dict(build, datetime(2026, 1, 1))))

        loaded = build_from_dict(data, catalog_of_complete_build())

        self.assertEqual(loaded.build, build)
        self.assertEqual(loaded.missing_ids, [])

    def test_unknown_ids_are_reported(self) -> None:
        data = {"components": [
            {"category": "cpu", "id": "cpu-test"},
            {"category": "ram", "id": "ram-antiga"},
        ]}

        loaded = build_from_dict(data, catalog_of_complete_build())

        self.assertIsNotNone(loaded.build.get(Category.CPU))
        self.assertIsNone(loaded.build.get(Category.RAM))
        self.assertEqual(loaded.missing_ids, ["ram-antiga"])

    def test_id_from_other_category_is_reported(self) -> None:
        data = {"components": [{"category": "gpu", "id": "cpu-test"}]}

        loaded = build_from_dict(data, catalog_of_complete_build())

        self.assertEqual(loaded.build.selected(), [])
        self.assertEqual(loaded.missing_ids, ["cpu-test"])

    def test_uses_current_catalog_price(self) -> None:
        catalog = Catalog({
            Category.CPU: [make_cpu(price="750.00")],
        })
        data = {"components": [
            {"category": "cpu", "id": "cpu-test", "price": "1000.00"},
        ]}

        loaded = build_from_dict(data, catalog)

        self.assertEqual(loaded.build.total_price, 750)

    def test_invalid_structure_raises_error(self) -> None:
        catalog = catalog_of_complete_build()
        invalid: list[Any] = [
            [], {}, {"components": "x"}, {"components": [{}]},
        ]
        for data in invalid:
            with self.subTest(data=data):
                with self.assertRaises(SavedBuildError):
                    build_from_dict(data, catalog)


class LoadBuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)

    def test_missing_file_raises_error(self) -> None:
        with self.assertRaises(SavedBuildError):
            load_build(self.directory / "nada.json",
                       catalog_of_complete_build())

    def test_invalid_json_raises_error(self) -> None:
        path = self.directory / "quebrado.json"
        path.write_text("{ isso não é json", encoding="utf-8")

        with self.assertRaises(SavedBuildError):
            load_build(path, catalog_of_complete_build())

    def test_loads_file(self) -> None:
        path = self.directory / "orcamento.json"
        data = to_dict(make_complete_build(), datetime(2026, 1, 1))
        path.write_text(json.dumps(data), encoding="utf-8")

        loaded = load_build(path, catalog_of_complete_build())

        self.assertTrue(loaded.build.is_complete)


if __name__ == "__main__":
    unittest.main()
