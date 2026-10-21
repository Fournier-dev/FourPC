# FourPC - Simulador de Montagem de PC
# Pra rodar: python main.py

import io
import sys
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from core.catalog import Catalog, CatalogError
from core.models import Build, Category, Component
from core.presets import DEFAULT_PRESETS_PATH, PresetError, load_presets
from core.pricing import parse_brl
from core.saved_build import SavedBuildError, load_build
from core.report import (
    REPORT_WIDTH, THICK_LINE, THIN_LINE, ExportFormat, budget_warning,
    export_report, fit, format_brl, format_price_diff, format_result,
    render_summary, status_message,
)
from core.validators import find_issues, find_warnings

REPORTS_DIR = Path(__file__).resolve().parent / "reports"

LOGO = (
    r" _____                      ____    ____",
    r"|  ___|  ___   _   _  _ __ |  _ \  / ___|",
    r"| |_    / _ \ | | | || '__|| |_) || |",
    r"|  _|  | (_) || |_| || |   |  __/ | |___",
    r"|_|     \___/  \__,_||_|   |_|     \____|",
)

# opções do menu principal: 1 a 7 são as categorias
CATEGORIES = list(Category)
EXIT_OPTION = 0
SUMMARY_OPTION = 8
FINALIZE_OPTION = 9
BUDGET_OPTION = 10
LOAD_OPTION = 11
PRESETS_OPTION = 12

# larguras das colunas na lista de opções de uma categoria
NAME_WIDTH = 37
SPECS_WIDTH = 15
MAX_SPECS_WIDTH = 24

EXPORT_CHOICES: dict[int, list[ExportFormat]] = {
    1: [ExportFormat.TXT],
    2: [ExportFormat.JSON],
    3: [ExportFormat.CSV],
    4: [ExportFormat.TXT, ExportFormat.JSON, ExportFormat.CSV],
}

InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]


