from pathlib import Path

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# as páginas HTML ficam fora do /docs, que é só pra API
router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=TEMPLATES_DIR)
