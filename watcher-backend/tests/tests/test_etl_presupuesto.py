"""
Tests for:
  - scripts/etl_analisis_to_ejecucion.py  (pure functions + ETL integration)
  - scripts/parse_pdf_presupuesto_2026.py (pure functions)

Run from watcher-backend/:
    python -m pytest tests/tests/test_etl_presupuesto.py -v
"""

import json
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────────
_BACKEND = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "scripts"))

from etl_analisis_to_ejecucion import (
    _normalize,
    _token_jaccard,
    _normalize_acto,
    _dedup_key,
    build_presupuesto_index,
    match_organismo,
    parse_date,
    first_beneficiario,
    run_etl,
    DB_PATH,
)

from parse_pdf_presupuesto_2026 import (
    _parse_monto,
    _normalize_fin_fun_det,
    _clean_cell,
    _is_jurisdiction_header,
    _col_for_x,
    _words_to_rows,
)


# ═══════════════════════════════════════════════════════════════════════════════
# etl_analisis_to_ejecucion — unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalize:
    def test_strips_accents(self):
        assert _normalize("Córdoba") == "CORDOBA"

    def test_uppercase(self):
        assert _normalize("secretaría") == "SECRETARIA"

    def test_compresses_whitespace(self):
        assert _normalize("  a  b  ") == "A B"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_none_like(self):
        assert _normalize(None) == ""   # type: ignore[arg-type]

    def test_mixed(self):
        assert _normalize("  Ministerio De   Salud  ") == "MINISTERIO DE SALUD"


class TestTokenJaccard:
    def test_identical(self):
        assert _token_jaccard("A B C", "A B C") == 1.0

    def test_disjoint(self):
        assert _token_jaccard("A B", "C D") == 0.0

    def test_partial_overlap(self):
        # union={A,B,C,D}, intersection={B,C}
        score = _token_jaccard("A B C", "B C D")
        assert abs(score - 2 / 4) < 1e-6

    def test_empty_strings(self):
        assert _token_jaccard("", "A B") == 0.0
        assert _token_jaccard("A B", "") == 0.0


class TestParseDate:
    def test_valid(self):
        assert parse_date("20260201") == date(2026, 2, 1)

    def test_invalid_format(self):
        assert parse_date("2026-02-01") is None

    def test_invalid_values(self):
        assert parse_date("20261399") is None  # month 13

    def test_empty(self):
        assert parse_date("") is None

    def test_none(self):
        assert parse_date(None) is None   # type: ignore[arg-type]


class TestFirstBeneficiario:
    def test_list_json(self):
        row = {"beneficiarios_json": ["Empresa XYZ", "Persona ABC"], "entidad_beneficiaria": None}
        assert first_beneficiario(row) == "Empresa XYZ"

    def test_encoded_json_string(self):
        row = {"beneficiarios_json": json.dumps(["Empresa XYZ"]), "entidad_beneficiaria": None}
        assert first_beneficiario(row) == "Empresa XYZ"

    def test_fallback_entidad(self):
        row = {"beneficiarios_json": None, "entidad_beneficiaria": "Empresa Fallback"}
        assert first_beneficiario(row) == "Empresa Fallback"

    def test_empty_list(self):
        row = {"beneficiarios_json": [], "entidad_beneficiaria": "Fallback"}
        assert first_beneficiario(row) == "Fallback"

    def test_all_none(self):
        row = {"beneficiarios_json": None, "entidad_beneficiaria": None}
        assert first_beneficiario(row) is None

    def test_truncates_at_200(self):
        row = {"beneficiarios_json": ["X" * 300], "entidad_beneficiaria": None}
        result = first_beneficiario(row)
        assert result is not None and len(result) == 200


