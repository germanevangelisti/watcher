# Próxima sesión — Watcher Agent

**Fecha del handoff:** 2026-09-14  
**Trabajo cerrado:** P.7.1–P.7.4 mergeada a `main` + historia **V.1** documentada.  
**Trabajo siguiente:** [V.1.1 Inventario calendario vs DB](../backlog/V.1-verificar-pipeline-vs-realidad.md).

---

## Dónde quedó

`/presupuesto/ejecucion` muestra compromiso vs ejecución contra `monto_vigente` (filtro default provincial). API de presupuesto emite montos en **millones de ARS**.

Sobre el corpus local (provincial, canónicos):

| | |
|---|---|
| Compromiso | ~$188,3 mil M |
| Ejecución | ~$0,23 mil M |
| EPEC | 2,87% del vigente |
| Poder Judicial | 86,55% |
| Sobre-compromiso | 1 organismo: `DIRECCIÓN DE MINISTERIO` 295% (falso positivo S-511 → Jaccard 0,40) |

El corpus es un recorte (feb–mar 2026 + 1 sep). No usar esos % como claim de año completo.

## Qué implementar

**V.1.1** — script o informe: días hábiles publicados (fecha × sección S1–S5) vs filas en `boletines`. Lista de huecos, `failed` y `pending`.

No completar abr–dic antes del gold set (V.1.2). No mezclar CGE/SIGAF en la misma barra que el ledger del boletín.

## Contexto mínimo

- Historia: `knowledgebase/backlog/V.1-verificar-pipeline-vs-realidad.md`
- Contraste P.7: `app/services/ejecucion_contrast.py`. Matching: `presupuesto_matching.py`.
- Runtime: backend `127.0.0.1:8001`, frontend `localhost:5173`. No commitear `sqlite.db`.
- Notion MCP no disponible.

## DoR para arrancar V.1

- [x] Historia en backlog con criterio de aceptación
- [x] Working tree limpio tras este merge
- [x] Rama `main` actualizada
- [ ] Crear `feature/V.1-verificar-pipeline-vs-realidad` desde `main`
