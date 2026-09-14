"""JSON money on presupuesto schemas is millions of ARS (P.7.4 UI)."""

from app.schemas.presupuesto import EjecucionResumenResponse, _money_millions


def test_money_millions_rounds_four_decimals():
    assert _money_millions(188_502_432_072.64) == 188502.4321


def test_resumen_json_does_not_emit_11_digit_ars():
    payload = EjecucionResumenResponse(
        total_canonical=82,
        total_duplicates=0,
        monto_canonical=188_502_432_072.64,
        monto_duplicates=12_345_678.0,
        monto_compromiso=188_273_970_882.64,
        monto_ejecucion=228_461_190.0,
        sobre_compromiso_count=0,
        por_organismo=[],
        por_mes=[],
    )
    data = payload.model_dump(mode="json")
    assert data["monto_canonical"] == 188502.4321
    encoded = payload.model_dump_json()
    assert "188502432072" not in encoded
    assert "188502.4321" in encoded
