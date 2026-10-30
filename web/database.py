import os
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    DateTime, Engine, ForeignKey, Numeric, String, UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, Session, mapped_column, relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

# sem a variável de ambiente, o banco é um arquivo fourpc.db na pasta
# de onde o servidor foi iniciado
DEFAULT_DATABASE_URL = "sqlite:///fourpc.db"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Os nomes das tabelas e colunas ficaram em português (como no banco),
# mas os atributos em Python seguem em inglês, igual o resto do código.
class BuildRow(Base):
    __tablename__ = "montagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        "codigo", String(16), unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "criada_em", DateTime(timezone=True), default=_now
    )
    # Numeric guarda o valor exato, sem os erros de arredondamento do float
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    parts: Mapped[list["BuildPartRow"]] = relationship(
        back_populates="build",
        cascade="all, delete-orphan",
        order_by="BuildPartRow.id",
    )


# Uma linha pra cada peça da montagem. A posição separa o disco principal
# (1) do segundo disco (2); nas outras categorias é sempre 1.
class BuildPartRow(Base):
    __tablename__ = "montagem_pecas"
    __table_args__ = (UniqueConstraint("montagem_id", "categoria", "posicao"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(
        "montagem_id", ForeignKey("montagens.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column("categoria", String(20))
    position: Mapped[int] = mapped_column("posicao", default=1)
    component_id: Mapped[str] = mapped_column("peca_id", String(80))

    build: Mapped[BuildRow] = relationship(back_populates="parts")


def create_db_engine(url: str | None = None) -> Engine:
    url = url if url is not None else get_database_url()
    if not url.startswith("sqlite"):
        return create_engine(url)
    # O SQLite por padrão só deixa usar a conexão na thread que criou, e o
    # FastAPI roda as rotas em outras threads. No banco em memória (usado
    # nos testes) também precisa ser sempre a mesma conexão, senão cada
    # conexão nova abre um banco vazio.
    connect_args = {"check_same_thread": False}
    if url in ("sqlite://", "sqlite:///:memory:"):
        return create_engine(
            url, connect_args=connect_args, poolclass=StaticPool
        )
    return create_engine(url, connect_args=connect_args)


# create_all só cria as tabelas que ainda não existem, então pode rodar
# toda vez que o app sobe
def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
