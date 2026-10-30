from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.catalog import Catalog
from core.presets import DEFAULT_PRESETS_PATH
from web.database import (
    create_db_engine, create_tables, make_session_factory,
)
from web.repository import BuildRepository
from web.routes import api, pages

STATIC_DIR = Path(__file__).resolve().parent / "static"

DESCRIPTION = (
    "API do FourPC, o simulador de montagem de PC. Ela usa as mesmas regras "
    "de compatibilidade do programa de terminal (pasta `core/`)."
)


# As tabelas são criadas quando o servidor sobe (e não quando o arquivo é
# importado), assim só importar o app não cria o fourpc.db.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_tables(app.state.engine)
    yield
    app.state.engine.dispose()


# Criei o app numa função pra conseguir montar um app novo em cada teste.
# Sem catálogo, usa o data/catalog.json. Sem database_url, usa a variável
# de ambiente DATABASE_URL (nos testes eu passo "sqlite://", em memória).
def create_app(
    catalog: Catalog | None = None,
    presets_path: Path = DEFAULT_PRESETS_PATH,
    database_url: str | None = None,
) -> FastAPI:
    app = FastAPI(
        title="FourPC API", description=DESCRIPTION, version="1.0.0",
        lifespan=lifespan,
    )
    app.state.catalog = catalog if catalog is not None else Catalog.from_json()
    app.state.presets_path = presets_path
    engine = create_db_engine(database_url)
    app.state.engine = engine
    app.state.repository = BuildRepository(make_session_factory(engine))
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(api.router)
    app.include_router(pages.router)

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
