import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import main
from core.catalog import DEFAULT_CATALOG_PATH
from core.models import Category


class ParseArgsTest(unittest.TestCase):
    def test_sem_argumentos_usa_catalogo_padrao(self) -> None:
        args = main.parse_args([])
        self.assertEqual(args.catalogo, DEFAULT_CATALOG_PATH)

    def test_catalogo_recebe_o_caminho_informado(self) -> None:
        args = main.parse_args(["--catalogo", "outro.json"])
        self.assertEqual(args.catalogo, Path("outro.json"))

    def test_argumento_desconhecido_encerra_com_erro(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main.parse_args(["--nao-existe"])
        self.assertEqual(context.exception.code, 2)


# troca a parte que mexe no terminal pra não atrapalhar o runner
@mock.patch("main._use_utf8_output")
class MainCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_custom_catalog(self) -> Path:
        raw: dict[str, Any] = json.loads(
            DEFAULT_CATALOG_PATH.read_text(encoding="utf-8")
        )
        raw[Category.CPU.value][0]["id"] = "cpu-personalizado"
        path = self.tmp_dir / "meu_catalogo.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return path

    def test_usa_o_catalogo_informado(self, _utf8: mock.Mock) -> None:
        path = self._write_custom_catalog()
        with mock.patch("main.FourPCApp") as app_class:
            code = main.main(["--catalogo", str(path)])

        self.assertEqual(code, 0)
        catalog = app_class.call_args.args[0]
        self.assertEqual(catalog.get("cpu-personalizado").id,
                         "cpu-personalizado")

    def test_catalogo_inexistente_retorna_erro(
        self, _utf8: mock.Mock
    ) -> None:
        path = self.tmp_dir / "sumiu.json"
        stderr = io.StringIO()
        with mock.patch("main.FourPCApp") as app_class:
            with contextlib.redirect_stderr(stderr):
                code = main.main(["--catalogo", str(path)])

        self.assertEqual(code, 1)
        app_class.assert_not_called()
        self.assertIn("Erro ao carregar o catálogo", stderr.getvalue())
        self.assertIn("sumiu.json", stderr.getvalue())

    def test_catalogo_com_json_invalido_retorna_erro(
        self, _utf8: mock.Mock
    ) -> None:
        path = self.tmp_dir / "quebrado.json"
        path.write_text("{ isso não é json", encoding="utf-8")
        with mock.patch("main.FourPCApp") as app_class:
            with contextlib.redirect_stderr(io.StringIO()):
                code = main.main(["--catalogo", str(path)])

        self.assertEqual(code, 1)
        app_class.assert_not_called()


class FakeTerminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@mock.patch("main._use_utf8_output")
@mock.patch("main._enable_ansi_colors", return_value=True)
class MainColorTest(unittest.TestCase):
    def _use_color(self, environ: dict[str, str]) -> bool:
        with mock.patch.dict("os.environ", environ, clear=True):
            with mock.patch("sys.stdout", FakeTerminal()):
                with mock.patch("main.FourPCApp") as app_class:
                    main.main([])
        value: bool = app_class.call_args.kwargs["use_color"]
        return value

    def test_terminal_liga_a_cor(
        self, _ansi: mock.Mock, _utf8: mock.Mock
    ) -> None:
        self.assertTrue(self._use_color({}))

    def test_no_color_desliga_a_cor(
        self, _ansi: mock.Mock, _utf8: mock.Mock
    ) -> None:
        self.assertFalse(self._use_color({"NO_COLOR": "1"}))

    def test_sem_suporte_a_ansi_fica_sem_cor(
        self, ansi: mock.Mock, _utf8: mock.Mock
    ) -> None:
        ansi.return_value = False
        self.assertFalse(self._use_color({}))


if __name__ == "__main__":
    unittest.main()
