from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.models import Category
from core.validators import (
    FORM_FACTOR_RULE, MIN_RECOMMENDED_RAM_GB, PSU_RULE, PSU_SAFETY_MARGIN,
    RAM_CAPACITY_RULE, RAM_RULE, RULES, SOCKET_RULE, STORAGE_KIND_RULE,
)
from web.dependencies import CatalogDep

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# as páginas HTML ficam fora do /docs, que é só pra API
router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@dataclass(frozen=True)
class RuleCard:
    name: str
    blocks: bool  # True = erro (impede de finalizar), False = só aviso
    description: str


# os nomes vêm do core/, assim o site e o terminal mostram o mesmo texto
RULE_CARDS = [
    RuleCard(
        SOCKET_RULE, True,
        "O soquete do processador tem que ser igual ao da placa-mãe "
        "(ex.: AM5 com AM5).",
    ),
    RuleCard(
        RAM_RULE, True,
        "A memória tem que ser do padrão que a placa-mãe aceita: DDR4 ou "
        "DDR5.",
    ),
    RuleCard(
        PSU_RULE, True,
        "A fonte precisa aguentar o processador e a placa de vídeo com "
        f"{PSU_SAFETY_MARGIN:.0%} de folga.",
    ),
    RuleCard(
        FORM_FACTOR_RULE, True,
        "A placa-mãe (ATX, mATX ou ITX) precisa caber no gabinete.",
    ),
    RuleCard(
        RAM_CAPACITY_RULE, False,
        f"Com menos de {MIN_RECOMMENDED_RAM_GB} GB de memória o PC funciona, "
        "mas fica lento em jogos e com muitos programas abertos.",
    ),
    RuleCard(
        STORAGE_KIND_RULE, False,
        "HD como disco principal deixa o sistema lento para ligar. O ideal "
        "é um SSD, e o HD fica para guardar arquivos.",
    ),
]


@router.get("/", response_class=HTMLResponse)
def home(request: Request, catalog: CatalogDep) -> HTMLResponse:
    total_parts = sum(len(catalog.options(c)) for c in Category)
    return templates.TemplateResponse(request, "index.html", {
        "active": "inicio",
        "rules": RULE_CARDS,
        "total_parts": total_parts,
        "total_categories": len(Category),
        "total_rules": len(RULES),
    })
