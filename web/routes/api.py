from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from core.presets import PresetError, load_presets
from core.selection import SelectionError, build_from_ids
from web.dependencies import CatalogDep
from web.schemas import BuildIn, CatalogOut, PresetOut, ValidationOut

router = APIRouter(prefix="/api", tags=["API"])


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


@router.get(
    "/presets",
    summary="Lista as montagens prontas sugeridas",
    description="Cada montagem já vem com os IDs no formato do "
    "`/api/montagens/validar` e o preço total calculado.",
)
def list_presets(request: Request, catalog: CatalogDep) -> list[PresetOut]:
    presets_path: Path = request.app.state.presets_path
    try:
        presets = load_presets(catalog, presets_path)
    except PresetError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Não foi possível carregar as montagens prontas: {error}",
        ) from None
    return [PresetOut.from_preset(preset) for preset in presets]


# 422 é o código que o FastAPI já usa quando os dados enviados estão errados
@router.post(
    "/montagens/validar",
    summary="Valida uma montagem sem salvar",
    description="Recebe o ID da peça de cada categoria e devolve o resultado "
    "de todas as regras de compatibilidade, o consumo de energia e o preço "
    "(total, PIX e parcelado). Pode mandar uma montagem incompleta: as "
    "regras que dependem das peças que faltam voltam como `pending`.",
    responses={422: {"description": "Algum ID ou categoria inválido"}},
)
def validate_build(selection: BuildIn, catalog: CatalogDep) -> ValidationOut:
    try:
        build = build_from_ids(
            catalog, selection.components, selection.extra_storage
        )
    except SelectionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return ValidationOut.from_build(build)
