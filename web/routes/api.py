from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["API"])


# rota simples pra saber se o servidor está no ar
@router.get("/saude", summary="Verifica se a API está no ar")
def health() -> dict[str, str]:
    return {"status": "ok"}
