import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:
    raise unittest.SkipTest(
        "FastAPI não instalado (pip install -r requirements-dev.txt)"
    )

from core.models import Build
from core.validators import RULES
from tests.web_helpers import web_catalog
from web.app import create_app


class LayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(web_catalog()))

    def test_css_is_served(self) -> None:
        response = self.client.get("/static/css/style.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.headers["content-type"])
        # a cor de destaque do tema
        self.assertIn("#a855f7", response.text)

    def test_favicon_is_served(self) -> None:
        response = self.client.get("/static/img/favicon.svg")

        self.assertEqual(response.status_code, 200)

    def test_favicon_ico_points_to_the_svg(self) -> None:
        response = self.client.get("/favicon.ico", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(
            response.headers["location"], "/static/img/favicon.svg"
        )

    def test_page_not_found_uses_the_site_layout(self) -> None:
        response = self.client.get("/pagina-que-nao-existe")

        self.assertEqual(response.status_code, 404)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Página não encontrada", response.text)
        self.assertIn('lang="pt-BR"', response.text)
        self.assertIn("/static/css/style.css", response.text)
        self.assertIn('href="/simulador"', response.text)

    def test_api_not_found_is_json(self) -> None:
        response = self.client.get("/api/rota-que-nao-existe")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Rota não encontrada."})

    def test_other_errors_keep_their_message(self) -> None:
        response = self.client.post(
            "/api/montagens/validar", json={"components": {"cpu": "x"}}
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("não existe", response.json()["detail"])


class HomePageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(web_catalog()))
        self.response = self.client.get("/")

    def test_home_page(self) -> None:
        self.assertEqual(self.response.status_code, 200)
        self.assertIn("text/html", self.response.headers["content-type"])
        self.assertIn("Montar meu PC", self.response.text)
        self.assertIn('href="/simulador"', self.response.text)
        self.assertIn('href="/docs"', self.response.text)

    def test_menu_marks_the_current_page(self) -> None:
        self.assertIn('href="/" aria-current="page"', self.response.text)

    def test_shows_every_rule_from_core(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.__name__):
                name = rule(Build()).rule
                self.assertIn(name, self.response.text)

    def test_numbers_come_from_the_catalog(self) -> None:
        # o catálogo dos testes tem 14 peças e são 6 regras
        self.assertIn("<strong>14</strong>", self.response.text)
        self.assertIn("<strong>6</strong>", self.response.text)


class SimulatorPageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(web_catalog()))

    def test_simulator_page(self) -> None:
        response = self.client.get("/simulador")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Monte seu PC", response.text)
        self.assertIn('src="/static/js/simulador.js"', response.text)
        self.assertIn('id="resumo-total"', response.text)
        self.assertIn('href="/simulador" aria-current="page"', response.text)

    def test_script_is_served_and_uses_the_api(self) -> None:
        response = self.client.get("/static/js/simulador.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.headers["content-type"])
        self.assertIn("/api/catalogo", response.text)
        self.assertIn("/api/montagens/validar", response.text)
        self.assertIn("/api/montagens/conflitos", response.text)

    def test_simulator_has_the_panels(self) -> None:
        response = self.client.get("/simulador")

        for panel in ("painel-pagamento", "painel-energia", "painel-regras"):
            with self.subTest(panel=panel):
                self.assertIn(f'id="{panel}"', response.text)


if __name__ == "__main__":
    unittest.main()