class TestMatchOrganismo:
    """Tests for match_organismo with a minimal pb_index."""

    def _make_index(self, entries):
        """entries: list of (pb_id, org_raw, programa, partida)"""
        pb_index = [(pid, _normalize(org), prog, part) for pid, org, prog, part in entries]
        pb_exact = {pb_norm: (pid, prog, part) for pid, pb_norm, prog, part in pb_index}
        return pb_index, pb_exact

    def test_exact_match(self):
        pb_index, pb_exact = self._make_index([(1, "Ministerio de Salud", "P1", None)])
        pb_id, score, method, prog, _ = match_organismo(
            _normalize("Ministerio de Salud"), pb_index, pb_exact
        )
        assert pb_id == 1
        assert score == 1.0
        assert method == "exact"

    def test_substring_match(self):
        pb_index, pb_exact = self._make_index([(2, "Secretaria de Salud Provincial", "P2", None)])
        pb_id, score, method, _, _ = match_organismo(
            _normalize("Secretaria de Salud"), pb_index, pb_exact
        )
        assert pb_id == 2
        assert method == "substring"
        assert 0.4 <= score < 1.0

    def test_jaccard_match(self):
        pb_index, pb_exact = self._make_index([(3, "Direccion General de Rentas Ministerio", "P3", "1.3.0")])
        pb_id, score, method, _, partida = match_organismo(
            _normalize("Direccion General de Rentas de la Provincia"),
            pb_index, pb_exact
        )
        assert pb_id == 3
        assert method == "jaccard"
        assert partida == "1.3.0"

    def test_no_match_below_threshold(self):
        pb_index, pb_exact = self._make_index([(4, "Ministerio de Ambiente", "P4", None)])
        pb_id, score, method, _, _ = match_organismo(
            _normalize("Poder Judicial de Córdoba"), pb_index, pb_exact
        )
        assert pb_id is None

    def test_blocklist_unidad_ejecutora(self):
        pb_index, pb_exact = self._make_index([(5, "Unidad Ejecutora Para El Saneamiento", "P5", None)])
        pb_id, *_ = match_organismo("UNIDAD EJECUTORA", pb_index, pb_exact)
        assert pb_id is None

    def test_blocklist_na(self):
        pb_index, pb_exact = self._make_index([(6, "N/A Servicios", "P6", None)])
        pb_id, *_ = match_organismo("N/A", pb_index, pb_exact)
        assert pb_id is None

    def test_empty_org(self):
        pb_index, pb_exact = self._make_index([(7, "Ministerio de Salud", "P7", None)])
        pb_id, *_ = match_organismo("", pb_index, pb_exact)
        assert pb_id is None


# ═══════════════════════════════════════════════════════════════════════════════
# parse_pdf_presupuesto_2026 — unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseMonto:
    def test_dot_thousands_no_decimal(self):
        assert _parse_monto("6.831.523.000") == 6_831_523_000.0

    def test_dot_thousands_comma_decimal(self):
        assert _parse_monto("1.234.567,89") == 1_234_567.89

    def test_plain_integer(self):
        assert _parse_monto("1000000") == 1_000_000.0

    def test_currency_symbol(self):
        assert _parse_monto("$1.500.000") == 1_500_000.0

    def test_empty(self):
        assert _parse_monto("") == 0.0

    def test_none(self):
        assert _parse_monto(None) == 0.0

    def test_non_numeric(self):
        assert _parse_monto("N/A") == 0.0


class TestNormalizeFinFunDet:
    def test_spaces_to_dots(self):
        assert _normalize_fin_fun_det("1 6 0") == "1.6.0"

    def test_already_dotted(self):
        assert _normalize_fin_fun_det("2.3.1") == "2.3.1"

    def test_empty(self):
        assert _normalize_fin_fun_det("") == ""

    def test_single_digit(self):
        assert _normalize_fin_fun_det("5") == "5"


class TestCleanCell:
    def test_collapses_spaces(self):
        assert _clean_cell("  hello   world  ") == "hello world"

    def test_none(self):
        assert _clean_cell(None) == ""

    def test_number(self):
        assert _clean_cell(42) == "42"


class TestIsJurisdictionHeader:
    def test_valid(self):
        assert _is_jurisdiction_header("1.09 - Ministerio De Ambiente Y Economía Circular")
        assert _is_jurisdiction_header("2.01 – Secretaría de Gobierno")

    def test_invalid(self):
        assert not _is_jurisdiction_header("ACTIVIDADES CENTRALES")
        assert not _is_jurisdiction_header("TOTAL")
        assert not _is_jurisdiction_header("")


class TestColForX:
    def test_codigo_range(self):
        assert _col_for_x(0.0) == "codigo"
        assert _col_for_x(50.0) == "codigo"
        assert _col_for_x(92.9) == "codigo"

    def test_denominacion_range(self):
        assert _col_for_x(93.0) == "denominacion"
        assert _col_for_x(150.0) == "denominacion"

    def test_naturaleza_range(self):
        assert _col_for_x(215.0) == "naturaleza"
        assert _col_for_x(217.5) == "naturaleza"  # SUBPROGRAMA x0

    def test_monto_range(self):
        assert _col_for_x(800.0) == "monto"
        assert _col_for_x(9000.0) == "monto"