# Recebe o input e o print como parâmetro pra eu conseguir trocar eles
# nos testes e simular o usuário digitando.
class FourPCApp:
    def __init__(
        self,
        catalog: Catalog,
        reports_dir: Path = REPORTS_DIR,
        input_func: InputFunc = input,
        output_func: OutputFunc = print,
        presets_path: Path = DEFAULT_PRESETS_PATH,
    ) -> None:
        self.catalog = catalog
        self.reports_dir = reports_dir
        self.presets_path = presets_path
        self.build = Build()
        # orçamento máximo em R$, None = sem limite
        self.budget: Decimal | None = None
        self._input = input_func
        self._print = output_func

    def run(self) -> None:
        self._show_banner()
        while True:
            self._show_main_menu()
            choice = self._ask_option("Escolha uma opção: ", PRESETS_OPTION)
            if choice == EXIT_OPTION:
                if self._confirm(
                    "Deseja mesmo sair? A montagem atual será descartada. "
                    "(s/N): "
                ):
                    self._print("\nAté a próxima!")
                    return
            elif choice == SUMMARY_OPTION:
                self._show_summary()
            elif choice == FINALIZE_OPTION:
                if self._finalize():
                    return
            elif choice == BUDGET_OPTION:
                self._set_budget()
            elif choice == LOAD_OPTION:
                self._load_saved_build()
            elif choice == PRESETS_OPTION:
                self._choose_preset()
            else:
                self._choose_component(CATEGORIES[choice - 1])

    def _show_banner(self) -> None:
        logo_width = max(len(line) for line in LOGO)
        padding = " " * ((REPORT_WIDTH - logo_width) // 2)
        self._print(THICK_LINE)
        for line in LOGO:
            self._print(padding + line)
        self._print("")
        subtitle = "Simulador de Montagem de PC"
        self._print(subtitle.center(REPORT_WIDTH).rstrip())
        self._print(THICK_LINE)
        self._print(
            "Escolha uma peça de cada categoria. A compatibilidade é\n"
            "verificada a cada escolha e, ao final, o orçamento pode ser\n"
            "exportado em TXT, JSON ou CSV."
        )

    def _show_main_menu(self) -> None:
        self._print("")
        self._print(THICK_LINE)
        self._print("MONTAGEM ATUAL")
        self._print(THIN_LINE)
        for number, category in enumerate(CATEGORIES, start=1):
            component = self.build.get(category)
            if component is None:
                name = "(não selecionado)"
                price = ""
            else:
                name = component.name
                price = format_brl(component.price)
            line = f"  {number}) {category.label:<16}{fit(name, 36):<36}"
            self._print(f"{line}{price:>15}".rstrip())
        self._print(THIN_LINE)
        total = format_brl(self.build.total_price)
        self._print(f"{'Total parcial':>20}{total:>52}")
        if self.budget is not None:
            budget = format_brl(self.budget)
            self._print(f"{'Orçamento máximo':>20}{budget:>52}")
            warning = budget_warning(self.build, self.budget)
            if warning is not None:
                self._print(f"  [!] {warning}")

        issues = find_issues(self.build)
        if issues:
            self._print(
                f"  [!] {len(issues)} incompatibilidade(s) encontrada(s). "
                f"Veja os detalhes na opção {SUMMARY_OPTION}."
            )
        warnings = find_warnings(self.build)
        if warnings:
            self._print(
                f"  [i] {len(warnings)} aviso(s) na montagem. "
                f"Veja os detalhes na opção {SUMMARY_OPTION}."
            )
        self._print("")
        self._print(
            f"  {SUMMARY_OPTION}) Ver resumo detalhado e compatibilidade"
        )
        self._print(f"  {FINALIZE_OPTION}) Finalizar e exportar orçamento")
        self._print(f" {BUDGET_OPTION}) Definir orçamento máximo")
        self._print(f" {LOAD_OPTION}) Carregar orçamento salvo (JSON)")
        self._print(f" {PRESETS_OPTION}) Montagens prontas sugeridas")
        self._print(f"  {EXIT_OPTION}) Sair")

    def _choose_component(self, category: Category) -> None:
        options = self.catalog.options(category)
        current = self.build.get(category)

        self._print("")
        self._print(THIN_LINE)
        title = f"{category.label.upper()} - escolha uma opção"
        if current is not None:
            title += "  (> = peça atual)"
        self._print(title)
        self._print(THIN_LINE)
        # a coluna de specs cresce se precisar (a placa-mãe tem 3 dados)
        # e o nome cede o espaço, pra linha continuar com a mesma largura
        specs_width = max(
            [SPECS_WIDTH] + [len(option.specs()) for option in options]
        )
        specs_width = min(specs_width, MAX_SPECS_WIDTH)
        name_width = NAME_WIDTH + SPECS_WIDTH - specs_width
        for number, option in enumerate(options, start=1):
            marker = ">" if option == current else " "
            name = fit(option.name, name_width)
            specs = fit(option.specs(), specs_width)
            price = format_brl(option.price)
            self._print(
                f"{marker} {number:>2}) {name:<{name_width}} "
                f"{specs:<{specs_width}} {price:>12}"
            )
            # mostra quanto muda no total se trocar pela peça atual
            if current is not None and option != current:
                diff = format_price_diff(option.price - current.price)
                self._print(f"      Diferença: {diff}")
            # avisa antes de escolher se a peça vai dar problema
            for rule in self._conflicts_with(option):
                self._print(f"      [!] Incompatível: {rule}")
        # a opção de remover só aparece se já tiver peça escolhida e fica
        # logo depois da última peça da lista
        remove_option = len(options) + 1
        max_option = len(options)
        if current is not None:
            self._print(f"  {remove_option:>2}) Remover peça atual")
            max_option = remove_option
        self._print("   0) Voltar")

        choice = self._ask_option("Escolha a peça: ", max_option)
        if choice == 0:
            return
        if current is not None and choice == remove_option:
            self.build = self.build.without(category)
            self._print(
                f"\nPeça removida de {category.label}: {current.name}"
            )
            return
        selected = options[choice - 1]
        self.build = self.build.with_component(selected)
        self._print(
            f"\nPeça selecionada em {category.label}: {selected.name} "
            f"({format_brl(selected.price)})"
        )
        self._show_alerts_for(category)

    def _show_alerts_for(self, category: Category) -> None:
        issues = []
        for issue in find_issues(self.build):
            if issue.involves(category):
                issues.append(issue)
        if issues:
            self._print("\nALERTA DE COMPATIBILIDADE")
            for issue in issues:
                for line in format_result(issue):
                    self._print(line)
        # o aviso só informa, a peça continua escolhida normalmente
        for warning in find_warnings(self.build):
            if warning.involves(category):
                self._print("\nAVISO")
                for line in format_result(warning):
                    self._print(line)

    def _show_summary(self) -> None:
        self._print("")
        self._print(THICK_LINE)
        self._print("RESUMO DA MONTAGEM".center(REPORT_WIDTH).rstrip())
        self._print(THICK_LINE)
        self._print(render_summary(self.build, self.budget))
        self._print("")
        self._print(f"Status: {status_message(self.build)}")
        self._input("\nPressione Enter para voltar ao menu...")

    # retorna True se conseguiu exportar o orçamento
    def _finalize(self) -> bool:
        missing = self.build.missing_categories()
        if missing:
            names = ", ".join(category.label for category in missing)
            self._print(
                f"\nAinda não é possível finalizar. Faltam: {names}."
            )
            return False

        issues = find_issues(self.build)
        if issues:
            self._print(
                "\nCorrija as incompatibilidades abaixo antes de finalizar:"
            )
            for issue in issues:
                for line in format_result(issue):
                    self._print(line)
            return False

        self._print("")
        self._print(THICK_LINE)
        self._print("ORÇAMENTO FINAL".center(REPORT_WIDTH).rstrip())
        self._print(THICK_LINE)
        self._print(render_summary(self.build, self.budget))
        self._print("")
        self._print("Em qual formato deseja exportar o orçamento?")
        self._print("  1) TXT")
        self._print("  2) JSON")
        self._print("  3) CSV (planilha)")
        self._print("  4) Todos (TXT, JSON e CSV)")
        self._print("  0) Voltar ao menu")
        choice = self._ask_option(
            "Escolha uma opção: ", len(EXPORT_CHOICES)
        )
        if choice == 0:
            return False

        # mesma data/hora pros arquivos terem o mesmo nome
        generated_at = datetime.now()
        paths = []
        try:
            for fmt in EXPORT_CHOICES[choice]:
                path = export_report(
                    self.build, self.reports_dir, fmt, generated_at
                )
                paths.append(path)
        except OSError as error:
            self._print(f"\nNão foi possível salvar o orçamento: {error}")
            return False

        self._print("")
        for path in paths:
            self._print(f"Orçamento exportado em: {path}")
        self._print("\nObrigado por usar o FourPC!")
        return True

    # Enter vazio tira o limite. Passar do orçamento só gera aviso,
    # não impede de finalizar
    def _set_budget(self) -> None:
        self._print("")
        if self.budget is not None:
            self._print(f"Orçamento máximo atual: {format_brl(self.budget)}")
        while True:
            answer = self._input(
                "Digite o orçamento máximo em R$ (Enter para não ter "
                "limite): "
            ).strip()
            if not answer:
                if self.budget is not None:
                    self._print("\nOrçamento máximo removido.")
                self.budget = None
                return
            try:
                self.budget = parse_brl(answer)
            except ValueError:
                self._print(
                    "Valor inválido. Digite um valor maior que zero, "
                    "ex.: 5000 ou 5.000,00."
                )
                continue
            self._print(
                f"\nOrçamento máximo definido: {format_brl(self.budget)}"
            )
            warning = budget_warning(self.build, self.budget)
            if warning is not None:
                self._print(f"[!] {warning}")
            return

    # Dá pra digitar o caminho completo ou só o nome do arquivo, que aí
    # eu procuro na pasta reports/
    def _load_saved_build(self) -> None:
        self._print("")
        answer = self._input(
            "Caminho do orçamento JSON (Enter para voltar): "
        ).strip().strip('"')
        if not answer:
            return
        path = Path(answer)
        if not path.exists() and (self.reports_dir / answer).exists():
            path = self.reports_dir / answer

        try:
            loaded = load_build(path, self.catalog)
        except SavedBuildError as error:
            self._print(f"\nNão foi possível carregar o orçamento: {error}")
            return

        if self.build.selected() and not self._confirm(
            "A montagem atual será substituída. Continuar? (s/N): "
        ):
            return
        self.build = loaded.build
        count = len(loaded.build.selected())
        self._print(f"\nOrçamento carregado: {count} peça(s).")
        if loaded.missing_ids:
            ids = ", ".join(loaded.missing_ids)
            self._print(
                f"[!] Peças que não existem mais no catálogo: {ids}. "
                "Escolha outras para essas categorias."
            )

    # as montagens prontas são só um ponto de partida, depois dá pra trocar
    # qualquer peça normalmente
    def _choose_preset(self) -> None:
        try:
            presets = load_presets(self.catalog, self.presets_path)
        except PresetError as error:
            self._print(
                f"\nNão foi possível carregar as montagens prontas: {error}"
            )
            return
        if not presets:
            self._print("\nNenhuma montagem pronta cadastrada.")
            return

        self._print("")
        self._print(THIN_LINE)
        self._print("MONTAGENS PRONTAS - escolha uma opção")
        self._print(THIN_LINE)
        for number, preset in enumerate(presets, start=1):
            total = format_brl(preset.build.total_price)
            self._print(f"  {number}) {fit(preset.name, 52):<52}{total:>15}")
            if preset.description:
                self._print(f"     {preset.description}")
        self._print("  0) Voltar")

        choice = self._ask_option("Escolha a montagem: ", len(presets))
        if choice == 0:
            return
        if self.build.selected() and not self._confirm(
            "A montagem atual será substituída. Continuar? (s/N): "
        ):
            return
        preset = presets[choice - 1]
        self.build = preset.build
        self._print(
            f"\nMontagem carregada: {preset.name} "
            f"({format_brl(preset.build.total_price)})."
        )
        self._print("Você pode trocar qualquer peça pelo menu.")

    # regras que dariam erro se essa peça fosse escolhida agora
    def _conflicts_with(self, option: Component) -> list[str]:
        test_build = self.build.with_component(option)
        rules = []
        for issue in find_issues(test_build):
            if issue.involves(option.category):
                rules.append(issue.rule)
        return rules

    # fica perguntando até a pessoa digitar um número válido
    def _ask_option(self, prompt: str, max_option: int) -> int:
        while True:
            answer = self._input(prompt).strip()
            if answer.isdecimal() and int(answer) <= max_option:
                return int(answer)
            self._print(
                f"Opção inválida. Digite um número de 0 a {max_option}."
            )

    def _confirm(self, prompt: str) -> bool:
        return self._input(prompt).strip().lower() in ("s", "sim")


# sem isso a acentuação sai errada em alguns terminais (tipo o Git Bash)
def _use_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def main() -> int:
    _use_utf8_output()
    try:
        catalog = Catalog.from_json()
    except CatalogError as error:
        print(f"Erro ao carregar o catálogo: {error}", file=sys.stderr)
        return 1

    try:
        FourPCApp(catalog).run()
    except (KeyboardInterrupt, EOFError):
        print("\n\nMontagem interrompida. Até a próxima!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
