#!/usr/bin/env python3
"""Evaluate the V.1.2 gold set against analisis in sqlite.db."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.extraction_goldset import (
    evaluate_goldset,
    extracted_from_db_row,
    load_gold_csv,
)

DB = Path(__file__).resolve().parent.parent / "sqlite.db"
GOLD = (
    Path(__file__).resolve().parent.parent.parent
    / "watcher-doc"
    / "data"
    / "2026"
    / "goldset"
    / "goldset.csv"
)
MD_OUT = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledgebase"
    / "current"
    / "goldset.md"
)


def main() -> None:
    gold = load_gold_csv(GOLD)
    filenames = sorted({row.filename for row in gold})
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    extracted = []
    for name in filenames:
        rows = conn.execute(
            """
            SELECT a.id, a.tipo_acto, a.numero_acto, a.organismo, a.monto_numerico,
                   a.etapa_gasto, a.is_gasto_publico, a.descripcion, b.section
            FROM analisis a JOIN boletines b ON b.id=a.boletin_id
            WHERE b.filename=?
            """,
            (name,),
        ).fetchall()
        for row in rows:
            extracted.append(extracted_from_db_row(row, name, row["section"]))
    conn.close()
    metrics = evaluate_goldset(gold, extracted)
    extra = [
        "",
        "## Corpus",
        "",
        f"- PDFs etiquetados: {len(filenames)}",
        f"- Actos extraídos en esos PDFs: {len(extracted)}",
        f"- Gold versionado en `{GOLD.as_posix()}`",
        "- PDFs en `boletines/` (gitignored). Dumps de páginas 1–4 en "
        "`watcher-doc/data/2026/goldset/*.txt`.",
        "",
        "Precisión omitida: el gold no es exhaustivo por PDF (S4 tiene "
        "decenas de pliegos EPEC). Recall mide si Watcher recuperó los "
        "actos etiquetados a mano desde el PDF.",
        "",
        "El scorer exige `numero_acto` con monto a ≤10% (si ambos tienen "
        "monto) y no acepta organismo+monto cuando el número extraído "
        "contradice el gold. Así se evita un falso match de `numero_acto` "
        "con otro pliego. El MAE es sobre matches honestos.",
        "",
    ]
    md = metrics.to_markdown() + "\n".join(extra)
    MD_OUT.write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
