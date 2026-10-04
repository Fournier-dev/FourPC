"""Testes de ponta a ponta da CLI, simulando o que o usuário digita."""

import json
import tempfile
import unittest
from collections.abc import Iterable
from pathlib import Path

from core.catalog import Catalog
from core.models import Category, Component, RamType
from main import FourPCApp
from tests.helpers import (
    make_case, make_cpu, make_gpu, make_motherboard, make_psu, make_ram,
    make_storage,
)


def small_catalog() -> Catalog:
    """Duas opções por categoria; a opção 1 é sempre a compatível."""
    components: dict[Category, list[Component]] = {
        Category.CPU: [
            make_cpu("AM5", component_id="cpu-am5"),
            make_cpu("LGA1700", component_id="cpu-intel"),
        ],
        Category.MOTHERBOARD: [
            make_motherboard("AM5", RamType.DDR5, component_id="mb-am5"),
            make_motherboard("AM4", RamType.DDR4, component_id="mb-am4"),
        ],
        Category.RAM: [
            make_ram(RamType.DDR5, component_id="ram-ddr5"),
            make_ram(RamType.DDR4, component_id="ram-ddr4"),
        ],
        Category.GPU: [
            make_gpu(115, component_id="gpu-small"),
            make_gpu(575, component_id="gpu-huge"),
        ],
        Category.PSU: [
            make_psu(650, component_id="psu-650"),
            make_psu(300, component_id="psu-300"),
        ],
        Category.STORAGE: [
            make_storage(component_id="ssd-1"),
            make_storage(component_id="ssd-2"),
        ],
        Category.CASE: [
            make_case(component_id="case-1"),
            make_case(component_id="case-2"),
        ],
    }
    return Catalog(components)


def select_all_first_options() -> list[str]:
    """Entradas que escolhem a opção 1 em cada uma das 7 categorias."""
    inputs: list[str] = []
    for menu_option in range(1, 8):
        inputs += [str(menu_option), "1"]
    return inputs


class ScriptedSession:
    """Simula o terminal: fornece entradas pré-definidas e guarda a saída."""

    def __init__(self, inputs: Iterable[str]) -> None:
        self._inputs = iter(inputs)
        self.lines: list[str] = []

    def input(self, prompt: str) -> str:
        self.lines.append(prompt)
        try:
            return next(self._inputs)
        except StopIteration:
            raise EOFError("entradas do teste esgotadas") from None

    def print(self, text: str = "") -> None:
        self.lines.append(text)

    @property
    def output(self) -> str:
        return "\n".join(self.lines)


class FourPCAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.reports_dir = Path(self._tmp.name)

    def run_app(self, inputs: list[str]) -> ScriptedSession:
        session = ScriptedSession(inputs)
        app = FourPCApp(
            small_catalog(), self.reports_dir, session.input, session.print
        )
        app.run()
        return session

    def test_full_session_exports_both_formats(self) -> None:
        session = self.run_app(select_all_first_options() + ["9", "3"])

        exported = sorted(path.suffix for path in self.reports_dir.iterdir())
        self.assertEqual(exported, [".json", ".txt"])
        self.assertIn("Obrigado por usar o FourPC!", session.output)

        json_file = next(self.reports_dir.glob("*.json"))
        data = json.loads(json_file.read_text(encoding="utf-8"))
        self.assertEqual(data["total_price"], "5400.00")

    def test_incompatible_choice_shows_alert_and_blocks_export(self) -> None:
        inputs = [
            "1", "1",  # CPU AM5
            "2", "2",  # placa-mãe AM4 -> incompatível
            "9",       # tenta finalizar
            "0", "s",  # sai
        ]

        session = self.run_app(inputs)

        self.assertIn("ALERTA DE COMPATIBILIDADE", session.output)
        self.assertIn("soquete AM5", session.output)
        self.assertIn("Faltam:", session.output)
        self.assertEqual(list(self.reports_dir.iterdir()), [])

    def test_finalize_lists_incompatibilities(self) -> None:
        inputs = select_all_first_options() + [
            "4", "2",  # troca para a GPU de 575 W (fonte de 650 W não basta)
            "9",       # tenta finalizar
            "0", "s",
        ]

        session = self.run_app(inputs)

        self.assertIn("Corrija as incompatibilidades", session.output)
        self.assertIn("pelo menos 768 W", session.output)
        self.assertEqual(list(self.reports_dir.iterdir()), [])

    def test_options_are_flagged_before_being_chosen(self) -> None:
        inputs = ["1", "1", "2", "0", "0", "s"]

        session = self.run_app(inputs)

        self.assertIn("[!] Incompatível: Soquete CPU x Placa-Mãe",
                      session.output)

    def test_invalid_option_asks_again(self) -> None:
        session = self.run_app(["abc", "42", "0", "s"])

        self.assertEqual(
            session.output.count("Opção inválida. Digite um número de 0 a 9."),
            2,
        )

    def test_exit_requires_confirmation(self) -> None:
        session = self.run_app(["0", "n", "0", "s"])

        self.assertEqual(session.output.count("Deseja mesmo sair?"), 2)
        self.assertIn("Até a próxima!", session.output)


if __name__ == "__main__":
    unittest.main()
