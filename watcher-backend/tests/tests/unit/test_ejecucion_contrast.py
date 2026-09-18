"""Unit tests for app.services.ejecucion_contrast (P.7.4)."""

from app.services.ejecucion_contrast import (
    BUCKET_COMPROMISO,
    BUCKET_EJECUCION,
    BUCKET_OTRO,
    aggregate_cobertura,
    aggregate_cobertura_temporal,
    aggregate_denominador_sin_dueno,
    aggregate_organismos,
    bucket_etapa,
    is_sobre,
    pct_vs_vigente,
    remap_organismo_key,
    vigente_por_organismo_canonico,
)
from app.services.presupuesto_matching import canonical_organismo_name


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


class TestVigentePorOrganismoCanonico:
    def test_poder_judicial_hyphen_merges_into_jurisdiction_ceiling(self):
        vigente, display = vigente_por_organismo_canonico(
            [
                ("PODER JUDICIAL", 11_163_852_000.0),
                ("PODER JUDICIAL -", 92_112_308_000.0),
            ]
        )
        assert len(vigente) == 1
        label = display["PODER JUDICIAL"]
        assert vigente[label] == 103_276_160_000.0
        assert not label.endswith("-")

        rows = [(label, "llamado", 18_188_665_592.0, 16)]
        items = aggregate_organismos(rows, vigente)
        assert items[0].pct_compromiso == 17.61
        assert items[0].sobre_compromiso is False

    def test_truncated_ministerio_de_stays_its_own_bucket(self):
        vigente, _ = vigente_por_organismo_canonico(
            [
                ("MINISTERIO DE", 290_000_000_000.0),
                ("MINISTERIO DE SEGURIDAD", 219_000_000_000.0),
            ]
        )
        assert len(vigente) == 2

    def test_garbled_economia_collapses_duplicate_token(self):
        vigente, display = vigente_por_organismo_canonico(
            [
                ("MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA", 23.0),
                ("MINISTERIO DE ECONOMÍA Y GESTIÓN PÚBLICA", 10.0),
            ]
        )
        assert len(vigente) == 1
        assert list(vigente.values())[0] == 33.0
        key = canonical_organismo_name(
            "MINISTERIO DE ECONOMÍA Y GESTIÓN PÚBLICA"
        )
        assert remap_organismo_key(
            "Ministerio de Economía y Gestión Pública", display
        ) == display[key]


class TestLlamadoDisclosure:
    """`llamado` stays inside the compromiso bucket but is reported apart.

    The published pct and the >100% alert keep their V.2 definition; separating
    the series must not silently retire an alert.
    """

    def test_llamado_is_reported_but_not_subtracted(self):
        rows = [
            ("EPEC", "llamado", 500.0, 3),
            ("EPEC", "contrato", 7.0, 1),
        ]
        item = aggregate_organismos(rows, {"EPEC": 1000.0})[0]
        assert item.monto_compromiso == 507.0
        assert item.monto_llamado == 500.0
        assert item.pct_compromiso == 50.7

    def test_pago_is_not_llamado(self):
        rows = [("EPEC", "pago", 42.0, 1)]
        item = aggregate_organismos(rows, {"EPEC": 1000.0})[0]
        assert item.monto_llamado == 0.0
        assert item.monto_ejecucion == 42.0

    def test_omitted_when_no_llamado_rows(self):
        rows = [("EPEC", "adjudicacion", 9.0, 1)]
        assert aggregate_organismos(rows, {"EPEC": 100.0})[0].monto_llamado == 0.0


class TestCobertura:
    def test_splits_matched_from_unmatched(self):
        items = aggregate_organismos(
            [
                ("CON DENOMINADOR", "llamado", 300.0, 2),
                ("SIN DENOMINADOR", "llamado", 100.0, 5),
            ],
            {"CON DENOMINADOR": 1000.0},
        )
        cob = aggregate_cobertura(items)
        assert cob.monto_total == 400.0
        assert cob.monto_con_denominador == 300.0
        assert cob.monto_sin_denominador == 100.0
        assert cob.count_sin_denominador == 5
        assert cob.pct_sin_denominador == 25.0

    def test_empty_contrast_is_zero_not_a_divide_by_zero(self):
        cob = aggregate_cobertura([])
        assert cob.monto_total == 0.0
        assert cob.pct_sin_denominador == 0.0

    def test_unmatched_spend_is_total_minus_matched(self):
        items = aggregate_organismos(
            [("A", "llamado", 250.0, 1), ("B", "pago", 750.0, 1)],
            {"A": 1.0},
        )
        cob = aggregate_cobertura(items)
        assert cob.monto_con_denominador + cob.monto_sin_denominador == cob.monto_total
        assert cob.pct_sin_denominador == 75.0


