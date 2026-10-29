from typing import Annotated

from fastapi import APIRouter, Depends, Request

from core.catalog import Catalog
from web.schemas import CatalogOut

router = APIRouter(prefix="/api", tags=["API"])


# O catálogo é carregado uma vez só, quando o app sobe, e fica guardado no
# app.state. As rotas pegam ele por aqui (nos testes dá pra trocar por um
# catálogo menor).
def get_catalog(request: Request) -> Catalog:
    catalog: Catalog = request.app.state.catalog
    return catalog


CatalogDep = Annotated[Catalog, Depends(get_catalog)]


# rota simples pra saber se o servidor está no ar
@router.get("/saude", summary="Verifica se a API está no ar")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/catalogo",
    summary="Lista as peças do catálogo",
    description="Peças agrupadas por categoria, do mais barato pro mais caro.",
)
def list_catalog(catalog: CatalogDep) -> CatalogOut:
    return CatalogOut.from_catalog(catalog)
