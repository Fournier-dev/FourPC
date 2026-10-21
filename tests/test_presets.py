import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from core.catalog import Catalog
from core.models import Category
from core.presets import PresetError, load_presets, presets_from_dict
from core.validators import find_issues
from tests.helpers import make_complete_build


def catalog_of_complete_build() -> Catalog:
    build = make_complete_build()
    return Catalog({c.category: [c] for c in build.selected()})


class RealPresetsTest(unittest.TestCase):
    # usa os arquivos de verdade da pasta data/
    def setUp(self) -> None:
        self.presets = load_presets(Catalog.from_json())

    def test_has_the_three_presets(self) -> None:
        names = [preset.name for preset in self.presets]
        self.assertEqual(names, ["Básica", "Intermediária", "Avançada"])

    def test_all_presets_are_complete_and_compatible(self) -> None:
        for preset in self.presets:
            with self.subTest(preset=preset.name):
                self.assertTrue(preset.build.is_complete)
                self.assertEqual(find_issues(preset.build), [])

    def test_presets_go_from_cheapest_to_most_expensive(self) -> None:
        totals = [preset.build.total_price for preset in self.presets]
        self.assertEqual(totals, sorted(totals))


class PresetsFromDictTest(unittest.TestCase):
    def test_builds_preset_from_ids(self) -> None:
        build = make_complete_build()
        data = {"presets": [{
            "name": "Teste",
            "description": "Montagem de teste.",
            "components": {
                c.category.value: c.id for c in build.selected()
            },
        }]}

        presets = presets_from_dict(data, catalog_of_complete_build())

        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0].name, "Teste")
        self.assertEqual(presets[0].description, "Montagem de teste.")
        self.assertEqual(presets[0].build, build)

    def test_invalid_data_raises_error(self) -> None:
        invalid: list[Any] = [
            [],
            {},
            {"presets": "x"},
            {"presets": [{"components": {}}]},
            {"presets": [{"name": "Sem peças"}]},
            {"presets": [{"name": "A", "components": {"cpu": "nao-existe"}}]},
            {"presets": [{"name": "A", "components": {"teclado": "x"}}]},
            # ID que existe, mas é de outra categoria
            {"presets": [{"name": "A", "components": {"gpu": "cpu-test"}}]},
        ]
        catalog = catalog_of_complete_build()
        for data in invalid:
            with self.subTest(data=data):
                with self.assertRaises(PresetError):
                    presets_from_dict(data, catalog)

    def test_preset_can_be_incomplete(self) -> None:
        data = {"presets": [{"name": "Só CPU",
                             "components": {"cpu": "cpu-test"}}]}

        presets = presets_from_dict(data, catalog_of_complete_build())

        self.assertEqual(presets[0].build.missing_categories()[0],
                         Category.MOTHERBOARD)


class LoadPresetsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)

    def test_missing_file_raises_error(self) -> None:
        with self.assertRaises(PresetError):
            load_presets(catalog_of_complete_build(),
                         self.directory / "nada.json")

    def test_invalid_json_raises_error(self) -> None:
        path = self.directory / "presets.json"
        path.write_text("{ quebrado", encoding="utf-8")

        with self.assertRaises(PresetError):
            load_presets(catalog_of_complete_build(), path)

    def test_loads_file(self) -> None:
        path = self.directory / "presets.json"
        path.write_text(json.dumps({"presets": [
            {"name": "Teste", "components": {"cpu": "cpu-test"}},
        ]}), encoding="utf-8")

        presets = load_presets(catalog_of_complete_build(), path)

        self.assertEqual(presets[0].description, "")


if __name__ == "__main__":
    unittest.main()