class TestWordsToRows:
    """Tests for _words_to_rows grouping logic."""

    def _word(self, text, x0, top):
        return {"text": text, "x0": x0, "top": top, "x1": x0 + 10, "bottom": top + 10}

    def test_single_row(self):
        words = [
            self._word("PROGRAMA", 220, 150),
            self._word("100", 10, 150),
            self._word("SALUD", 95, 150),
        ]
        rows = _words_to_rows(words)
        assert len(rows) == 1
        assert "naturaleza" in rows[0]
        assert rows[0]["naturaleza"] == "PROGRAMA"

    def test_two_rows_separated(self):
        words = [
            self._word("PROGRAMA", 220, 150),
            self._word("SUBPROGRAMA", 220, 175),  # >14px apart
        ]
        rows = _words_to_rows(words)
        assert len(rows) == 2

    def test_header_words_filtered(self):
        words = [
            self._word("HEADER", 220, 50),   # top < _TABLE_TOP_MIN (115)
            self._word("DATA", 220, 150),
        ]
        rows = _words_to_rows(words)
        assert len(rows) == 1
        assert rows[0].get("naturaleza") == "DATA"

    def test_multiword_cell_joined(self):
        words = [
            self._word("ACTIVIDADES", 220, 150),
            self._word("CENTRALES", 280, 151),  # same row, same column
        ]
        rows = _words_to_rows(words)
        assert len(rows) == 1
        assert "ACTIVIDADES CENTRALES" in rows[0].get("naturaleza", "")


# ═══════════════════════════════════════════════════════════════════════════════
# ETL integration test (in-memory SQLite)
# ═══════════════════════════════════════════════════════════════════════════════

def _setup_test_db(path: str):
    """Create minimal schema + seed data for ETL integration test."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE boletines (
            id INTEGER PRIMARY KEY,
            date TEXT,
            filename TEXT,
            section TEXT,
            status TEXT,
            fuente TEXT DEFAULT 'provincial',
            origin TEXT DEFAULT 'downloaded'
        );

        CREATE TABLE presupuesto_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ejercicio INTEGER,
            organismo TEXT,
            programa TEXT,
            subprograma TEXT,
            partida_presupuestaria TEXT,
            descripcion TEXT,
            monto_inicial REAL,
            monto_vigente REAL,
            fecha_aprobacion TEXT,
            fuente_financiamiento TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE analisis (
            id INTEGER PRIMARY KEY,
            boletin_id INTEGER,
            tipo_acto TEXT,
            numero_acto TEXT,
            organismo TEXT,
            descripcion TEXT,
            fragmento TEXT,
            monto_numerico REAL,
            categoria TEXT,
            riesgo TEXT,
            beneficiarios_json TEXT,
            entidad_beneficiaria TEXT,
            motivo_riesgo TEXT
        );

        CREATE TABLE ejecucion_presupuestaria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boletin_id INTEGER,
            presupuesto_base_id INTEGER,
            fecha_boletin TEXT,
            organismo TEXT,
            beneficiario TEXT,
            concepto TEXT,
            monto REAL,
            tipo_operacion TEXT,
            partida_presupuestaria TEXT,
            programa TEXT,
            subprograma TEXT,
            categoria_watcher TEXT,
            riesgo_watcher TEXT,
            monto_acumulado_mes REAL,
            monto_acumulado_trimestre REAL,
            monto_acumulado_anual REAL,
            es_modificacion_presupuestaria INTEGER DEFAULT 0,
            requiere_revision INTEGER DEFAULT 0,
            observaciones TEXT,
            is_duplicate INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        );

        -- seed data
        INSERT INTO boletines VALUES (1, '20260201', 'b1.pdf', 'S1', 'completed', 'provincial', 'downloaded');
        INSERT INTO boletines VALUES (2, '20260215', 'b2.pdf', 'S4', 'completed', 'provincial', 'downloaded');
        INSERT INTO boletines VALUES (3, '20260202', 'b3.pdf', 'S1', 'completed', 'provincial', 'downloaded');

        INSERT INTO presupuesto_base VALUES (
            1, 2026, 'MINISTERIO DE SEGURIDAD', '10 - Programa Policia', NULL,
            '3.1.0', 'Ministerio de Seguridad - Policia', 500000000, 500000000,
            '2026-01-01', 'Rentas Generales', '2026-01-01', '2026-01-01'
        );

        INSERT INTO analisis VALUES
            (1, 1, 'licitacion', 'RES 001', 'MINISTERIO DE SEGURIDAD',
             'Compra de patrulleros', 'frag1', 5000000.0, 'gasto', 'bajo',
             '["Empresa ABC"]', NULL, NULL),
            (2, 2, 'subsidio', 'DEC 002', 'MUNICIPALIDAD DE CORDOBA',
             'Subsidio transporte', 'frag2', 1000000.0, 'subsidio', 'medio',
             NULL, 'Municipalidad Córdoba', 'Monto elevado'),
            (3, 1, 'resolucion', 'RES 003', NULL,
             'Acto sin organismo', 'frag3', 2000000.0, 'otro', 'informativo',
             NULL, NULL, NULL),
            -- duplicate of analisis_id=1: same org + acto + monto, published day after
            (4, 3, 'licitacion', 'RES 001', 'MINISTERIO DE SEGURIDAD',
             'Compra de patrulleros (republica)', 'frag4', 5000000.0, 'gasto', 'bajo',
             '["Empresa ABC"]', NULL, NULL);
    """)
    conn.commit()
    conn.close()


