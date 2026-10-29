import unittest
from typing import Any

try:
    from fastapi.testclient import TestClient
except ImportError:
    raise unittest.SkipTest(
        "FastAPI não instalado (pip install -r requirements-dev.txt)"
    )

from core.models import Category
from tests.web_helpers import web_catalog
from web.app import create_app


def find_component(data: dict[str, Any], component_id: str) -> Any:
    for category in data["categories"]:
        for component in category["components"]:
            if component["id"] == component_id:
                return component
    raise AssertionError(f"peça {component_id} não veio na resposta")


class CatalogRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(web_catalog()))
        self.data = self.client.get("/api/catalogo").json()

    def test_lists_every_category_in_order(self) -> None:
        categories = [c["category"] for c in self.data["categories"]]

        self.assertEqual(categories, [c.value for c in Category])
        self.assertEqual(self.data["categories"][0]["label"], "Processador")

    def test_component_fields(self) -> None:
        cpu = find_component(self.data, "cpu-am5")

        self.assertEqual(cpu["name"], "CPU Teste")
        self.assertEqual(cpu["category_label"], "Processador")
        self.assertEqual(cpu["price"], "1000.00")
        self.assertEqual(cpu["price_formatted"], "R$ 1.000,00")
        self.assertEqual(cpu["specs"], "AM5 · 65 W")
        self.assertEqual(
            cpu["attributes"], {"socket": "AM5", "tdp_watts": 65}
        )

    def test_enum_and_tuple_attributes_become_text(self) -> None:
        board = find_component(self.data, "mb-am4")
        case = find_component(self.data, "case-itx")

        self.assertEqual(board["attributes"]["ram_type"], "DDR4")
        self.assertEqual(board["attributes"]["form_factor"], "mATX")
        self.assertEqual(
            case["attributes"]["supported_form_factors"], ["ITX"]
        )

    def test_components_come_sorted_by_price(self) -> None:
        motherboards = self.data["categories"][1]["components"]

        self.assertEqual(
            [board["id"] for board in motherboards], ["mb-am4", "mb-am5"]
        )


class RealCatalogTest(unittest.TestCase):
    def test_default_app_uses_the_real_catalog(self) -> None:
        data = TestClient(create_app()).get("/api/catalogo").json()

        total = sum(len(c["components"]) for c in data["categories"])
        self.assertGreater(total, 40)


if __name__ == "__main__":
    unittest.main()