class TestCoberturaTemporal:
    """The period behind the numerator, so the pct stops implying a full year."""

    def _feb_abr(self):
        """Feb–Apr 2026 as stored: 3 months, one justified holiday pair."""
        rows = [("20260202", "completed", None)]
        rows += [("20260216", "failed", "justified: Carnaval 2026, HTTP 404")]
        rows += [("20260217", "failed", "justified: Carnaval 2026, HTTP 404")]
        rows += [(f"2026030{d}", "completed", None) for d in range(2, 6)]
        rows += [(f"2026040{d}", "completed", None) for d in range(2, 6)]
        return rows

    def test_counts_months_covered_against_the_year(self):
        cob = aggregate_cobertura_temporal(
            self._feb_abr(), 2026, "2026-02", "2026-04", mes_actual="2026-09"
        )
        assert cob.meses_cubiertos == 3
        assert cob.meses_del_ejercicio == 12
        assert cob.denominador_es_anual is True

    def test_overdue_months_are_separate_from_future_ones(self):
        cob = aggregate_cobertura_temporal(
            self._feb_abr(), 2026, "2026-02", "2026-04", mes_actual="2026-09"
        )
        assert cob.meses_vencidos_sin_ingesta == ("2026-01", "2026-05", "2026-06",
                                                 "2026-07", "2026-08", "2026-09")
        assert cob.meses_futuros == ("2026-10", "2026-11", "2026-12")

    def test_a_justified_holiday_is_not_a_missing_day(self):
        cob = aggregate_cobertura_temporal(
            self._feb_abr(), 2026, "2026-02", "2026-04", mes_actual="2026-09"
        )
        assert cob.dias_con_publicacion == 9
        assert cob.dias_justificados == 2
        assert cob.dias_faltantes == 0

    def test_an_unjustified_failure_is_a_missing_day(self):
        rows = [
            ("20260302", "completed", None),
            ("20260303", "failed", "HTTP 500"),
        ]
        cob = aggregate_cobertura_temporal(
            rows, 2026, "2026-03", "2026-03", mes_actual="2026-09"
        )
        assert cob.dias_faltantes == 1
        assert cob.dias_justificados == 0

    def test_no_partial_day_counts_as_published(self):
        # One section completing makes the day published, however many failed.
        rows = [
            ("20260302", "completed", None),
            ("20260302", "failed", "HTTP 500"),
        ]
        cob = aggregate_cobertura_temporal(
            rows, 2026, "2026-03", "2026-03", mes_actual="2026-09"
        )
        assert cob.dias_con_publicacion == 1
        assert cob.dias_faltantes == 0

    def test_empty_ledger_reports_no_period_rather_than_twelve_missing(self):
        # With no span there is nothing to split: claiming "all 12 months are
        # missing" would be a scarier and less useful statement than "no period".
        cob = aggregate_cobertura_temporal([], 2026, None, None, mes_actual="2026-09")
        assert cob.meses_cubiertos == 0
        assert cob.meses_vencidos_sin_ingesta == ()
        assert cob.meses_futuros == ()
        assert cob.dias_con_publicacion == 0


class TestDenominadorSinDueno:
    """The ceiling split into what can be a denominator and what cannot."""

    def _rows(self):
        return [
            ("MINISTERIO DE SALUD", 1_000_000.0),
            ("MINISTERIO DE SALUD", 500_000.0),
            ("MINISTERIO DE", 600_000.0),  # 12 rows, same stub
            ("MINISTERIO DE", 400_000.0),
            ("SECRETARÍA DE", 200_000.0),
            ("SECRETARIA DE", 100_000.0),  # same stub, no accent
            ("PODER JUDICIAL -", 300_000.0),  # messy but not truncated
        ]

    def test_splits_total_into_verifiable_and_unowned(self):
        d = aggregate_denominador_sin_dueno(self._rows())
        assert d.monto_total == 3_100_000.0
        assert d.monto_sin_dueno == 1_300_000.0
        assert d.monto_verificable == 1_800_000.0
        assert d.count_sin_dueno == 4
        assert d.pct_sin_dueno == 41.94

    def test_truncated_stubs_group_by_canonical_name(self):
        # SECRETARÍA DE / SECRETARIA DE are one stub. The display is the variant
        # that appears most often — here they tie, and the tie-breaks are length
        # then name, so the label does not depend on row order — and the amounts
        # add up either way.
        d = aggregate_denominador_sin_dueno(self._rows())
        by_name = {item.organismo: item for item in d.por_organismo}
        assert set(by_name) == {"MINISTERIO DE", "SECRETARIA DE"}
        assert by_name["MINISTERIO DE"].count == 2
        assert by_name["MINISTERIO DE"].monto_vigente == 1_000_000.0
        assert by_name["SECRETARIA DE"].monto_vigente == 300_000.0

    def test_items_are_ordered_by_monto(self):
        d = aggregate_denominador_sin_dueno(self._rows())
        montos = [item.monto_vigente for item in d.por_organismo]
        assert montos == sorted(montos, reverse=True)

    def test_a_messy_but_complete_name_is_not_unowned(self):
        # "PODER JUDICIAL -" is normalized, not lost: it keeps its denominator.
        d = aggregate_denominador_sin_dueno([("PODER JUDICIAL -", 300_000.0)])
        assert d.monto_sin_dueno == 0.0
        assert d.por_organismo == ()

    def test_empty_ceiling_does_not_divide_by_zero(self):
        d = aggregate_denominador_sin_dueno([])
        assert d.monto_total == 0.0
        assert d.pct_sin_dueno == 0.0
