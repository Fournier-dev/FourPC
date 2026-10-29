import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:
    raise unittest.SkipTest(
        "FastAPI não instalado (pip install -r requirements-dev.txt)"
    )

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


if __name__ == "__main__":
    unittest.main()
