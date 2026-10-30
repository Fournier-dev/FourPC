from typing import Annotated

from fastapi import Depends, Request

from core.catalog import Catalog
from web.repository import BuildRepository


# O catálogo é carregado uma vez só, quando o app sobe, e fica guardado no
# app.state. As rotas pegam ele por aqui (nos testes dá pra trocar por um
# catálogo menor).
def get_catalog(request: Request) -> Catalog:
    catalog: Catalog = request.app.state.catalog
    return catalog


# mesma ideia pro banco: o repositório é criado junto com o app
def get_repository(request: Request) -> BuildRepository:
    repository: BuildRepository = request.app.state.repository
    return repository


CatalogDep = Annotated[Catalog, Depends(get_catalog)]
RepositoryDep = Annotated[BuildRepository, Depends(get_repository)]
