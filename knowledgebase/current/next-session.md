# Próxima sesión — Watcher Agent

**Fecha del handoff:** 2026-09-15  
**Trabajo cerrado esta sesión:** V.1 (feb–mar) + scripts de lote + **abril 2026 cerrado** (98/98). Corte UI documentado.  
**Trabajo siguiente:** **V.2 matching / denominador** — no ingest de mayo.

---

## Dónde quedó

Rama: `feature/V.1-verificar-pipeline-vs-realidad` (artefactos V.1 + scripts de lote). Mergear **sin** `sqlite.db`.

| Mes | DB | Notas |
|---|---|---|
| 202602 | 90 completed + 10 failed Carnaval justificado | Cerrado |
| 202603 | 98 completed | Cerrado V.1.3 |
| 202604 | 98 completed, 0 pending | Operador: `ingest_month` + `process_pending` (S4 primero, 20/20; resto 78). 110 slots lun–vie est.; Δ feriados |

Cola viva vacía. Failed no justificados: 0.

UI `/presupuesto/ejecucion` (2026-09-15): 369 canónicos, **$703.7B compromiso / $1.1B ejecución**, 4 alertas >100%. Detalle: [corte-abril-ui.md](corte-abril-ui.md).

## Qué implementar (V.2)

Historia: [V.2-matching-denominador.md](../backlog/V.2-matching-denominador.md). Arrancar por **V.2.1**.

1. Reproducir las 4 alertas (S-511 → Dirección de Ministerio 295%; Secretaría de Desarrollo 2703%; Economía 145%; PJ 163% con vigente $11.2B).
2. Fix matching + denominador por organismo (`presupuesto_matching.py` / `ejecucion_contrast.py`).
3. Tests; no silenciar la alerta >100% en UI.
4. Actualizar `ancla-ley-11088.md` y el corte UI.

## Qué no hacer

- Ingest mayo–diciembre (multiplica matching basura y recall 44.4%).
- Meter pagado CGE en la misma barra que compromiso/ejecución del BO.
- Tratar $703.7B como ejecución SIGAF.
- Commitear `sqlite.db`, `*.db-wal`, `uv.lock`, PDFs, Mapas-por-Programas, xlsx CGE.

## Scripts de lote (si hace falta operar, no es V.2)

Desde `watcher-backend/`, Ollama en `127.0.0.1:11434`:

```powershell
uv run python scripts/lote_status.py
uv run python scripts/lote_status.py --watch 20
uv run python scripts/ingest_month.py --month 202605
uv run python scripts/process_pending.py --month 202605 --section 4
uv run python scripts/process_pending.py --month 202605
```

## Contexto mínimo

| Corte | Archivo |
|---|---|
| Handoff UI abril | [corte-abril-ui.md](corte-abril-ui.md) |
| Inventario feb–mar | [cobertura-calendario.md](cobertura-calendario.md) |
| Gold set | [goldset.md](goldset.md) |
| Ley 11.088 | [ancla-ley-11088.md](ancla-ley-11088.md) |
| CGE T1 | [cge-trimestral.md](cge-trimestral.md) |
| V.1 | [V.1-verificar-pipeline-vs-realidad.md](../backlog/V.1-verificar-pipeline-vs-realidad.md) |
| V.2 | [V.2-matching-denominador.md](../backlog/V.2-matching-denominador.md) |

Runtime LocalPro: `qwen2.5:7b`. Notion MCP no disponible.

## DoR V.2

- [x] Historia en backlog con criterio de aceptación
- [x] Rama sugerida `feature/V.2-matching-denominador`
- [ ] Working tree: mergear V.1 sin la DB
- [x] Criterio testeable (las 4 alertas)
