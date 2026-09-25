"""Tests for `crud.create_boletin` y la procedencia de la fila (jurisdiccion_id).

Por qué importan: `GET /boletines/calendar` filtra `Boletin.jurisdiccion_id ==
jurisdiccion_id` (el frontend siempre manda 1).  En SQL `NULL == 1` es falso, así
que una fila sin jurisdicción es **invisible** al calendario: se dibuja como
`not_found` y su botón "Descargar" no hace nada, aunque el documento esté
procesado.  Estas pruebas fijan que una fila nueva nazca con procedencia, y que
una huérfana se repare cuando se la vuelve a registrar.

Run from watcher-backend/:
    uv run pytest tests/tests/unit/test_crud_boletin.py -v
"""

import pytest
import pytest_asyncio
from app.db import crud
from app.db.models import Base, Boletin, FuenteDato
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

JURISDICCION_PROVINCIAL = 1
JURISDICCION_MUNICIPAL = 3


@pytest_asyncio.fixture
async def session():
    """Real async SQLite session over the project's declarative metadata."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db


async def _fuente(db, jurisdiccion_id: int, *, activa: bool = True) -> FuenteDato:
    fuente = FuenteDato(
        jurisdiccion_id=jurisdiccion_id,
        tipo="boletin_diario",
        nombre=f"BO de la jurisdiccion {jurisdiccion_id}",
        url_template="https://example.test/{year}/{month}/{section}_Secc_{day}{month}{year_short}.pdf",
        activa=activa,
    )
    db.add(fuente)
    await db.flush()
    return fuente


async def _visible_al_calendario(db, filename: str) -> bool:
    """La fila aparece en la consulta que arma el calendario para jurisdicción 1."""
    result = await db.execute(
        select(Boletin.id).where(
            Boletin.filename == filename,
            Boletin.jurisdiccion_id == JURISDICCION_PROVINCIAL,
        )
    )
    return result.first() is not None


class TestProcedenciaAlCrear:
    @pytest.mark.asyncio
    async def test_hereda_la_jurisdiccion_de_la_fuente_unica(self, session):
        """Con una sola fuente boletin_diario activa, la fila nace con esa jurisdicción."""
        await _fuente(session, JURISDICCION_PROVINCIAL)

        boletin = await crud.create_boletin(
            session, filename="20260604_2_Secc.pdf", date="20260604", section="2"
        )

        assert boletin.jurisdiccion_id == JURISDICCION_PROVINCIAL
        # La consecuencia que importa: el calendario la ve.
        assert await _visible_al_calendario(session, "20260604_2_Secc.pdf")

    @pytest.mark.asyncio
    async def test_jurisdiccion_explicita_gana_sobre_la_derivada(self, session):
        """Un llamador que sabe la jurisdicción manda, aunque la fuente diga otra."""
        await _fuente(session, JURISDICCION_PROVINCIAL)

        boletin = await crud.create_boletin(
            session,
            filename="20260604_2_Secc.pdf",
            date="20260604",
            section="2",
            jurisdiccion_id=JURISDICCION_MUNICIPAL,
        )

        assert boletin.jurisdiccion_id == JURISDICCION_MUNICIPAL

    @pytest.mark.asyncio
    async def test_sin_fuente_no_inventa_procedencia(self, session):
        """Sin fuente configurada la fila queda en NULL: no se afirma de quién es."""
        boletin = await crud.create_boletin(
            session, filename="20260604_2_Secc.pdf", date="20260604", section="2"
        )

        assert boletin.jurisdiccion_id is None

    @pytest.mark.asyncio
    async def test_fuente_ambigua_no_inventa_procedencia(self, session):
        """Dos fuentes activas de jurisdicciones distintas: NULL, no la primera."""
        await _fuente(session, JURISDICCION_PROVINCIAL)
        await _fuente(session, JURISDICCION_MUNICIPAL)

        boletin = await crud.create_boletin(
            session, filename="20260604_2_Secc.pdf", date="20260604", section="2"
        )

        assert boletin.jurisdiccion_id is None

    @pytest.mark.asyncio
    async def test_fuente_inactiva_no_cuenta(self, session):
        """Una fuente desactivada no define procedencia."""
        await _fuente(session, JURISDICCION_PROVINCIAL, activa=False)

        boletin = await crud.create_boletin(
            session, filename="20260604_2_Secc.pdf", date="20260604", section="2"
        )

        assert boletin.jurisdiccion_id is None


class TestReparacionDeHuerfanas:
    """Una fila que ya existe sin jurisdicción se repara al re-registrarla.

    Sin esto, la reparación no vuelve a pasar nunca: la fila invisible lo sigue
    siendo para siempre, aunque se la registre mil veces.
    """

    @pytest.mark.asyncio
    async def test_repara_por_filename(self, session):
        huerfana = Boletin(
            filename="20260604_2_Secc.pdf", date="20260604", section="2", status="completed"
        )
        session.add(huerfana)
        await session.flush()
        assert huerfana.jurisdiccion_id is None

        await _fuente(session, JURISDICCION_PROVINCIAL)
        reparada = await crud.create_boletin(
            session, filename="20260604_2_Secc.pdf", date="20260604", section="2"
        )

        assert reparada.id == huerfana.id
        assert reparada.jurisdiccion_id == JURISDICCION_PROVINCIAL
        assert await _visible_al_calendario(session, "20260604_2_Secc.pdf")

    @pytest.mark.asyncio
    async def test_repara_por_hash(self, session):
        """La rama de dedupe por hash también repara, no sólo la de filename.

        El caso real: el mismo PDF llega con otro nombre y el dedupe lo reconoce
        por hash.  Si sólo reparara la rama de filename, esa fila seguiría
        invisible para siempre.
        """
        huerfana = Boletin(
            filename="otro_nombre.pdf",
            date="20260604",
            section="2",
            status="completed",
            file_hash="a" * 64,
        )
        session.add(huerfana)
        await session.flush()
        assert huerfana.jurisdiccion_id is None

        await _fuente(session, JURISDICCION_PROVINCIAL)
        reparada = await crud.create_boletin(
            session,
            filename="20260604_2_Secc.pdf",
            date="20260604",
            section="2",
            file_hash="a" * 64,
        )

        assert reparada.id == huerfana.id
        assert reparada.jurisdiccion_id == JURISDICCION_PROVINCIAL

    @pytest.mark.asyncio
    async def test_no_pisa_una_jurisdiccion_ya_declarada(self, session):
        """Si la fila ya tiene jurisdicción, la derivada no la sobrescribe."""
        existente = Boletin(
            filename="20260604_2_Secc.pdf",
            date="20260604",
            section="2",
            status="completed",
            jurisdiccion_id=JURISDICCION_MUNICIPAL,
        )
        session.add(existente)
        await session.flush()

        await _fuente(session, JURISDICCION_PROVINCIAL)
        tocada = await crud.create_boletin(
            session, filename="20260604_2_Secc.pdf", date="20260604", section="2"
        )

        assert tocada.jurisdiccion_id == JURISDICCION_MUNICIPAL


class TestGetDefaultJurisdiccionId:
    @pytest.mark.asyncio
    async def test_sin_fuentes(self, session):
        assert await crud.get_default_jurisdiccion_id(session) is None

    @pytest.mark.asyncio
    async def test_una_fuente(self, session):
        await _fuente(session, JURISDICCION_PROVINCIAL)
        assert await crud.get_default_jurisdiccion_id(session) == JURISDICCION_PROVINCIAL

    @pytest.mark.asyncio
    async def test_dos_fuentes_misma_jurisdiccion_es_inequivoca(self, session):
        """Dos fuentes de la MISMA jurisdicción no son ambigüedad."""
        await _fuente(session, JURISDICCION_PROVINCIAL)
        await _fuente(session, JURISDICCION_PROVINCIAL)

        assert await crud.get_default_jurisdiccion_id(session) == JURISDICCION_PROVINCIAL

    @pytest.mark.asyncio
    async def test_dos_fuentes_distintas_es_ambigua(self, session):
        await _fuente(session, JURISDICCION_PROVINCIAL)
        await _fuente(session, JURISDICCION_MUNICIPAL)

        assert await crud.get_default_jurisdiccion_id(session) is None

    @pytest.mark.asyncio
    async def test_ignora_otros_tipos_de_fuente(self, session):
        """Una fuente de presupuesto no define la jurisdicción de un boletín."""
        session.add(
            FuenteDato(
                jurisdiccion_id=JURISDICCION_MUNICIPAL,
                tipo="presupuesto_anual",
                nombre="Presupuesto",
                activa=True,
            )
        )
        await session.flush()

        assert await crud.get_default_jurisdiccion_id(session) is None
