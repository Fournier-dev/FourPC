from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.catalog import Catalog
from core.presets import DEFAULT_PRESETS_PATH
from web.routes import api, pages

STATIC_DIR = Path(__file__).resolve().parent / "static"

DESCRIPTION = (
    "API do FourPC, o simulador de montagem de PC. Ela usa as mesmas regras "
    "de compatibilidade do programa de terminal (pasta `core/`)."
)


# Criei o app numa função pra conseguir montar um app novo em cada teste.
# Sem catálogo, usa o data/catalog.json.
def create_app(
    catalog: Catalog | None = None,
    presets_path: Path = DEFAULT_PRESETS_PATH,
) -> FastAPI:
    app = FastAPI(title="FourPC API", description=DESCRIPTION, version="1.0.0")
    app.state.catalog = catalog if catalog is not None else Catalog.from_json()
    app.state.presets_path = presets_path
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(api.router)
    app.include_router(pages.router)

    # enquanto o site não tem página inicial, a raiz leva pra documentação
    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        return RedirectResponse("/docs")

    # Endereço que não existe: no site mostra a página 404 com o visual do
    # site e na API responde em JSON. Os outros erros (como o 422 da
    # validação) continuam do jeito padrão do FastAPI.
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> Response:
        if exc.status_code == 404 and exc.detail == "Not Found":
            if request.url.path.startswith("/api"):
                return JSONResponse(
                    {"detail": "Rota não encontrada."}, status_code=404
                )
            return pages.templates.TemplateResponse(
                request, "404.html", status_code=404
            )
        return await http_exception_handler(request, exc)

    return app


app = create_app()
