import unittest
from typing import Any

try:
    from fastapi.testclient import TestClient
except ImportError:
    raise unittest.SkipTest(
        "FastAPI não instalado (pip install -r requirements-dev.txt)"
    )

from core.models import Category
from tests.web_helpers import GOOD_BUILD, web_catalog
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


class ValidateRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(web_catalog()))

    def validate(
        self, components: dict[str, str], extra: str | None = None
    ) -> Any:
        return self.client.post(
            "/api/montagens/validar",
            json={"components": components, "extra_storage": extra},
        )

    def test_good_build(self) -> None:
        data = self.validate(GOOD_BUILD).json()

        self.assertTrue(data["is_complete"])
        self.assertTrue(data["can_finalize"])
        self.assertEqual(data["missing"], [])
        self.assertEqual(len(data["rules"]), 6)
        self.assertTrue(all(r["status"] == "ok" for r in data["rules"]))
        self.assertIn("Pronta para compra", data["status_message"])

    def test_prices(self) -> None:
        payment = self.validate(GOOD_BUILD).json()["payment"]

        self.assertEqual(payment["total"], "5400.00")
        self.assertEqual(payment["total_formatted"], "R$ 5.400,00")
        self.assertEqual(payment["pix_price"], "4860.00")
        self.assertEqual(payment["installments"], 10)
        self.assertEqual(payment["installment_price"], "540.00")

    def test_power(self) -> None:
        power = self.validate(GOOD_BUILD).json()["power"]

        # 65 W + 115 W = 180 W, com 20% de margem dá 216 W
        self.assertEqual(power["estimated_load_watts"], 180)
        self.assertEqual(power["required_psu_watts"], 216)
        self.assertEqual(power["psu_watts"], 650)
        self.assertEqual(power["psu_headroom_percent"], 72)

    def test_incompatible_build_cannot_be_finalized(self) -> None:
        data = self.validate({**GOOD_BUILD, "cpu": "cpu-intel"}).json()

        failed = [r for r in data["rules"] if r["status"] == "fail"]
        self.assertFalse(data["can_finalize"])
        self.assertEqual(len(failed), 1)
        self.assertIn("LGA1700", failed[0]["message"])
        self.assertEqual(failed[0]["categories"], ["cpu", "motherboard"])
        self.assertTrue(failed[0]["hint"])

    def test_warning_does_not_block(self) -> None:
        data = self.validate({**GOOD_BUILD, "storage": "hd-1"}).json()

        statuses = [r["status"] for r in data["rules"]]
        self.assertIn("warning", statuses)
        self.assertTrue(data["can_finalize"])

    def test_empty_build(self) -> None:
        data = self.validate({}).json()

        self.assertEqual(len(data["missing"]), 7)
        self.assertIsNone(data["power"])
        self.assertTrue(all(r["status"] == "pending" for r in data["rules"]))
        self.assertEqual(data["payment"]["total"], "0.00")

    def test_second_disk(self) -> None:
        data = self.validate(GOOD_BUILD, "hd-1").json()

        labels = [c["category_label"] for c in data["components"]]
        self.assertIn("Armazenamento 2", labels)
        self.assertEqual(data["payment"]["total"], "5700.00")

    def test_invalid_ids_return_422_in_portuguese(self) -> None:
        cases = [
            ({"cpu": "nao-existe"}, None, "não existe"),
            ({"gpu": "cpu-am5"}, None, "não é da categoria"),
            ({"cooler": "cpu-am5"}, None, "Categoria desconhecida"),
            ({"cpu": "cpu-am5"}, "hd-1", "disco principal"),
        ]
        for components, extra, message in cases:
            with self.subTest(message=message):
                response = self.validate(components, extra)

                self.assertEqual(response.status_code, 422)
                self.assertIn(message, response.json()["detail"])


class PresetsRouteTest(unittest.TestCase):
    def test_real_presets_are_valid_builds(self) -> None:
        client = TestClient(create_app())

        presets = client.get("/api/presets").json()

        self.assertEqual(len(presets), 3)
        for preset in presets:
            with self.subTest(preset=preset["name"]):
                self.assertTrue(preset["total_formatted"].startswith("R$"))
                # o formato dos IDs é o mesmo que a validação recebe
                data = client.post(
                    "/api/montagens/validar",
                    json={"components": preset["components"]},
                ).json()
                self.assertTrue(data["can_finalize"])
                self.assertEqual(data["payment"]["total"], preset["total"])

    def test_broken_presets_return_500(self) -> None:
        # os presets de verdade usam peças que não estão no catálogo menor
        client = TestClient(create_app(web_catalog()))

        response = client.get("/api/presets")

        self.assertEqual(response.status_code, 500)
        self.assertIn("montagens prontas", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
