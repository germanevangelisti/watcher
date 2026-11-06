"""What the gasto listing covers, so the UI can say it out loud.

The listing mixes sources with very different reach: the provincial bulletin
(every provincial body, plus the municipalities that choose to publish in its
section 5), the Cordoba city bulletin and, since ``muni-portal-compras``, the
city's own procurement portal.  Every other municipality and comuna is *not*
covered unless it shows up in section 5.  A total without that caveat reads as
"all public spending in the province", which it is not.
"""

from __future__ import annotations

from app.db.models import Analisis, Boletin
from app.scrapers.muni_compras import (
    COMPRAS_BASE_URL,
    COMPRAS_FUENTE,
    COMPRAS_MUNICIPIO,
)
from app.scrapers.pds_muni import CORDOBA_BASE_URL, CORDOBA_FUENTE, CORDOBA_MUNICIPIO
from app.services.gasto_classifier import TIPO_NO_ES_GASTO
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ``tipo`` separates a bulletin (one row per edition, acts of any kind) from a
# procurement portal (one row per publication day, one row per procedure whose
# amount is the official budget of the *call*).  The UI words each source with
# its own unit instead of calling everything an "edición".
FUENTES: dict[str, dict] = {
    "provincial": {
        "nombre": "Boletín Oficial de la Provincia de Córdoba",
        "nivel": "provincial",
        "municipio": None,
        "portal": "https://boletinoficial.cba.gov.ar",
        "tipo": "boletin",
        "detalle": None,
    },
    CORDOBA_FUENTE: {
        "nombre": "Boletín Municipal de la Ciudad de Córdoba",
        "nivel": "municipal",
        "municipio": CORDOBA_MUNICIPIO,
        "portal": CORDOBA_BASE_URL,
        "tipo": "boletin",
        "detalle": None,
    },
    COMPRAS_FUENTE: {
        "nombre": "Portal de Compras de la Ciudad de Córdoba (MuniCompras)",
        "nivel": "municipal",
        "municipio": COMPRAS_MUNICIPIO,
        "portal": COMPRAS_BASE_URL,
        "tipo": "portal",
        "detalle": (
            "El monto es el presupuesto oficial del llamado: el adjudicatario y el monto "
            "adjudicado no son públicos. Las compras directas y las órdenes de provisión no "
            "aparecen en el listado público del portal; una licitación publicada también en el "
            "Boletín Municipal cuenta una sola vez."
        ),
    },
}

NOTA_SIN_COBERTURA = (
    "Los demás municipios y comunas sólo aparecen cuando publican en la sección 5 "
    "del boletín provincial; su gasto propio no está cubierto. El portal de compras "
    "de la ciudad publica las convocatorias, no las compras directas ni las órdenes "
    "de provisión."
)


def _iso(yyyymmdd: str | None) -> str | None:
    if not yyyymmdd or len(yyyymmdd) != 8:
        return None
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


async def cobertura(db: AsyncSession) -> dict:
    ediciones = (
        await db.execute(
            select(Boletin.fuente, func.count(Boletin.id), func.min(Boletin.date), func.max(Boletin.date))
            .group_by(Boletin.fuente)
        )
    ).all()
    es_gasto = (func.coalesce(Analisis.monto_numerico, 0) > 0) & (Analisis.tipo_gasto.is_not(None)) & (
        Analisis.tipo_gasto != TIPO_NO_ES_GASTO
    ) & (func.coalesce(Analisis.is_duplicate_gasto, 0) == 0)
    actos = {
        fuente: (n, n_gasto, monto)
        for fuente, n, n_gasto, monto in (
            await db.execute(
                select(
                    Boletin.fuente,
                    func.count(Analisis.id),
                    func.coalesce(func.sum(case((es_gasto, 1), else_=0)), 0),
                    func.coalesce(func.sum(case((es_gasto, Analisis.monto_numerico), else_=0.0)), 0.0),
                )
                .join(Boletin, Boletin.id == Analisis.boletin_id)
                .group_by(Boletin.fuente)
            )
        ).all()
    }
    fuentes = []
    for fuente, n_ed, desde, hasta in ediciones:
        meta = FUENTES.get(
            fuente or "provincial",
            {"nombre": fuente, "nivel": None, "municipio": None, "portal": None, "tipo": "boletin", "detalle": None},
        )
        n, n_gasto, monto = actos.get(fuente, (0, 0, 0.0))
        fuentes.append({
            "fuente": fuente,
            **meta,
            "ediciones": n_ed,
            "desde": _iso(desde),
            "hasta": _iso(hasta),
            "actos": n,
            "actos_gasto": n_gasto,
            "monto_gasto": float(monto),
        })
    fuentes.sort(key=lambda f: (f["nivel"] != "provincial", f["fuente"] or ""))
    return {
        "fuentes": fuentes,
        "municipios_cubiertos": sorted({f["municipio"] for f in fuentes if f["municipio"] and f["ediciones"]}),
        "nota": NOTA_SIN_COBERTURA,
    }
