# Próxima sesión — Watcher Agent

**Fecha del handoff:** 2026-09-15  
**Trabajo cerrado esta sesión:** **V.2 matching / denominador** (V.2.1–V.2.4). 0 alertas >100% en el corte abril.  
**Trabajo siguiente:** ingest mayo **o** UI huérfana / CI — el % vs Ley ya es defendible en las 4 alertas de abril.

---

## Dónde quedó

Rama: `feature/V.2-matching-denominador`. Mergear **sin** `sqlite.db`.

Operar el denominador en una DB local:

```powershell
cd C:\Users\germa\watcher\watcher-backend
uv run python scripts/parse_pdf_presupuesto_2026.py --repair-db
uv run python scripts/etl_analisis_to_ejecucion.py
```

| Mes | DB | Notas |
|---|---|---|
| 202602 | cerrado V.1 | Carnaval justificado |
| 202603 | 98 completed | Cerrado V.1.3 |
| 202604 | 98 completed | Cerrado |

UI `/presupuesto/ejecucion`: 369 canónicos, **$703.7B compromiso / $1.1B ejecución**, **0 alertas >100%**. Detalle: [corte-abril-ui.md](corte-abril-ui.md).

## Qué quedó hecho (V.2)

Historia: [V.2-matching-denominador.md](../backlog/V.2-matching-denominador.md).

1. Bitácora V.2.1: [bitacora-alertas-v2.md](bitacora-alertas-v2.md).
2. Matching: Jaccard por tokens distintivos; stubs (`MINISTERIO DE`, `DIRECCIÓN DE MINISTERIO`) no matchean.
3. Denominador: `PODER JUDICIAL` + `PODER JUDICIAL -` → $103.3B (17.6%). Economía → $80.9B (42.6%).
4. Parser: `--repair-db` promociona truncos desde la jurisdicción. Tests S-511 / PJ / trunco. La UI **no** silencia >100%.

## Qué no hacer

- Meter pagado CGE en la misma barra que compromiso/ejecución del BO.
- Tratar $703.7B como ejecución SIGAF.
- Commitear `sqlite.db`, `*.db-wal`, `uv.lock`, PDFs, Mapas-por-Programas, xlsx CGE.

## Contexto mínimo

| Corte | Archivo |
|---|---|
| Handoff UI post V.2 | [corte-abril-ui.md](corte-abril-ui.md) |
| Ancla Ley | [ancla-ley-11088.md](ancla-ley-11088.md) |
| V.2 | [V.2-matching-denominador.md](../backlog/V.2-matching-denominador.md) |

Runtime LocalPro: `qwen2.5:7b`. Notion MCP no disponible.
