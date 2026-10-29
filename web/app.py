from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from core.catalog import Catalog
from web.routes import api

DESCRIPTION = (
    "API do FourPC, o simulador de montagem de PC. Ela usa as mesmas regras "
    "de compatibilidade do programa de terminal (pasta `core/`)."
)


# Criei o app numa função pra conseguir montar um app novo em cada teste.
# Sem catálogo, usa o data/catalog.json.
def create_app(catalog: Catalog | None = None) -> FastAPI:
    app = FastAPI(title="FourPC API", description=DESCRIPTION, version="1.0.0")
    app.state.catalog = catalog if catalog is not None else Catalog.from_json()
    app.include_router(api.router)

    # enquanto o site não tem página inicial, a raiz leva pra documentação
    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        return RedirectResponse("/docs")

    return app


app = create_app()
