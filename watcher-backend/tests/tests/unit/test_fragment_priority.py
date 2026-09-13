"""Priority selection for local GPU/CPU caps on bulletin fragments."""

from app.core.fragment_priority import fragment_priority_score, select_prioritized


def test_high_signal_beats_edicto():
    assert fragment_priority_score("Licitación pública por $10.000.000") > fragment_priority_score(
        "EDICTO: se hace saber el remate judicial"
    )


def test_select_keeps_first_and_high_signal():
    items = [
        "sumario del boletin",
        "edicto de notificación",
        "Decreto N 123 contratación directa",
        "se hace saber remate judicial",
        "Licitación pública presupuesto $500.000.000",
    ]
    chosen = select_prioritized(items, 3, lambda t: t)
    assert chosen[0] == items[0]
    assert "Decreto" in " ".join(chosen)
    assert "Licitación" in " ".join(chosen)
    assert len(chosen) == 3


def test_select_noop_when_under_limit():
    items = ["a", "b"]
    assert select_prioritized(items, 8, lambda t: t) == items
