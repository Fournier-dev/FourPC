import io
import unittest

from core.colors import GREEN, RED, RESET, YELLOW, colorize, should_use_color


# finge ser um terminal de verdade
class FakeTerminal(io.StringIO):
    def isatty(self) -> bool:
        return True


class ShouldUseColorTest(unittest.TestCase):
    def test_terminal_usa_cor(self) -> None:
        self.assertTrue(should_use_color(FakeTerminal(), {}))

    def test_arquivo_ou_pipe_nao_usa_cor(self) -> None:
        self.assertFalse(should_use_color(io.StringIO(), {}))

    def test_no_color_desliga_a_cor(self) -> None:
        self.assertFalse(should_use_color(FakeTerminal(), {"NO_COLOR": "1"}))

    def test_no_color_vazio_nao_conta(self) -> None:
        self.assertTrue(should_use_color(FakeTerminal(), {"NO_COLOR": ""}))

    def test_stream_fechado_nao_usa_cor(self) -> None:
        # o isatty de um StringIO fechado dá ValueError
        stream = io.StringIO()
        stream.close()
        self.assertFalse(should_use_color(stream, {}))


class ColorizeTest(unittest.TestCase):
    def test_ok_fica_verde(self) -> None:
        self.assertEqual(
            colorize("  [ OK ] Soquete"), f"  {GREEN}[ OK ]{RESET} Soquete"
        )

    def test_erro_fica_vermelho(self) -> None:
        self.assertEqual(
            colorize("[ERRO] Fonte"), f"{RED}[ERRO]{RESET} Fonte"
        )

    def test_aviso_fica_amarelo(self) -> None:
        self.assertEqual(
            colorize("[AVISO] RAM"), f"{YELLOW}[AVISO]{RESET} RAM"
        )

    def test_marcacoes_do_menu(self) -> None:
        self.assertIn(f"{RED}[!]{RESET}", colorize("  [!] 1 problema"))
        self.assertIn(f"{YELLOW}[i]{RESET}", colorize("  [i] 1 aviso"))

    def test_texto_sem_etiqueta_nao_muda(self) -> None:
        text = "Total parcial   R$ 1.299,90"
        self.assertEqual(colorize(text), text)

    def test_pendente_fica_sem_cor(self) -> None:
        self.assertEqual(colorize("[ -- ] Soquete"), "[ -- ] Soquete")


if __name__ == "__main__":
    unittest.main()
