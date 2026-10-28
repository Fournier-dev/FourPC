import re
from collections.abc import Mapping
from typing import TextIO

from core.report import STATUS_TAGS
from core.validators import Status

# códigos ANSI que quase todo terminal entende
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# as marcações [!] e [i] do menu ganham a mesma cor de erro e aviso
TAG_COLORS: dict[str, str] = {
    STATUS_TAGS[Status.OK]: GREEN,
    STATUS_TAGS[Status.FAIL]: RED,
    STATUS_TAGS[Status.WARNING]: YELLOW,
    "[!]": RED,
    "[i]": YELLOW,
}

_TAG_PATTERN = re.compile(
    "|".join(re.escape(tag) for tag in TAG_COLORS)
)


# Segui a convenção do no-color.org: se a variável NO_COLOR existir e não
# estiver vazia, nada de cor. Também não uso cor quando a saída vai pra um
# arquivo ou pipe, senão os códigos ANSI aparecem como lixo no texto.
def should_use_color(stream: TextIO, environ: Mapping[str, str]) -> bool:
    if environ.get("NO_COLOR"):
        return False
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        # stream fechado ou que não é de verdade
        return False


# pinta só as etiquetas, o resto do texto continua igual
def colorize(text: str) -> str:
    return _TAG_PATTERN.sub(
        lambda match: f"{TAG_COLORS[match.group()]}{match.group()}{RESET}",
        text,
    )
