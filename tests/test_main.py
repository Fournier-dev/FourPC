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


# catálogo pequeno pros testes: 2 opções por categoria e a opção 1
# é sempre a compatível
def small_catalog() -> Catalog:
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


# escolhe a opção 1 em todas as 7 categorias
def select_all_first_options() -> list[str]:
    inputs: list[str] = []
    for menu_option in range(1, 8):
        inputs += [str(menu_option), "1"]
    return inputs


# finge ser o terminal: vai devolvendo as respostas da lista e guarda
# tudo que foi impresso
class ScriptedSession:
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

    def test_full_session_exports_all_formats(self) -> None:
        session = self.run_app(select_all_first_options() + ["9", "4"])

        exported = sorted(path.suffix for path in self.reports_dir.iterdir())
        self.assertEqual(exported, [".csv", ".json", ".txt"])
        self.assertIn("Obrigado por usar o FourPC!", session.output)

        json_file = next(self.reports_dir.glob("*.json"))
        data = json.loads(json_file.read_text(encoding="utf-8"))
        self.assertEqual(data["total_price"], "5400.00")

    def test_exports_only_csv(self) -> None:
        self.run_app(select_all_first_options() + ["9", "3"])

        exported = [path.suffix for path in self.reports_dir.iterdir()]
        self.assertEqual(exported, [".csv"])

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

    def test_options_are_listed_from_cheapest(self) -> None:
        catalog = Catalog({
            Category.CPU: [
                make_cpu(price="2000.00", component_id="cpu-cara"),
                make_cpu(price="900.00", component_id="cpu-barata"),
            ],
        })
        session = ScriptedSession(["1", "1", "0", "s"])
        app = FourPCApp(
            catalog, self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertLess(
            session.output.index("R$ 900,00"),
            session.output.index("R$ 2.000,00"),
        )
        # a opção 1 tem que ser a mais barata
        self.assertEqual(
            app.build.get(Category.CPU), catalog.get("cpu-barata")
        )

    def test_options_show_price_diff_from_current(self) -> None:
        catalog = Catalog({
            Category.CPU: [
                make_cpu(price="900.00", component_id="cpu-barata"),
                make_cpu(price="1200.00", component_id="cpu-media"),
                make_cpu(price="750.00", component_id="cpu-mais-barata"),
            ],
        })
        # escolhe a do meio (R$ 900,00) e depois abre a lista de novo
        session = ScriptedSession(["1", "2", "1", "0", "0", "s"])
        app = FourPCApp(
            catalog, self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertIn("Diferença: +R$ 300,00", session.output)
        self.assertIn("Diferença: -R$ 150,00", session.output)
        # sem peça escolhida ainda não tem diferença pra mostrar
        first_list = session.output.split("Peça selecionada")[0]
        self.assertNotIn("Diferença", first_list)

    def test_low_ram_shows_warning_but_allows_finalize(self) -> None:
        # mesmo catálogo pequeno, mas a única RAM tem só 8 GB
        base = small_catalog()
        components = {cat: base.options(cat) for cat in Category}
        components[Category.RAM] = [
            make_ram(capacity_gb=8, component_id="ram-8gb")
        ]
        session = ScriptedSession(select_all_first_options() + ["9", "2"])
        app = FourPCApp(
            Catalog(components), self.reports_dir, session.input,
            session.print,
        )

        app.run()

        self.assertIn("AVISO\n  [AVISO] Quantidade de Memória RAM",
                      session.output)
        self.assertIn("[i] 1 aviso(s) na montagem.", session.output)
        self.assertNotIn("ALERTA DE COMPATIBILIDADE", session.output)
        self.assertIn("Obrigado por usar o FourPC!", session.output)
        self.assertEqual(len(list(self.reports_dir.iterdir())), 1)

    def test_remove_current_component(self) -> None:
        catalog = small_catalog()
        # escolhe a CPU 1 e depois abre de novo e usa a opção 3 (remover)
        session = ScriptedSession(["1", "1", "1", "3", "0", "s"])
        app = FourPCApp(
            catalog, self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertIn("3) Remover peça atual", session.output)
        self.assertIn("Peça removida de Processador", session.output)
        self.assertIsNone(app.build.get(Category.CPU))

    def test_remove_option_hidden_without_component(self) -> None:
        # sem peça escolhida o 3 é inválido nessa tela
        session = self.run_app(["1", "3", "0", "0", "s"])

        self.assertNotIn("Remover peça atual", session.output)
        self.assertIn("Digite um número de 0 a 2.", session.output)

    def test_invalid_option_asks_again(self) -> None:
        session = self.run_app(["abc", "42", "0", "s"])

        self.assertEqual(
            session.output.count(
                "Opção inválida. Digite um número de 0 a 12."
            ),
            2,
        )

    def test_budget_warning_when_total_exceeds_limit(self) -> None:
        # define R$ 5.000 e escolhe tudo (total de R$ 5.400)
        inputs = ["10", "5.000,00"] + select_all_first_options() + [
            "8", "",   # abre o resumo e volta
            "0", "s",
        ]

        session = self.run_app(inputs)

        self.assertIn("Orçamento máximo definido: R$ 5.000,00",
                      session.output)
        self.assertIn(
            "[!] O total passou do orçamento de R$ 5.000,00 em R$ 400,00.",
            session.output,
        )
        summary = session.output.split("RESUMO DA MONTAGEM")[1]
        self.assertIn("passou do orçamento", summary)

    def test_budget_within_limit_has_no_warning(self) -> None:
        inputs = ["10", "6000"] + select_all_first_options() + [
            "8", "", "0", "s",
        ]

        session = self.run_app(inputs)

        self.assertNotIn("passou do orçamento", session.output)
        self.assertIn("Dentro do orçamento (sobram R$ 600,00)",
                      session.output)

    def test_budget_does_not_block_finalize(self) -> None:
        inputs = ["10", "100"] + select_all_first_options() + ["9", "2"]

        session = self.run_app(inputs)

        self.assertIn("Obrigado por usar o FourPC!", session.output)
        self.assertEqual(len(list(self.reports_dir.iterdir())), 1)

    def test_invalid_budget_asks_again_and_empty_removes(self) -> None:
        inputs = ["10", "abc", "-50", "3000", "10", "", "0", "s"]
        session = ScriptedSession(inputs)
        app = FourPCApp(
            small_catalog(), self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertEqual(session.output.count("Valor inválido."), 2)
        self.assertIn("Orçamento máximo atual: R$ 3.000,00", session.output)
        self.assertIn("Orçamento máximo removido.", session.output)
        self.assertIsNone(app.budget)

    def test_load_exported_json_by_file_name(self) -> None:
        # primeiro exporta um JSON, depois abre o programa de novo e carrega
        self.run_app(select_all_first_options() + ["9", "2"])
        json_file = next(self.reports_dir.glob("*.json"))
        session = ScriptedSession(["11", json_file.name, "0", "s"])
        app = FourPCApp(
            small_catalog(), self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertIn("Orçamento carregado: 7 peça(s).", session.output)
        self.assertTrue(app.build.is_complete)
        self.assertEqual(app.build.total_price, 5400)

    def test_load_warns_about_ids_not_in_catalog(self) -> None:
        path = self.reports_dir / "antigo.json"
        path.write_text(json.dumps({"components": [
            {"category": "cpu", "id": "cpu-am5"},
            {"category": "gpu", "id": "gpu-que-saiu"},
        ]}), encoding="utf-8")
        session = ScriptedSession(["11", str(path), "0", "s"])
        app = FourPCApp(
            small_catalog(), self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertIn("Orçamento carregado: 1 peça(s).", session.output)
        self.assertIn("não existem mais no catálogo: gpu-que-saiu",
                      session.output)
        self.assertIsNone(app.build.get(Category.GPU))

    def test_load_invalid_file_keeps_current_build(self) -> None:
        inputs = ["1", "1", "11", "nao-existe.json", "0", "s"]
        session = ScriptedSession(inputs)
        app = FourPCApp(
            small_catalog(), self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertIn("Não foi possível carregar o orçamento", session.output)
        self.assertIsNotNone(app.build.get(Category.CPU))

    def test_load_asks_before_replacing_build(self) -> None:
        path = self.reports_dir / "outro.json"
        path.write_text(json.dumps({"components": [
            {"category": "cpu", "id": "cpu-intel"},
        ]}), encoding="utf-8")
        # responde "n" na confirmação, então fica a CPU AM5
        inputs = ["1", "1", "11", str(path), "n", "0", "s"]
        session = ScriptedSession(inputs)
        catalog = small_catalog()
        app = FourPCApp(
            catalog, self.reports_dir, session.input, session.print
        )

        app.run()

        self.assertIn("será substituída", session.output)
        self.assertEqual(app.build.get(Category.CPU), catalog.get("cpu-am5"))

    def write_presets(self) -> Path:
        path = self.reports_dir / "presets.json"
        path.write_text(json.dumps({"presets": [
            {"name": "Só CPU", "description": "Uma peça só.",
             "components": {"cpu": "cpu-intel"}},
            {"name": "Completa", "description": "Tudo compatível.",
             "components": {
                 "cpu": "cpu-am5", "motherboard": "mb-am5",
                 "ram": "ram-ddr5", "gpu": "gpu-small", "psu": "psu-650",
                 "storage": "ssd-1", "case": "case-1",
             }},
        ]}), encoding="utf-8")
        return path

    def run_with_presets(self, inputs: list[str]) -> tuple[
        FourPCApp, ScriptedSession
    ]:
        session = ScriptedSession(inputs)
        app = FourPCApp(
            small_catalog(), self.reports_dir, session.input, session.print,
            presets_path=self.write_presets(),
        )
        app.run()
        return app, session

    def test_load_preset_and_finalize(self) -> None:
        app, session = self.run_with_presets(["12", "2", "9", "2"])

        self.assertIn("MONTAGENS PRONTAS", session.output)
        self.assertIn("Tudo compatível.", session.output)
        self.assertIn("Montagem carregada: Completa (R$ 5.400,00).",
                      session.output)
        self.assertTrue(app.build.is_complete)
        self.assertIn("Obrigado por usar o FourPC!", session.output)

    def test_preset_asks_before_replacing_build(self) -> None:
        # escolhe a CPU AM5 e responde "n" ao carregar a montagem pronta
        app, session = self.run_with_presets(
            ["1", "1", "12", "1", "n", "0", "s"]
        )

        self.assertIn("será substituída", session.output)
        self.assertEqual(
            app.build.get(Category.CPU), app.catalog.get("cpu-am5")
        )

    def test_preset_back_keeps_build(self) -> None:
        app, _ = self.run_with_presets(["12", "0", "0", "s"])

        self.assertEqual(app.build.selected(), [])

    def test_preset_file_error_is_shown(self) -> None:
        session = ScriptedSession(["12", "0", "s"])
        app = FourPCApp(
            small_catalog(), self.reports_dir, session.input, session.print,
            presets_path=self.reports_dir / "nao-existe.json",
        )

        app.run()

        self.assertIn("Não foi possível carregar as montagens prontas",
                      session.output)

    def test_exit_requires_confirmation(self) -> None:
        session = self.run_app(["0", "n", "0", "s"])

        self.assertEqual(session.output.count("Deseja mesmo sair?"), 2)
        self.assertIn("Até a próxima!", session.output)


if __name__ == "__main__":
    unittest.main()
