import unittest

# sem o FastAPI instalado (só o programa de terminal), esses testes são
# pulados em vez de quebrar
try:
    from fastapi.testclient import TestClient
except ImportError:
    raise unittest.SkipTest(
        "FastAPI não instalado (pip install -r requirements-dev.txt)"
    )

from web.app import create_app


class AppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_health(self) -> None:
        response = self.client.get("/api/saude")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_docs_page(self) -> None:
        response = self.client.get("/docs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("FourPC API", response.text)

    def test_openapi_lists_health_route(self) -> None:
        schema = self.client.get("/openapi.json").json()

        self.assertIn("/api/saude", schema["paths"])


if __name__ == "__main__":
    unittest.main()