class TestETLIntegration:
    """Integration tests for run_etl() against an in-memory test DB."""

    @pytest.fixture(autouse=True)
    def tmp_db(self, tmp_path, monkeypatch):
        """Patch DB_PATH to use a temp DB and populate it with test data."""
        db_file = str(tmp_path / "test.db")
        _setup_test_db(db_file)
        monkeypatch.setattr("etl_analisis_to_ejecucion.DB_PATH", Path(db_file))
        self.db_path = db_file

    def _query(self, sql):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def test_dry_run_does_not_insert(self):
        run_etl(dry_run=True)
        rows = self._query("SELECT COUNT(*) as n FROM ejecucion_presupuestaria")
        assert rows[0]["n"] == 0

    def test_inserts_rows_with_montos(self):
        run_etl(dry_run=False)
        rows = self._query("SELECT * FROM ejecucion_presupuestaria ORDER BY id")
        assert len(rows) == 4  # 3 original + 1 duplicate seed row

    def test_organismo_matched_to_presupuesto_base(self):
        run_etl(dry_run=False)
        matched = self._query(
            "SELECT * FROM ejecucion_presupuestaria "
            "WHERE organismo = 'MINISTERIO DE SEGURIDAD' AND is_duplicate = 0"
        )
        assert len(matched) == 1
        assert matched[0]["presupuesto_base_id"] == 1

    def test_unmatched_organismo_has_null_pb(self):
        run_etl(dry_run=False)
        rows = self._query(
            "SELECT * FROM ejecucion_presupuestaria WHERE organismo = 'MUNICIPALIDAD DE CORDOBA'"
        )
        assert len(rows) == 1
        assert rows[0]["presupuesto_base_id"] is None

    def test_null_organismo_row_is_inserted(self):
        run_etl(dry_run=False)
        rows = self._query(
            "SELECT * FROM ejecucion_presupuestaria WHERE organismo IS NULL OR organismo = ''"
        )
        assert len(rows) == 1
        assert rows[0]["presupuesto_base_id"] is None

    def test_medio_riesgo_sets_requiere_revision(self):
        run_etl(dry_run=False)
        rows = self._query(
            "SELECT requiere_revision FROM ejecucion_presupuestaria WHERE riesgo_watcher = 'medio'"
        )
        assert len(rows) == 1
        assert rows[0]["requiere_revision"] == 1

    def test_bajo_riesgo_does_not_require_revision(self):
        run_etl(dry_run=False)
        rows = self._query(
            "SELECT requiere_revision FROM ejecucion_presupuestaria WHERE riesgo_watcher = 'bajo'"
        )
        # Both canonical and duplicate analisis_id=1/4 have riesgo=bajo → 2 rows
        assert len(rows) == 2
        assert all(r["requiere_revision"] == 0 for r in rows)

    def test_accumulated_monthly_total(self):
        run_etl(dry_run=False)
        # Both analisis_id 1 and 3 are in boletin 1 (2026-02-01)
        # analisis_id 1: MINISTERIO DE SEGURIDAD, 5M
        # analisis_id 3: org=None, 2M  → different org_norm
        rows = self._query(
            "SELECT monto_acumulado_mes, organismo FROM ejecucion_presupuestaria "
            "WHERE organismo = 'MINISTERIO DE SEGURIDAD'"
        )
        assert rows[0]["monto_acumulado_mes"] == 5_000_000.0

    def test_idempotent_rerun(self):
        run_etl(dry_run=False)
        run_etl(dry_run=False)
        rows = self._query("SELECT COUNT(*) as n FROM ejecucion_presupuestaria")
        assert rows[0]["n"] == 4  # second run clears and re-inserts same 4 rows

    def test_monto_stored_correctly(self):
        run_etl(dry_run=False)
        rows = self._query("SELECT monto FROM ejecucion_presupuestaria ORDER BY monto DESC")
        assert rows[0]["monto"] == 5_000_000.0
        assert rows[1]["monto"] == 5_000_000.0  # duplicate row stored but flagged
        assert rows[2]["monto"] == 2_000_000.0
        assert rows[3]["monto"] == 1_000_000.0

    def test_duplicate_row_is_flagged(self):
        run_etl(dry_run=False)
        # analisis_id=4 is a re-publication of analisis_id=1 (same org+acto+monto)
        rows = self._query(
            "SELECT is_duplicate FROM ejecucion_presupuestaria "
            "ORDER BY fecha_boletin, id"
        )
        # Row 1 (2026-02-01, canonical), Row 3 (2026-02-01, different acto),
        # Row 4 (2026-02-02, duplicate), Row 2 (2026-02-15, canonical)
        is_dup_values = [r["is_duplicate"] for r in rows]
        assert is_dup_values.count(1) == 1   # exactly one duplicate
        assert is_dup_values.count(0) == 3   # three canonical rows

    def test_duplicate_excluded_from_accumulator(self):
        run_etl(dry_run=False)
        # Only the canonical RES 001 (2026-02-01) should be in the monthly accumulator
        # for MINISTERIO DE SEGURIDAD. The duplicate (2026-02-02) must not add 5M again.
        rows = self._query(
            "SELECT monto_acumulado_mes, is_duplicate FROM ejecucion_presupuestaria "
            "WHERE organismo = 'MINISTERIO DE SEGURIDAD' ORDER BY fecha_boletin, id"
        )
        assert len(rows) == 2
        canonical = next(r for r in rows if r["is_duplicate"] == 0)
        duplicate = next(r for r in rows if r["is_duplicate"] == 1)
        assert canonical["monto_acumulado_mes"] == 5_000_000.0
        # Duplicate row carries its snapshot of the accumulator at insertion time
        # (still 5M — accumulator was NOT incremented again)
        assert duplicate["monto_acumulado_mes"] == 5_000_000.0

    def test_canonical_row_not_flagged(self):
        run_etl(dry_run=False)
        rows = self._query(
            "SELECT is_duplicate FROM ejecucion_presupuestaria "
            "WHERE organismo = 'MUNICIPALIDAD DE CORDOBA'"
        )
        assert len(rows) == 1
        assert rows[0]["is_duplicate"] == 0

    def test_total_rows_includes_duplicates(self):
        run_etl(dry_run=False)
        # All 4 analisis rows (including the duplicate) should be stored
        rows = self._query("SELECT COUNT(*) as n FROM ejecucion_presupuestaria")
        assert rows[0]["n"] == 4


