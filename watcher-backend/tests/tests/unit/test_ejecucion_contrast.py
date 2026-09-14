"""Unit tests for app.services.ejecucion_contrast (P.7.4)."""

from app.services.ejecucion_contrast import (
    BUCKET_COMPROMISO,
    BUCKET_EJECUCION,
    BUCKET_OTRO,
    aggregate_organismos,
    bucket_etapa,
    is_sobre,
    pct_vs_vigente,
)


class TestBucketEtapa:
    def test_llamado_is_compromiso(self):
        assert bucket_etapa("llamado") == BUCKET_COMPROMISO

    def test_adjudicacion_is_compromiso(self):
        assert bucket_etapa("adjudicacion") == BUCKET_COMPROMISO

    def test_contrato_is_compromiso(self):
        assert bucket_etapa("contrato") == BUCKET_COMPROMISO

    def test_pago_is_ejecucion(self):
        assert bucket_etapa("pago") == BUCKET_EJECUCION

    def test_modificacion_is_otro(self):
        assert bucket_etapa("modificacion") == BUCKET_OTRO

    def test_none_is_otro(self):
        assert bucket_etapa(None) == BUCKET_OTRO


class TestPctVsVigente:
    def test_half(self):
        assert pct_vs_vigente(50, 100) == 50.0

    def test_over_one_hundred(self):
        assert pct_vs_vigente(250, 100) == 250.0

    def test_none_without_denominator(self):
        assert pct_vs_vigente(50, None) is None

    def test_none_when_vigente_zero(self):
        assert pct_vs_vigente(50, 0) is None

    def test_rounds_to_two_decimals(self):
        assert pct_vs_vigente(1, 3) == 33.33


class TestIsSobre:
    def test_over(self):
        assert is_sobre(100.01) is True

    def test_exact_hundred_is_not_over(self):
        assert is_sobre(100.0) is False

    def test_none_is_not_over(self):
        assert is_sobre(None) is False


class TestAggregateOrganismos:
    def test_splits_compromiso_and_ejecucion(self):
        rows = [
            ("EPEC", "llamado", 80.0, 2),
            ("EPEC", "pago", 10.0, 1),
        ]
        vigente = {"EPEC": 1000.0}
        items = aggregate_organismos(rows, vigente)
        assert len(items) == 1
        epec = items[0]
        assert epec.monto_compromiso == 80.0
        assert epec.monto_ejecucion == 10.0
        assert epec.monto_total == 90.0
        assert epec.count == 3
        assert epec.pct_compromiso == 8.0
        assert epec.pct_ejecucion == 1.0
        assert epec.sobre_compromiso is False
        assert epec.matched is True

    def test_unmatched_has_no_pct(self):
        rows = [("UNIDAD EJECUTORA", "llamado", 25.0, 1)]
        items = aggregate_organismos(rows, {})
        assert items[0].matched is False
        assert items[0].monto_vigente is None
        assert items[0].pct_compromiso is None
        assert items[0].sobre_compromiso is False

    def test_sobre_compromiso_alert(self):
        rows = [("MINISTERIO X", "llamado", 150.0, 1)]
        items = aggregate_organismos(rows, {"MINISTERIO X": 100.0})
        assert items[0].pct_compromiso == 150.0
        assert items[0].sobre_compromiso is True
        assert items[0].sobre_ejecucion is False

    def test_does_not_add_compromiso_into_ejecucion(self):
        rows = [
            ("ORG", "llamado", 90.0, 1),
            ("ORG", "pago", 10.0, 1),
        ]
        items = aggregate_organismos(rows, {"ORG": 100.0})
        # Mixing them would read as 100% executed; execution is 10%.
        assert items[0].pct_ejecucion == 10.0
        assert items[0].pct_compromiso == 90.0

    def test_sorts_by_compromiso_desc(self):
        rows = [
            ("SMALL", "llamado", 1.0, 1),
            ("BIG", "llamado", 99.0, 1),
        ]
        items = aggregate_organismos(rows, {})
        assert [i.organismo for i in items] == ["BIG", "SMALL"]

    def test_none_organismo_gets_placeholder(self):
        rows = [(None, "pago", 5.0, 1)]
        items = aggregate_organismos(rows, {})
        assert items[0].organismo == "(sin organismo)"
        assert items[0].monto_ejecucion == 5.0
