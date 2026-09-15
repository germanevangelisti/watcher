"""Unit tests for app.services.cge_trimestral (V.1.5)."""

from app.services.cge_trimestral import (
    aggregate_cge_rows,
    magnitude_note,
    pick_targets,
)


class TestAggregate:
    def test_sums_jurisdiccion_and_unidad(self):
        rows = [
            {
                "JURISDICCION": "805 - Empresa Provincial De Energía De Córdoba (Epec)",
                "UNIDAD ADMINISTRATIVA": "EPEC Casa Central",
                "PRESUPUESTO VIGENTE": "100",
                "DEVENGADO": "40",
                "PAGADO": "10",
            },
            {
                "JURISDICCION": "805 - Empresa Provincial De Energía De Córdoba (Epec)",
                "UNIDAD ADMINISTRATIVA": "EPEC Casa Central",
                "PRESUPUESTO VIGENTE": "50",
                "DEVENGADO": "20",
                "PAGADO": "5",
            },
        ]
        totals = aggregate_cge_rows(rows, source="emaee")
        epec = totals[
            "jurisdiccion:805 - Empresa Provincial De Energía De Córdoba (Epec)"
        ]
        assert epec.vigente == 150
        assert epec.devengado == 60
        assert epec.pagado == 15
        assert epec.n_rows == 2


class TestPickTargets:
    def test_resolves_eight_slots_even_when_missing(self):
        rows = [
            {
                "JURISDICCION": "300 - Poder Judicial",
                "UNIDAD ADMINISTRATIVA": "Tribunal",
                "PRESUPUESTO VIGENTE": "10",
                "COMPROMISO": "3",
                "DEVENGADO": "2",
                "PAGADO": "1",
            },
            {
                "JURISDICCION": "175 - Ministerio De Seguridad",
                "UNIDAD ADMINISTRATIVA": "199 - Policia De La Provincia",
                "PRESUPUESTO VIGENTE": "8",
                "COMPROMISO": "2",
                "DEVENGADO": "1",
                "PAGADO": "1",
            },
        ]
        picked = pick_targets(aggregate_cge_rows(rows))
        assert len(picked) == 8
        by_label = {item.label: item for item in picked}
        assert by_label["Poder Judicial"].devengado == 2.0
        assert by_label["Policía de la Provincia"].vigente == 8
        assert by_label["EPEC"].n_rows == 0
        assert by_label["Dirección de Ministerio / Inteligencia Fiscal"].n_rows == 0


class TestMagnitude:
    def test_floor_of_notices(self):
        note = magnitude_note(ledger=1_000, cge=100_000)
        assert "suelo de avisos" in note

    def test_empty_cge(self):
        note = magnitude_note(ledger=10, cge=0)
        assert "no publica" in note
