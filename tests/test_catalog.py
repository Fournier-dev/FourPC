import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.catalog import Catalog, CatalogError
from core.models import CPU, RAM, Category, Motherboard, RamType
from tests.helpers import make_cpu


def minimal_catalog_data() -> dict[str, Any]:
    return {
        "cpu": [{"id": "c1", "name": "CPU", "socket": "AM5",
                 "tdp_watts": 65, "price": 1000.00}],
        "motherboard": [{"id": "m1", "name": "Placa", "socket": "AM5",
                         "ram_type": "DDR5", "price": 800.00}],
        "ram": [{"id": "r1", "name": "RAM", "ram_type": "DDR5",
                 "capacity_gb": 16, "price": 400.00}],
        "gpu": [{"id": "g1", "name": "GPU", "power_watts": 115,
                 "price": 2000.00}],
        "psu": [{"id": "p1", "name": "Fonte", "wattage": 650,
                 "price": 400.00}],
        "storage": [{"id": "s1", "name": "SSD", "kind": "SSD NVMe",
                     "capacity_gb": 1000, "price": 500.00}],
        "case": [{"id": "k1", "name": "Gabinete", "price": 300.00}],
    }


class CatalogFileTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "catalog.json"

    def write_catalog(self, data: Any) -> Path:
        self.path.write_text(json.dumps(data), encoding="utf-8")
        return self.path


class LoadCatalogTest(CatalogFileTestCase):
    def test_loads_typed_components(self) -> None:
        catalog = Catalog.from_json(self.write_catalog(minimal_catalog_data()))

        cpu = catalog.get("c1")
        board = catalog.get("m1")

        self.assertIsInstance(cpu, CPU)
        self.assertIsInstance(board, Motherboard)
        assert isinstance(board, Motherboard)
        self.assertIs(board.ram_type, RamType.DDR5)

    def test_prices_are_parsed_as_exact_decimals(self) -> None:
        data = minimal_catalog_data()
        data["cpu"][0]["price"] = 699.90
        catalog = Catalog.from_json(self.write_catalog(data))

        self.assertEqual(catalog.get("c1").price, Decimal("699.90"))

    def test_missing_file_raises_catalog_error(self) -> None:
        with self.assertRaises(CatalogError):
            Catalog.from_json(self.path)

    def test_invalid_json_raises_catalog_error(self) -> None:
        self.path.write_text("{ isto não é json", encoding="utf-8")

        with self.assertRaises(CatalogError):
            Catalog.from_json(self.path)

    def test_missing_category_raises_catalog_error(self) -> None:
        data = minimal_catalog_data()
        del data["gpu"]

        with self.assertRaisesRegex(CatalogError, "gpu"):
            Catalog.from_json(self.write_catalog(data))

    def test_missing_field_is_reported_by_name(self) -> None:
        data = minimal_catalog_data()
        del data["cpu"][0]["socket"]

        with self.assertRaisesRegex(CatalogError, "socket"):
            Catalog.from_json(self.write_catalog(data))

    def test_unknown_ram_type_raises_catalog_error(self) -> None:
        data = minimal_catalog_data()
        data["ram"][0]["ram_type"] = "DDR3"

        with self.assertRaisesRegex(CatalogError, "r1"):
            Catalog.from_json(self.write_catalog(data))

    def test_duplicate_ids_are_rejected(self) -> None:
        data = minimal_catalog_data()
        data["case"][0]["id"] = "c1"

        with self.assertRaisesRegex(CatalogError, "duplicado"):
            Catalog.from_json(self.write_catalog(data))


class CatalogQueryTest(unittest.TestCase):
    def test_options_returns_components_of_the_category(self) -> None:
        cpu = make_cpu()
        catalog = Catalog({Category.CPU: [cpu]})

        self.assertEqual(catalog.options(Category.CPU), [cpu])
        self.assertEqual(catalog.options(Category.GPU), [])

    def test_get_unknown_id_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            Catalog({}).get("nao-existe")


class DefaultCatalogTest(unittest.TestCase):
    """Garante a integridade do catálogo distribuído em data/catalog.json."""

    catalog: Catalog

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = Catalog.from_json()

    def test_every_category_has_options(self) -> None:
        for category in Category:
            self.assertTrue(self.catalog.options(category), category.value)

    def test_every_cpu_has_a_compatible_motherboard(self) -> None:
        boards = self.catalog.options(Category.MOTHERBOARD)
        board_sockets = {
            board.socket for board in boards
            if isinstance(board, Motherboard)
        }
        for cpu in self.catalog.options(Category.CPU):
            assert isinstance(cpu, CPU)
            self.assertIn(cpu.socket, board_sockets, cpu.name)

    def test_every_motherboard_has_compatible_memory(self) -> None:
        ram_types = {
            ram.ram_type for ram in self.catalog.options(Category.RAM)
            if isinstance(ram, RAM)
        }
        for board in self.catalog.options(Category.MOTHERBOARD):
            assert isinstance(board, Motherboard)
            self.assertIn(board.ram_type, ram_types, board.name)


if __name__ == "__main__":
    unittest.main()
