"""Tests for app/services/ejecucion_ledger.py (P.7.2).

The ledger is written when a boletín closes the pipeline, replacing the manual
ETL run.  These tests use a real async SQLite session so the SQLAlchemy queries
(joins, date ranges, deletes) are exercised rather than mocked.

Run from watcher-backend/:
    uv run pytest tests/tests/test_ejecucion_ledger.py -v
"""

import pytest
import pytest_asyncio
from app.db.models import Analisis, Base, Boletin, EjecucionPresupuestaria, PresupuestoBase
from app.services.ejecucion_ledger import upsert_boletin_ejecucion
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Same pliego re-published on consecutive days — the S-511 pattern that was 44%
# of the raw total in the 2026-09-13 cut.
PLIEGO = "Licitación Pública S-511/2026 - pavimento Las Peñas - Isletillas"
MONTO_PLIEGO = 25_341_000_000.0


@pytest_asyncio.fixture
async def session():
    """Real async SQLite session over the project's declarative metadata."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db

    await engine.dispose()


async def _add_boletin(db, boletin_id: int, date: str, section: str) -> Boletin:
    boletin = Boletin(
        id=boletin_id,
        filename=f"{date}_{section}_Secc.pdf",
        date=date,
        section=section,
        status="completed",
    )
    db.add(boletin)
    await db.flush()
    return boletin


async def _add_acto(db, **kwargs) -> Analisis:
    kwargs.setdefault("tipo_acto", "licitacion")
    kwargs.setdefault("riesgo", "bajo")
    acto = Analisis(**kwargs)
    db.add(acto)
    await db.flush()
    return acto


async def _ledger_rows(db, **filters):
    query = select(EjecucionPresupuestaria).order_by(EjecucionPresupuestaria.id)
    for column, value in filters.items():
        query = query.where(getattr(EjecucionPresupuestaria, column) == value)
    return (await db.execute(query)).scalars().all()


# ═══════════════════════════════════════════════════════════════════════════════
# Caso base: un boletín S4 produce filas canónicas
# ═══════════════════════════════════════════════════════════════════════════════

class TestBoletinS4:
    @pytest.mark.asyncio
    async def test_produce_filas_canonicas(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session,
            id=1,
            boletin_id=1,
            numero_acto="S-511/2026",
            organismo="ACIF",
            descripcion=PLIEGO,
            monto_numerico=MONTO_PLIEGO,
            is_gasto_publico=True,
            etapa_gasto="llamado",
            jurisdiccion_gasto="provincial",
        )

        result = await upsert_boletin_ejecucion(session, 1)

        assert result.rows_written == 1
        assert result.canonical == 1
        assert result.duplicates == 0

        rows = await _ledger_rows(session)
        assert len(rows) == 1
        assert rows[0].monto == MONTO_PLIEGO
        assert rows[0].etapa_gasto == "llamado"
        assert rows[0].jurisdiccion == "provincial"
        assert rows[0].analisis_id == 1
        assert rows[0].monto_acumulado_anual == MONTO_PLIEGO

    @pytest.mark.asyncio
    async def test_acto_sin_monto_no_entra(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session,
            id=1,
            boletin_id=1,
            organismo="ACIF",
            descripcion="Licitación sin monto declarado",
            monto_numerico=0.0,
            is_gasto_publico=True,
            etapa_gasto="llamado",
            jurisdiccion_gasto="provincial",
        )

        result = await upsert_boletin_ejecucion(session, 1)
        assert result.rows_written == 0

    @pytest.mark.asyncio
    async def test_boletin_inexistente_no_explota(self, session):
        result = await upsert_boletin_ejecucion(session, 999)
        assert result.rows_written == 0

    @pytest.mark.asyncio
    async def test_fecha_invalida_no_escribe(self, session):
        await _add_boletin(session, 1, "fecha-mala", "4")
        await _add_acto(
            session,
            id=1,
            boletin_id=1,
            organismo="ACIF",
            descripcion=PLIEGO,
            monto_numerico=MONTO_PLIEGO,
            is_gasto_publico=True,
            etapa_gasto="llamado",
        )
        result = await upsert_boletin_ejecucion(session, 1)
        assert result.rows_written == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Republicación del mismo pliego
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepublicacion:
    async def _seed_dos_dias(self, session):
        """El mismo pliego publicado el 1 y el 2 de septiembre."""
        await _add_boletin(session, 1, "20260901", "4")
        await _add_boletin(session, 2, "20260902", "4")
        for acto_id, boletin_id in ((1, 1), (2, 2)):
            await _add_acto(
                session,
                id=acto_id,
                boletin_id=boletin_id,
                numero_acto="S-511/2026",
                organismo="ACIF",
                descripcion=PLIEGO,
                monto_numerico=MONTO_PLIEGO,
                is_gasto_publico=True,
                etapa_gasto="llamado",
                jurisdiccion_gasto="provincial",
            )

    @pytest.mark.asyncio
    async def test_segunda_publicacion_marca_duplicado(self, session):
        await self._seed_dos_dias(session)

        primero = await upsert_boletin_ejecucion(session, 1)
        segundo = await upsert_boletin_ejecucion(session, 2)

        assert primero.duplicates == 0
        assert segundo.duplicates == 1
        assert segundo.canonical == 0

        rows = await _ledger_rows(session, boletin_id=2)
        assert rows[0].is_duplicate == 1

    @pytest.mark.asyncio
    async def test_duplicado_no_suma_al_acumulado(self, session):
        """El bug que P.7 corrige: S-511 × 8 = 44% del total bruto."""
        await self._seed_dos_dias(session)
        await upsert_boletin_ejecucion(session, 1)
        await upsert_boletin_ejecucion(session, 2)

        duplicado = (await _ledger_rows(session, boletin_id=2))[0]
        assert duplicado.monto_acumulado_anual == MONTO_PLIEGO  # no 2x

        total_canonico = await session.scalar(
            select(func.sum(EjecucionPresupuestaria.monto)).where(
                EjecucionPresupuestaria.is_duplicate == 0
            )
        )
        assert total_canonico == MONTO_PLIEGO

    @pytest.mark.asyncio
    async def test_distinto_pliego_no_es_duplicado(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_boletin(session, 2, "20260902", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="S-511/2026", organismo="ACIF",
            descripcion=PLIEGO, monto_numerico=MONTO_PLIEGO,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )
        await _add_acto(
            session, id=2, boletin_id=2, numero_acto="S-512/2026", organismo="ACIF",
            descripcion="Licitación Pública S-512/2026 - agua Serrano",
            monto_numerico=MONTO_PLIEGO,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        await upsert_boletin_ejecucion(session, 1)
        segundo = await upsert_boletin_ejecucion(session, 2)

        assert segundo.duplicates == 0
        assert (await _ledger_rows(session, boletin_id=2))[0].monto_acumulado_anual == (
            MONTO_PLIEGO * 2
        )

    @pytest.mark.asyncio
    async def test_sin_numero_acto_no_se_deduplica(self, session):
        """Sin identificador no se puede afirmar que sea el mismo acto."""
        await _add_boletin(session, 1, "20260901", "4")
        await _add_boletin(session, 2, "20260902", "4")
        for acto_id, boletin_id in ((1, 1), (2, 2)):
            await _add_acto(
                session, id=acto_id, boletin_id=boletin_id, numero_acto=None,
                organismo="ACIF", descripcion="Obra vial sin identificador",
                monto_numerico=1_000_000.0,
                is_gasto_publico=True, etapa_gasto="llamado",
                jurisdiccion_gasto="provincial",
            )

        await upsert_boletin_ejecucion(session, 1)
        segundo = await upsert_boletin_ejecucion(session, 2)
        assert segundo.duplicates == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Idempotencia
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdempotencia:
    @pytest.mark.asyncio
    async def test_rerun_reemplaza_en_lugar_de_duplicar(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="S-511/2026", organismo="ACIF",
            descripcion=PLIEGO, monto_numerico=MONTO_PLIEGO,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        await upsert_boletin_ejecucion(session, 1)
        await upsert_boletin_ejecucion(session, 1)
        await upsert_boletin_ejecucion(session, 1)

        rows = await _ledger_rows(session)
        assert len(rows) == 1
        assert rows[0].monto_acumulado_anual == MONTO_PLIEGO

    @pytest.mark.asyncio
    async def test_rerun_no_se_marca_duplicado_de_si_mismo(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="S-511/2026", organismo="ACIF",
            descripcion=PLIEGO, monto_numerico=MONTO_PLIEGO,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        await upsert_boletin_ejecucion(session, 1)
        segundo = await upsert_boletin_ejecucion(session, 1)
        assert segundo.duplicates == 0
        assert (await _ledger_rows(session))[0].is_duplicate == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Exclusión de no-gasto
# ═══════════════════════════════════════════════════════════════════════════════

class TestExclusiones:
    @pytest.mark.asyncio
    async def test_remate_no_entra_al_ledger(self, session):
        await _add_boletin(session, 1, "20260901", "2")
        await _add_acto(
            session, id=1, boletin_id=1, tipo_acto="otro", numero_acto="EXP 900",
            organismo="JUZGADO CIVIL", descripcion="Remate judicial de inmueble",
            monto_numerico=13_500_000_000.0,
            is_gasto_publico=False, etapa_gasto="no_aplica",
            jurisdiccion_gasto="fuera_presupuesto",
        )

        result = await upsert_boletin_ejecucion(session, 1)
        assert result.rows_written == 0
        assert result.skipped_no_gasto == 1
        assert await _ledger_rows(session) == []

    @pytest.mark.asyncio
    async def test_clasifica_actos_sin_flags(self, session):
        """Actos ingeridos antes de P.7.1 se clasifican al escribir el ledger."""
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session, id=1, boletin_id=1, tipo_acto="otro", numero_acto="ACTA 5",
            organismo="EL AGUANTE SA", descripcion="Aumento de capital social",
            monto_numerico=8_000_000_000.0,
        )
        await _add_acto(
            session, id=2, boletin_id=1, numero_acto="S-511/2026", organismo="ACIF",
            descripcion=PLIEGO, monto_numerico=MONTO_PLIEGO,
        )

        result = await upsert_boletin_ejecucion(session, 1)

        assert result.classified == 2
        assert result.skipped_no_gasto == 1
        assert result.rows_written == 1

        societario = await session.get(Analisis, 1)
        assert societario.is_gasto_publico is False
        assert societario.jurisdiccion_gasto == "fuera_presupuesto"

    @pytest.mark.asyncio
    async def test_recupera_numero_acto_faltante(self, session):
        """numero_acto null en todos los S4 del 1-sep; sin él no hay dedup."""
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto=None, organismo="ACIF",
            descripcion=PLIEGO, monto_numerico=MONTO_PLIEGO,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        await upsert_boletin_ejecucion(session, 1)

        acto = await session.get(Analisis, 1)
        assert acto.numero_acto == "S-511/2026"


# ═══════════════════════════════════════════════════════════════════════════════
# Acumuladores y match contra presupuesto
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcumuladores:
    @pytest.mark.asyncio
    async def test_acumula_por_organismo_y_periodo(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_boletin(session, 2, "20261001", "4")  # otro mes, mismo año
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="A-1", organismo="ACIF",
            descripcion="Licitación obra 1", monto_numerico=1_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )
        await _add_acto(
            session, id=2, boletin_id=2, numero_acto="A-2", organismo="ACIF",
            descripcion="Licitación obra 2", monto_numerico=3_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        await upsert_boletin_ejecucion(session, 1)
        await upsert_boletin_ejecucion(session, 2)

        octubre = (await _ledger_rows(session, boletin_id=2))[0]
        assert octubre.monto_acumulado_mes == 3_000_000.0      # solo octubre
        assert octubre.monto_acumulado_trimestre == 3_000_000.0  # Q4 vs Q3
        assert octubre.monto_acumulado_anual == 4_000_000.0     # ambos

    @pytest.mark.asyncio
    async def test_acumulado_no_incluye_gasto_posterior(self, session):
        """Reprocesar un boletín viejo no debe sumarle lo publicado después."""
        await _add_boletin(session, 1, "20260901", "4")
        await _add_boletin(session, 2, "20260902", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="A-1", organismo="ACIF",
            descripcion="Licitación obra 1", monto_numerico=1_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )
        await _add_acto(
            session, id=2, boletin_id=2, numero_acto="A-2", organismo="ACIF",
            descripcion="Licitación obra 2", monto_numerico=3_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        await upsert_boletin_ejecucion(session, 1)
        await upsert_boletin_ejecucion(session, 2)
        # Reprocesar el día 1 cuando el día 2 ya está en el ledger
        await upsert_boletin_ejecucion(session, 1)

        dia1 = (await _ledger_rows(session, boletin_id=1))[0]
        dia2 = (await _ledger_rows(session, boletin_id=2))[0]
        assert dia1.monto_acumulado_anual == 1_000_000.0
        assert dia2.monto_acumulado_anual == 4_000_000.0

    @pytest.mark.asyncio
    async def test_organismos_distintos_no_se_mezclan(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="A-1", organismo="ACIF",
            descripcion="Licitación obra", monto_numerico=1_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )
        await _add_acto(
            session, id=2, boletin_id=1, numero_acto="B-1", organismo="EPEC",
            descripcion="Licitación electrica", monto_numerico=5_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        await upsert_boletin_ejecucion(session, 1)

        rows = await _ledger_rows(session)
        por_org = {r.organismo: r.monto_acumulado_anual for r in rows}
        assert por_org == {"ACIF": 1_000_000.0, "EPEC": 5_000_000.0}

    @pytest.mark.asyncio
    async def test_match_contra_presupuesto_base(self, session):
        session.add(
            PresupuestoBase(
                id=1,
                ejercicio=2026,
                organismo="MINISTERIO DE SEGURIDAD",
                programa="10 - Programa Policia",
                partida_presupuestaria="3.1.0",
                monto_inicial=500_000_000.0,
                monto_vigente=500_000_000.0,
            )
        )
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="A-1",
            organismo="MINISTERIO DE SEGURIDAD",
            descripcion="Licitación de patrulleros", monto_numerico=1_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        result = await upsert_boletin_ejecucion(session, 1)

        assert result.matched_presupuesto == 1
        row = (await _ledger_rows(session))[0]
        assert row.presupuesto_base_id == 1
        assert row.programa == "10 - Programa Policia"
        assert row.partida_presupuestaria == "3.1.0"

    @pytest.mark.asyncio
    async def test_organismo_sin_match_queda_null(self, session):
        await _add_boletin(session, 1, "20260901", "4")
        await _add_acto(
            session, id=1, boletin_id=1, numero_acto="A-1", organismo="UNIDAD EJECUTORA",
            descripcion="Licitación de obra", monto_numerico=1_000_000.0,
            is_gasto_publico=True, etapa_gasto="llamado", jurisdiccion_gasto="provincial",
        )

        result = await upsert_boletin_ejecucion(session, 1)

        assert result.matched_presupuesto == 0
        assert (await _ledger_rows(session))[0].presupuesto_base_id is None