# ═══════════════════════════════════════════════════════════════════════════════
# _normalize_acto and _dedup_key — unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizeActo:
    def test_strips_whitespace(self):
        assert _normalize_acto("RES 001") == "RES001"

    def test_uppercases(self):
        assert _normalize_acto("res 001") == "RES001"

    def test_none_returns_none(self):
        assert _normalize_acto(None) is None

    def test_empty_returns_none(self):
        assert _normalize_acto("") is None
        assert _normalize_acto("   ") is None

    def test_na_returns_none(self):
        assert _normalize_acto("N/A") is None
        assert _normalize_acto("NA") is None

    def test_no_especificado_returns_none(self):
        assert _normalize_acto("NO ESPECIFICADO") is None
        assert _normalize_acto("SIN NUMERO") is None

    def test_valid_acto_number(self):
        assert _normalize_acto("DECRETO 056/2026") == "DECRETO056/2026"


class TestDedupKey:
    def test_same_inputs_same_key(self):
        k1 = _dedup_key("EPEC", 5_000_000.0, "RES001")
        k2 = _dedup_key("EPEC", 5_000_000.0, "RES001")
        assert k1 == k2

    def test_monto_rounded_to_1m(self):
        # 5.1M and 5.4M both round to 5 (below the .5 threshold)
        k1 = _dedup_key("EPEC", 5_100_000.0, "RES001")
        k2 = _dedup_key("EPEC", 5_400_000.0, "RES001")
        assert k1 == k2

    def test_different_org_different_key(self):
        k1 = _dedup_key("EPEC", 5_000_000.0, "RES001")
        k2 = _dedup_key("MINISTERIO", 5_000_000.0, "RES001")
        assert k1 != k2

    def test_none_acto_included_in_key(self):
        k1 = _dedup_key("EPEC", 5_000_000.0, None)
        k2 = _dedup_key("EPEC", 5_000_000.0, None)
        assert k1 == k2  # keys are equal, but ETL won't add None-acto rows to seen_set
