"""Parse CGE open-data Excel and contrast vs the boletín ledger (V.1.5).

Hacienda publishes *devengado/pagado* of the whole SIGAF perimeter.  Watcher
publishes *compromiso* (and rare *pago*) seen in the Boletín Oficial.  The
numbers are an order-of-magnitude check, not a join acto-a-acto.
"""

from __future__ import annotations

import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from app.services.presupuesto_matching import _normalize

SSML = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_COL_RE = re.compile(r"^([A-Z]+)")

# Eight organisms the story asks to read by hand against the ledger.
CGE_TARGETS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("EPEC", ("epec", "empresa provincial de energia"), "jurisdiccion"),
    (
        "ACIF",
        ("agencia cordoba de inversion y financiamiento", "acif"),
        "jurisdiccion",
    ),
    ("Poder Judicial", ("poder judicial",), "jurisdiccion"),
    ("Ministerio de Seguridad", ("ministerio de seguridad",), "jurisdiccion"),
    ("Ministerio de Educación", ("ministerio de educacion",), "jurisdiccion"),
    ("Ministerio de Salud", ("ministerio de salud",), "jurisdiccion"),
    ("Policía de la Provincia", ("policia de la provincia",), "unidad"),
    (
        "Dirección de Ministerio / Inteligencia Fiscal",
        ("direccion de ministerio", "inteligencia fiscal"),
        "unidad",
    ),
)


@dataclass
class CgeTotals:
    label: str
    vigente: float = 0.0
    compromiso: float = 0.0
    devengado: float = 0.0
    pagado: float = 0.0
    n_rows: int = 0
    source: str = ""

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "vigente": self.vigente,
            "compromiso": self.compromiso,
            "devengado": self.devengado,
            "pagado": self.pagado,
            "n_rows": self.n_rows,
            "source": self.source,
        }


@dataclass
class LedgerBucket:
    compromiso: float = 0.0
    ejecucion: float = 0.0
    n: int = 0


def _col_index(ref: str) -> int:
    letters = _COL_RE.match(ref or "")
    if not letters:
        return 0
    n = 0
    for ch in letters.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall(f"{SSML}si"):
        texts = [t.text or "" for t in si.findall(f".//{SSML}t")]
        out.append("".join(texts))
    return out


def _cell_value(cell: ET.Element, shared: list[str]) -> str | None:
    kind = cell.get("t")
    node = cell.find(f"{SSML}v")
    if node is None:
        inline = cell.find(f"{SSML}is")
        if inline is None:
            return None
        return "".join(t.text or "" for t in inline.findall(f".//{SSML}t"))
    raw = node.text
    if raw is None:
        return None
    if kind == "s":
        return shared[int(raw)]
    return raw


def _row_values(row: ET.Element, shared: list[str]) -> list[str | None]:
    cells = list(row.findall(f"{SSML}c"))
    if not cells:
        return []
    refs = [c.get("r") for c in cells]
    if all(refs):
        width = max(_col_index(ref) for ref in refs) + 1
        out: list[str | None] = [None] * width
        for cell, ref in zip(cells, refs):
            out[_col_index(ref or "")] = _cell_value(cell, shared)
        return out
    return [_cell_value(cell, shared) for cell in cells]


def _to_float(raw: str | None) -> float:
    if raw is None or str(raw).strip() == "":
        return 0.0
    try:
        return float(str(raw).replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0


def iter_gasto_rows(xlsx_path: Path) -> Iterable[dict[str, str | None]]:
    """Yield dict rows from sheet1 of a CGE 'Gastos …' workbook."""
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = _shared_strings(zf)
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows = root.findall(f".//{SSML}row")
        if not rows:
            return
        header = [h or "" for h in _row_values(rows[0], shared)]
        for row in rows[1:]:
            vals = _row_values(row, shared)
            payload = {
                header[i]: (vals[i] if i < len(vals) else None)
                for i in range(len(header))
                if header[i]
            }
            if not any(payload.values()):
                continue
            yield payload


def aggregate_cge_rows(
    rows: Iterable[dict],
    *,
    source: str = "",
) -> dict[str, CgeTotals]:
    """Sum vigente/compromiso/devengado/pagado by JURISDICCION and unidad."""
    by_key: dict[str, CgeTotals] = {}
    for row in rows:
        juris = (row.get("JURISDICCION") or "").strip()
        unidad = (row.get("UNIDAD ADMINISTRATIVA") or "").strip()
        for label, kind in ((juris, "jurisdiccion"), (unidad, "unidad")):
            if not label:
                continue
            key = f"{kind}:{label}"
            bucket = by_key.get(key)
            if bucket is None:
                bucket = CgeTotals(label=label, source=source)
                by_key[key] = bucket
            bucket.vigente += _to_float(row.get("PRESUPUESTO VIGENTE"))
            bucket.compromiso += _to_float(row.get("COMPROMISO"))
            bucket.devengado += _to_float(row.get("DEVENGADO"))
            bucket.pagado += _to_float(row.get("PAGADO"))
            bucket.n_rows += 1
    return by_key


def _needles_hit(name: str, needles: tuple[str, ...]) -> bool:
    n = _normalize(name)
    return any(_normalize(needle) in n for needle in needles)


def pick_targets(totals: dict[str, CgeTotals]) -> list[CgeTotals]:
    """Resolve the eight story organisms against CGE aggregates."""
    picked: list[CgeTotals] = []
    for display, needles, kind in CGE_TARGETS:
        prefix = f"{kind}:"
        matches = [
            item
            for key, item in totals.items()
            if key.startswith(prefix) and _needles_hit(item.label, needles)
        ]
        if not matches:
            picked.append(CgeTotals(label=display, source=""))
            continue
        merged = CgeTotals(label=display, source=matches[0].source)
        for item in matches:
            merged.vigente += item.vigente
            merged.compromiso += item.compromiso
            merged.devengado += item.devengado
            merged.pagado += item.pagado
            merged.n_rows += item.n_rows
        picked.append(merged)
    return picked


def match_ledger_bucket(org_name: str, needles: tuple[str, ...]) -> bool:
    return _needles_hit(org_name, needles)


def magnitude_note(ledger: float, cge: float) -> str:
    if cge <= 0 and ledger <= 0:
        return "ambos vacíos"
    if cge <= 0:
        return "CGE no publica esta unidad; el ledger no es caja"
    if ledger <= 0:
        return "Watcher 0 — el boletín no trajo gasto canónico"
    ratio = ledger / cge
    if ratio < 0.05:
        return f"Watcher es ~{ratio:.1%} de CGE (suelo de avisos, no tesorería)"
    if ratio > 2:
        return f"Watcher {ratio:.1f}× CGE — revisar matching / duplicados"
    return f"mismo orden de magnitud ({ratio:.1%} de CGE)"
