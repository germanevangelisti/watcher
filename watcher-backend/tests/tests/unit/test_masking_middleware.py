"""
Unit tests for CUITMaskingMiddleware.

Tests validate:
- CUIT regex matches correctly formatted and unformatted CUITs
- mask_cuit() replaces all variants
- mask_value() recurses through dicts and lists
- CUITs in text are not over-masked (non-CUIT numbers untouched)
"""

from __future__ import annotations

from app.middleware.masking import CUIT_MASK, CUIT_RE, mask_cuit, mask_value


class TestCUITRegex:
    def test_matches_hyphenated_cuit(self):
        assert CUIT_RE.search("20-12345678-9") is not None

    def test_matches_unhyphenated_cuit(self):
        assert CUIT_RE.search("20123456789") is not None

    def test_matches_partially_hyphenated(self):
        assert CUIT_RE.search("20-123456789") is not None

    def test_does_not_match_short_number(self):
        assert CUIT_RE.search("12345") is None

    def test_does_not_match_12_digit_number(self):
        # 12 digits is not a valid CUIT (needs exactly 11)
        assert CUIT_RE.search("123456789012") is None

    def test_matches_cuit_within_text(self):
        text = "El contribuyente 20-12345678-9 presentó declaración"
        assert CUIT_RE.search(text) is not None


class TestMaskCuit:
    def test_replaces_hyphenated_cuit(self):
        result = mask_cuit("CUIT: 20-12345678-9 del contribuyente")
        assert "20-12345678-9" not in result
        assert CUIT_MASK in result

    def test_replaces_unhyphenated_cuit(self):
        result = mask_cuit("id=20123456789")
        assert "20123456789" not in result
        assert CUIT_MASK in result

    def test_replaces_multiple_cuits(self):
        text = "CUITs: 20-12345678-9 y 27-87654321-3"
        result = mask_cuit(text)
        assert result.count(CUIT_MASK) == 2

    def test_does_not_alter_non_cuit_text(self):
        text = "Resolución N° 1234 del 15/01/2026"
        assert mask_cuit(text) == text

    def test_empty_string_returns_empty(self):
        assert mask_cuit("") == ""


class TestMaskValue:
    def test_masks_string(self):
        result = mask_value("CUIT 20-12345678-9")
        assert CUIT_MASK in result

    def test_recurses_into_dict(self):
        data = {"cuit": "20-12345678-9", "nombre": "Juan"}
        result = mask_value(data)
        assert CUIT_MASK in result["cuit"]
        assert result["nombre"] == "Juan"

    def test_recurses_into_list(self):
        data = ["20-12345678-9", "texto sin CUIT"]
        result = mask_value(data)
        assert CUIT_MASK in result[0]
        assert result[1] == "texto sin CUIT"

    def test_nested_dict_in_list(self):
        data = [{"cuit": "20-12345678-9", "valor": 100}]
        result = mask_value(data)
        assert CUIT_MASK in result[0]["cuit"]
        assert result[0]["valor"] == 100

    def test_non_string_non_container_passthrough(self):
        assert mask_value(42) == 42
        assert mask_value(3.14) == 3.14
        assert mask_value(None) is None
        assert mask_value(True) is True

    def test_deeply_nested(self):
        data = {"level1": {"level2": {"cuit": "27-87654321-3"}}}
        result = mask_value(data)
        assert CUIT_MASK in result["level1"]["level2"]["cuit"]


# ═══════════════════════════════════════════════════════════════════════════════
# El middleware sobre un cuerpo real
# ═══════════════════════════════════════════════════════════════════════════════
#
# Faltaba: los tests de arriba cubren las funciones puras, así que nada probaba
# el camino que corre en producción. Lo que se rompió fue justamente ése — el
# middleware regexeaba el texto serializado, así que un `monto` de 11 dígitos en
# pesos matcheaba el patrón de CUIT y se reemplazaba por la máscara sin comillas,
# dejando la respuesta sin parsear para cualquier cliente.

import json  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402


def _app_con_middleware(payload: dict):
    from app.middleware.masking import CUITMaskingMiddleware
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(CUITMaskingMiddleware)

    @app.get("/datos")
    async def datos():
        return payload

    return app


class TestMiddlewareEnElCuerpo:
    @pytest.mark.asyncio
    async def test_monto_de_11_digitos_no_se_enmascara_y_el_json_sigue_valido(self):
        # 10000000000.5 tiene 11 dígitos enteros: exactamente lo que el patrón
        # de CUIT matchea, y es un monto en pesos perfectamente normal.
        app = _app_con_middleware({"monto": 10000000000.5, "organismo": "ACIF"})
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/datos")

        body = json.loads(r.text)  # revienta si el cuerpo quedó inválido
        assert body["monto"] == 10000000000.5
        assert body["organismo"] == "ACIF"
        assert "*" not in r.text

    @pytest.mark.asyncio
    async def test_el_cuit_en_un_string_si_se_enmascara(self):
        app = _app_con_middleware(
            {"beneficiario": "Papelera Cumbre S.A. CUIT 20-12345678-9", "monto": 150150000.0}
        )
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/datos")

        body = json.loads(r.text)
        assert "20-12345678-9" not in body["beneficiario"]
        assert CUIT_MASK in body["beneficiario"]
        assert body["monto"] == 150150000.0

    @pytest.mark.asyncio
    async def test_un_cuit_sin_guiones_tambien_se_enmascara(self):
        app = _app_con_middleware({"detalle": "id=20123456789"})
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/datos")

        assert "20123456789" not in r.text
        assert CUIT_MASK in json.loads(r.text)["detalle"]
