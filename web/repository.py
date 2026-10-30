import secrets
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from core.models import Build, Category
from web.database import BuildPartRow, BuildRow

# sem 0/O e 1/I/L, que se confundem quando alguém digita o código
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
MAX_CODE_ATTEMPTS = 10

MAIN_POSITION = 1
EXTRA_STORAGE_POSITION = 2


# Montagem como ela volta do banco: só os IDs das peças, no mesmo formato
# do core.selection.build_from_ids (assim dá pra remontar a Build com o
# catálogo atual).
@dataclass(frozen=True)
class SavedBuildRecord:
    code: str
    created_at: datetime
    total: Decimal
    component_ids: dict[str, str] = field(default_factory=dict)
    extra_storage_id: str | None = None


def generate_code() -> str:
    return "".join(
        secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH)
    )


def _parts_of(build: Build) -> list[BuildPartRow]:
    parts: list[BuildPartRow] = []
    for category in Category:
        component = build.get(category)
        if component is not None:
            parts.append(BuildPartRow(
                category=category.value, position=MAIN_POSITION,
                component_id=component.id,
            ))
    if build.extra_storage is not None:
        parts.append(BuildPartRow(
            category=Category.STORAGE.value,
            position=EXTRA_STORAGE_POSITION,
            component_id=build.extra_storage.id,
        ))
    return parts


def _to_record(row: BuildRow) -> SavedBuildRecord:
    component_ids: dict[str, str] = {}
    extra_storage_id: str | None = None
    for part in row.parts:
        if (part.category == Category.STORAGE.value
                and part.position == EXTRA_STORAGE_POSITION):
            extra_storage_id = part.component_id
        else:
            component_ids[part.category] = part.component_id
    return SavedBuildRecord(
        code=row.code, created_at=row.created_at, total=row.total,
        component_ids=component_ids, extra_storage_id=extra_storage_id,
    )


# Todo acesso ao banco passa por aqui, então as rotas não precisam saber
# de SQL nem de sessão do SQLAlchemy.
class BuildRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _code_exists(self, session: Session, code: str) -> bool:
        query = select(BuildRow.id).where(BuildRow.code == code)
        return session.scalar(query) is not None

    def _new_code(self, session: Session) -> str:
        # com 31 letras e 6 posições são quase 900 milhões de códigos, mas
        # mesmo assim confiro se o sorteado já foi usado
        for _ in range(MAX_CODE_ATTEMPTS):
            code = generate_code()
            if not self._code_exists(session, code):
                return code
        raise RuntimeError("Não consegui gerar um código livre.")

    # salva as peças e o total e devolve o código da montagem
    def save(self, build: Build) -> str:
        with self._session_factory.begin() as session:
            row = BuildRow(
                code=self._new_code(session),
                total=build.total_price,
                parts=_parts_of(build),
            )
            session.add(row)
        return row.code

    def get(self, code: str) -> SavedBuildRecord | None:
        query = (
            select(BuildRow)
            .where(BuildRow.code == code.strip().upper())
            .options(selectinload(BuildRow.parts))
        )
        with self._session_factory() as session:
            row = session.scalar(query)
            return _to_record(row) if row is not None else None
