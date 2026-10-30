import os
import unittest
from decimal import Decimal
from unittest import mock

# o banco também é parte da versão web, então sem as dependências dela
# (SQLAlchemy e FastAPI) esses testes são pulados
try:
    import sqlalchemy
    from fastapi.testclient import TestClient
except ImportError:
    raise unittest.SkipTest(
        "Dependências da web não instaladas "
        "(pip install -r requirements-dev.txt)"
    )

from core.models import Build
from tests.helpers import (
    make_case, make_cpu, make_gpu, make_motherboard, make_psu, make_ram,
    make_storage,
)
from web.app import create_app
from web.database import (
    DEFAULT_DATABASE_URL, BuildPartRow, BuildRow, create_db_engine,
    create_tables, get_database_url, make_session_factory,
)
from web.repository import (
    CODE_ALPHABET, CODE_LENGTH, BuildRepository, generate_code,
)

MEMORY_URL = "sqlite://"


def complete_build() -> Build:
    build = Build()
    for component in (
        make_cpu(component_id="cpu-1"),
        make_motherboard(component_id="mb-1"),
        make_ram(component_id="ram-1"),
        make_gpu(component_id="gpu-1"),
        make_psu(component_id="psu-1"),
        make_storage(component_id="ssd-1"),
        make_case(component_id="case-1"),
    ):
        build = build.with_component(component)
    return build


class DatabaseUrlTest(unittest.TestCase):
    def test_default_is_local_sqlite(self) -> None:
        with mock.patch.dict(os.environ, clear=True):
            self.assertEqual(get_database_url(), DEFAULT_DATABASE_URL)
        self.assertEqual(DEFAULT_DATABASE_URL, "sqlite:///fourpc.db")

    def test_reads_environment_variable(self) -> None:
        url = "sqlite:///outro.db"
        with mock.patch.dict(os.environ, {"DATABASE_URL": url}):
            self.assertEqual(get_database_url(), url)

    def test_empty_variable_uses_default(self) -> None:
        with mock.patch.dict(os.environ, {"DATABASE_URL": ""}):
            self.assertEqual(get_database_url(), DEFAULT_DATABASE_URL)


class TablesTest(unittest.TestCase):
    def test_creates_tables_with_portuguese_names(self) -> None:
        engine = create_db_engine(MEMORY_URL)
        create_tables(engine)

        inspector = sqlalchemy.inspect(engine)
        self.assertEqual(
            sorted(inspector.get_table_names()),
            ["montagem_pecas", "montagens"],
        )
        build_columns = {c["name"] for c in inspector.get_columns("montagens")}
        self.assertEqual(
            build_columns, {"id", "codigo", "criada_em", "total"}
        )
        part_columns = {
            c["name"] for c in inspector.get_columns("montagem_pecas")
        }
        self.assertEqual(
            part_columns,
            {"id", "montagem_id", "categoria", "posicao", "peca_id"},
        )
        engine.dispose()

    def test_create_tables_twice_is_safe(self) -> None:
        engine = create_db_engine(MEMORY_URL)
        create_tables(engine)
        create_tables(engine)
        engine.dispose()

    def test_app_creates_tables_on_startup(self) -> None:
        app = create_app(database_url=MEMORY_URL)
        with TestClient(app):
            inspector = sqlalchemy.inspect(app.state.engine)
            self.assertIn("montagens", inspector.get_table_names())


class GenerateCodeTest(unittest.TestCase):
    def test_code_format(self) -> None:
        for _ in range(50):
            code = generate_code()
            self.assertEqual(len(code), CODE_LENGTH)
            self.assertTrue(all(char in CODE_ALPHABET for char in code))

    def test_alphabet_has_no_confusing_characters(self) -> None:
        for char in "0O1IL":
            self.assertNotIn(char, CODE_ALPHABET)


class RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_db_engine(MEMORY_URL)
        create_tables(self.engine)
        self.session_factory = make_session_factory(self.engine)
        self.repository = BuildRepository(self.session_factory)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_save_and_get(self) -> None:
        build = complete_build()

        code = self.repository.save(build)
        record = self.repository.get(code)

        assert record is not None
        self.assertEqual(record.code, code)
        self.assertEqual(record.total, build.total_price)
        self.assertEqual(record.component_ids, {
            "cpu": "cpu-1", "motherboard": "mb-1", "ram": "ram-1",
            "gpu": "gpu-1", "psu": "psu-1", "storage": "ssd-1",
            "case": "case-1",
        })
        self.assertIsNone(record.extra_storage_id)
        self.assertIsNotNone(record.created_at)

    def test_total_keeps_cents_exact(self) -> None:
        build = Build().with_component(make_cpu(price="1299.90"))

        record = self.repository.get(self.repository.save(build))

        assert record is not None
        self.assertEqual(record.total, Decimal("1299.90"))
        self.assertIsInstance(record.total, Decimal)

    def test_extra_storage_is_saved_in_position_two(self) -> None:
        build = complete_build().with_extra_storage(
            make_storage(2000, "300.00", "hd-1", kind="HD")
        )

        code = self.repository.save(build)
        record = self.repository.get(code)

        assert record is not None
        self.assertEqual(record.component_ids["storage"], "ssd-1")
        self.assertEqual(record.extra_storage_id, "hd-1")
        with self.session_factory() as session:
            rows = session.scalars(
                sqlalchemy.select(BuildPartRow)
                .where(BuildPartRow.category == "storage")
                .order_by(BuildPartRow.position)
            ).all()
            self.assertEqual(
                [(row.position, row.component_id) for row in rows],
                [(1, "ssd-1"), (2, "hd-1")],
            )

    def test_saves_one_row_per_part(self) -> None:
        self.repository.save(complete_build())

        with self.session_factory() as session:
            count = session.scalar(
                sqlalchemy.select(sqlalchemy.func.count())
                .select_from(BuildPartRow)
            )
        self.assertEqual(count, 7)

    def test_each_build_gets_a_different_code(self) -> None:
        codes = {self.repository.save(complete_build()) for _ in range(20)}

        self.assertEqual(len(codes), 20)

    def test_get_unknown_code_returns_none(self) -> None:
        self.assertIsNone(self.repository.get("NAOEXISTE"))

    def test_get_ignores_case_and_spaces(self) -> None:
        code = self.repository.save(complete_build())

        self.assertIsNotNone(self.repository.get(f"  {code.lower()} "))

    def test_retries_when_code_is_taken(self) -> None:
        first = self.repository.save(complete_build())
        codes = iter([first, "NOVO23"])

        with mock.patch(
            "web.repository.generate_code", side_effect=lambda: next(codes)
        ):
            second = self.repository.save(complete_build())

        self.assertEqual(second, "NOVO23")

    def test_gives_up_when_codes_keep_repeating(self) -> None:
        taken = self.repository.save(complete_build())

        with (
            mock.patch("web.repository.generate_code", return_value=taken),
            self.assertRaises(RuntimeError),
        ):
            self.repository.save(complete_build())

    def test_deleting_build_deletes_parts(self) -> None:
        code = self.repository.save(complete_build())

        with self.session_factory.begin() as session:
            row = session.scalar(
                sqlalchemy.select(BuildRow).where(BuildRow.code == code)
            )
            assert row is not None
            session.delete(row)
        with self.session_factory() as session:
            count = session.scalar(
                sqlalchemy.select(sqlalchemy.func.count())
                .select_from(BuildPartRow)
            )
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
