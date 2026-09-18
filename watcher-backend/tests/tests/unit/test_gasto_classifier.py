"""Tests for app/services/gasto_classifier.py (P.7.1).

Covers the semantics table of the P.7 story: what counts as public spending,
at which stage, and against which jurisdiction.  Cases are drawn from the
2026-09-13 corpus cut, where the raw $458 mil M total turned out to be inflated
by re-publications, judicial auctions and corporate filings.

Run from watcher-backend/:
    uv run pytest tests/tests/unit/test_gasto_classifier.py -v
"""

import pytest
from app.services.gasto_classifier import (
    ETAPA_ADJUDICACION,
    ETAPA_CONTRATO,
    ETAPA_LLAMADO,
    ETAPA_MODIFICACION,
    ETAPA_NO_APLICA,
    ETAPA_PAGO,
    ETAPAS_GASTO,
    JURISDICCION_FUERA,
    JURISDICCION_MUNICIPAL,
    JURISDICCION_PROVINCIAL,
    _parse_section,
    classify_gasto,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Section parsing
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseSection:
    """`boletines.section` has several shapes in the wild; all must normalize."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1", 1),
            ("4", 4),
            ("5", 5),
            ("S1", 1),
            ("S4", 4),
            ("1_Secc", 1),
            ("4_Secc", 4),
            ("Seccion 2", 2),
            (3, 3),
        ],
    )
    def test_supported_shapes(self, raw, expected):
        assert _parse_section(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "sin numero", "9", 0, 7])
    def test_unparseable_is_none(self, raw):
        assert _parse_section(raw) is None


# ═══════════════════════════════════════════════════════════════════════════════
# Exclusiones — no son gasto público
# ═══════════════════════════════════════════════════════════════════════════════

class TestRemateJudicial:
    """S2: edictos y remates. $46,6 mil M en el corte, nada de gasto."""

    def test_remate_de_inmueble(self):
        result = classify_gasto(
            {
                "tipo_acto": "otro",
                "descripcion": "Remate judicial de inmueble en autos caratulados",
                "organismo": "JUZGADO CIVIL Y COMERCIAL",
            },
            section="2",
        )
        assert result.is_gasto_publico is False
        assert result.etapa_gasto == ETAPA_NO_APLICA
        assert result.jurisdiccion == JURISDICCION_FUERA

    def test_ejecucion_fiscal(self):
        result = classify_gasto(
            {
                "tipo_acto": "otro",
                "descripcion": "Ejecución fiscal contra el contribuyente",
                "organismo": "DIRECCION GENERAL DE RENTAS",
            },
            section="2",
        )
        assert result.is_gasto_publico is False

    def test_edicto_sin_seccion(self):
        """La exclusión no depende de la sección: vale por keyword."""
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Edicto de notificación"},
            section=None,
        )
        assert result.is_gasto_publico is False
        assert result.jurisdiccion == JURISDICCION_FUERA

    def test_martillero(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Subasta a cargo del martillero"},
            section="2",
        )
        assert result.is_gasto_publico is False

    def test_seccion_2_sin_keyword_sigue_excluida(self):
        """S2 es estructuralmente judicial, aunque el texto no diga remate."""
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Autos caratulados s/ cobro"},
            section="2",
        )
        assert result.is_gasto_publico is False
        assert result.jurisdiccion == JURISDICCION_FUERA


class TestActoSocietario:
    """S3: sociedades. $48,1 mil M de capital privado, no gasto público."""

    def test_aumento_de_capital(self):
        result = classify_gasto(
            {
                "tipo_acto": "otro",
                "descripcion": "Aumento de capital social por $500.000.000",
                "organismo": "EL AGUANTE S.A.",
            },
            section="3",
        )
        assert result.is_gasto_publico is False
        assert result.etapa_gasto == ETAPA_NO_APLICA
        assert result.jurisdiccion == JURISDICCION_FUERA

    def test_escision(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Escisión de la sociedad Buen Credit"},
            section="3",
        )
        assert result.is_gasto_publico is False

    def test_asamblea_extraordinaria(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Asamblea general extraordinaria"},
            section="3",
        )
        assert result.is_gasto_publico is False

    def test_seccion_3_sin_keyword_sigue_excluida(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Publicación art. 10 Ley 19.550"},
            section="3",
        )
        assert result.is_gasto_publico is False
        assert result.jurisdiccion == JURISDICCION_FUERA


class TestModificacionDePartidas:
    """Mueve el techo presupuestario; no paga. La Cumbre: $5.964 M × 4."""

    def test_compensacion_de_partidas(self):
        result = classify_gasto(
            {
                "tipo_acto": "decreto",
                "descripcion": "Compensación de partidas del ejercicio 2026",
                "organismo": "MINISTERIO DE ECONOMIA",
            },
            section="1",
        )
        assert result.is_gasto_publico is False
        assert result.etapa_gasto == ETAPA_MODIFICACION

    def test_incremento_de_partidas(self):
        result = classify_gasto(
            {"tipo_acto": "decreto", "descripcion": "Incremento de partidas presupuestarias"},
            section="1",
        )
        assert result.is_gasto_publico is False
        assert result.etapa_gasto == ETAPA_MODIFICACION

    def test_transferencia_de_partidas_no_es_pago(self):
        """'transferencia' sola sería pago; 'de partidas' la vuelve modificación."""
        result = classify_gasto(
            {
                "tipo_acto": "transferencia",
                "descripcion": "Transferencia de partidas entre programas",
            },
            section="1",
        )
        assert result.is_gasto_publico is False
        assert result.etapa_gasto == ETAPA_MODIFICACION

    def test_modificacion_conserva_jurisdiccion(self):
        result = classify_gasto(
            {"tipo_acto": "decreto", "descripcion": "Compensación de partidas municipales"},
            section="5",
        )
        assert result.etapa_gasto == ETAPA_MODIFICACION
        assert result.jurisdiccion == JURISDICCION_MUNICIPAL


class TestSinSenalDeGasto:
    """El default es excluir: el ledger es una afirmación sobre dinero público."""

    def test_designacion_sin_monto(self):
        result = classify_gasto(
            {"tipo_acto": "designacion", "descripcion": "Desígnase al Sr. X como director"},
            section="1",
        )
        assert result.is_gasto_publico is False
        assert result.etapa_gasto == ETAPA_NO_APLICA

    def test_texto_vacio(self):
        result = classify_gasto({}, section=None)
        assert result.is_gasto_publico is False
        assert result.etapa_gasto == ETAPA_NO_APLICA


# ═══════════════════════════════════════════════════════════════════════════════
# Gasto público — etapas
# ═══════════════════════════════════════════════════════════════════════════════

class TestLlamado:
    """S4: 65% del dinero del corte. Compromiso, no pago."""

    def test_licitacion_publica(self):
        result = classify_gasto(
            {
                "tipo_acto": "licitacion",
                "descripcion": "Licitación pública para pavimento Las Peñas - Isletillas",
                "organismo": "ACIF",
            },
            section="4",
        )
        assert result.is_gasto_publico is True
        assert result.etapa_gasto == ETAPA_LLAMADO
        assert result.jurisdiccion == JURISDICCION_PROVINCIAL

    def test_tipo_acto_licitacion_sin_keyword(self):
        result = classify_gasto(
            {"tipo_acto": "licitacion", "descripcion": "Provision de balizas"},
            section="4",
        )
        assert result.etapa_gasto == ETAPA_LLAMADO

    def test_compulsa_abreviada(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Compulsa abreviada para provision de alfalfa"},
            section="4",
        )
        assert result.is_gasto_publico is True
        assert result.etapa_gasto == ETAPA_LLAMADO

    def test_subasta_electronica_es_compra_no_remate(self):
        """'subasta electrónica' es un método de compra; no debe caer en judicial."""
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Subasta electrónica para adquirir insumos"},
            section="4",
        )
        assert result.is_gasto_publico is True
        assert result.etapa_gasto == ETAPA_LLAMADO

    def test_concurso_de_precios_no_es_concurso_preventivo(self):
        result = classify_gasto(
            {"tipo_acto": "otro", "descripcion": "Concurso de precios para mobiliario"},
            section="4",
        )
        assert result.etapa_gasto == ETAPA_LLAMADO

    def test_pliego_con_presupuesto_oficial(self):
        result = classify_gasto(
            {
                "tipo_acto": "otro",
                "descripcion": "Pliego de obra con presupuesto oficial de $2.114.469.923",
            },
            section="4",
        )
        assert result.etapa_gasto == ETAPA_LLAMADO


class TestAdjudicacionYContrato:
    def test_adjudicacion_gana_sobre_llamado(self):
        """Un acto que adjudica una licitación es adjudicación, no llamado."""
        result = classify_gasto(
            {
                "tipo_acto": "licitacion",
                "descripcion": "Adjudícase la Licitación Pública N° 12/2026 a Empresa ABC",
            },
            section="4",
        )
        assert result.etapa_gasto == ETAPA_ADJUDICACION
        assert result.is_gasto_publico is True

    def test_preadjudicacion(self):
        result = classify_gasto(
            {"tipo_acto": "resolucion", "descripcion": "Preadjudicación de la obra"},
            section="4",
        )
        assert result.etapa_gasto == ETAPA_ADJUDICACION

    @pytest.mark.parametrize(
        "descripcion",
        [
            "Adjudícase la obra a Empresa ABC",
            "Adjudicase la obra a Empresa ABC",
            "ADJUDÍCASE LA OBRA A EMPRESA ABC",
            "Se resuelve la adjudicación de la obra",
        ],
    )
    def test_acentos_y_mayusculas_no_afectan(self, descripcion):
        """La extracción de PDF pierde acentos de forma inconsistente."""
        result = classify_gasto(
            {"tipo_acto": "licitacion", "descripcion": descripcion}, section="4"
        )
        assert result.etapa_gasto == ETAPA_ADJUDICACION

    def test_contratacion_directa(self):
        result = classify_gasto(
            {"tipo_acto": "resolucion", "descripcion": "Contratación directa de servicios"},
            section="4",
        )
        assert result.etapa_gasto == ETAPA_CONTRATO

    def test_redeterminacion_de_precios(self):
        result = classify_gasto(
            {"tipo_acto": "resolucion", "descripcion": "Redeterminación de precios de la obra"},
            section="4",
        )
        assert result.etapa_gasto == ETAPA_CONTRATO


class TestPago:
    def test_tipo_acto_subsidio(self):
        result = classify_gasto(
            {"tipo_acto": "subsidio", "descripcion": "Otórgase apoyo economico"},
            section="1",
        )
        assert result.is_gasto_publico is True
        assert result.etapa_gasto == ETAPA_PAGO

    def test_tipo_acto_transferencia(self):
        result = classify_gasto(
            {"tipo_acto": "transferencia", "descripcion": "Fondos a la cooperativa"},
            section="1",
        )
        assert result.etapa_gasto == ETAPA_PAGO

    def test_orden_de_pago(self):
        result = classify_gasto(
            {"tipo_acto": "resolucion", "descripcion": "Orden de pago por servicios prestados"},
            section="1",
        )
        assert result.etapa_gasto == ETAPA_PAGO

    def test_aporte_no_reintegrable(self):
        result = classify_gasto(
            {"tipo_acto": "decreto", "descripcion": "Aporte no reintegrable a la fundación"},
            section="1",
        )
        assert result.etapa_gasto == ETAPA_PAGO


# ═══════════════════════════════════════════════════════════════════════════════
# Jurisdicción
# ═══════════════════════════════════════════════════════════════════════════════

class TestJurisdiccion:
    """S5 y comunas no se contrastan contra la Ley provincial 11.088."""

    def test_seccion_5_es_municipal(self):
        result = classify_gasto(
            {"tipo_acto": "licitacion", "descripcion": "Licitación de obra vial"},
            section="5",
        )
        assert result.jurisdiccion == JURISDICCION_MUNICIPAL
        assert result.is_gasto_publico is True
        assert result.cuenta_contra_presupuesto_provincial is False

    def test_municipalidad_por_organismo(self):
        result = classify_gasto(
            {
                "tipo_acto": "licitacion",
                "descripcion": "Licitación pública",
                "organismo": "MUNICIPALIDAD DE COSQUIN",
            },
            section="4",
        )
        assert result.jurisdiccion == JURISDICCION_MUNICIPAL

    def test_comuna_por_organismo(self):
        result = classify_gasto(
            {
                "tipo_acto": "licitacion",
                "descripcion": "Licitación de servicios",
                "organismo": "COMUNA DE VILLA CIUDAD PARQUE",
            },
            section="4",
        )
        assert result.jurisdiccion == JURISDICCION_MUNICIPAL

    def test_provincial_cuenta_contra_presupuesto(self):
        result = classify_gasto(
            {
                "tipo_acto": "licitacion",
                "descripcion": "Licitación pública de escuelas",
                "organismo": "ACIF",
            },
            section="4",
        )
        assert result.jurisdiccion == JURISDICCION_PROVINCIAL
        assert result.cuenta_contra_presupuesto_provincial is True


# ═══════════════════════════════════════════════════════════════════════════════
# Contrato de la API
# ═══════════════════════════════════════════════════════════════════════════════

class TestApiContract:
    def test_etapa_siempre_del_enum(self):
        casos = [
            ({"tipo_acto": "licitacion", "descripcion": "Licitación"}, "4"),
            ({"tipo_acto": "otro", "descripcion": "Remate"}, "2"),
            ({"tipo_acto": "otro", "descripcion": "Aumento de capital social"}, "3"),
            ({"tipo_acto": "decreto", "descripcion": "Compensación de partidas"}, "1"),
            ({"tipo_acto": "designacion", "descripcion": "Desígnase"}, "1"),
        ]
        for acto, section in casos:
            assert classify_gasto(acto, section=section).etapa_gasto in ETAPAS_GASTO

    def test_as_analisis_fields_mapea_al_modelo(self):
        result = classify_gasto(
            {"tipo_acto": "licitacion", "descripcion": "Licitación pública"}, section="4"
        )
        fields = result.as_analisis_fields()
        assert fields == {
            "is_gasto_publico": True,
            "etapa_gasto": ETAPA_LLAMADO,
            "jurisdiccion_gasto": JURISDICCION_PROVINCIAL,
        }

    def test_acepta_fila_de_analisis(self):
        """El clasificador corre tanto sobre el dict del LLM como sobre una fila."""
        fila = {
            "tipo_acto": "licitacion",
            "descripcion": None,
            "fragmento": "LICITACION PUBLICA N 12/2026 - Obra de pavimento",
            "organismo": "ACIF",
        }
        result = classify_gasto(fila, section="4")
        assert result.is_gasto_publico is True
        assert result.etapa_gasto == ETAPA_LLAMADO

    def test_motivo_no_vacio(self):
        result = classify_gasto({"tipo_acto": "otro", "descripcion": "Remate"}, section="2")
        assert result.motivo
