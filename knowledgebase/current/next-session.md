# Próxima sesión — Watcher Agent

**Fecha del handoff:** 2026-09-13  
**Trabajo cerrado:** H.1 (pipeline hardware local) mergeado a `main`.  
**Trabajo siguiente:** [P.7 Gasto acumulado vs presupuesto](../backlog/P.7-gasto-acumulado-presupuesto.md)

---

## Qué implementar

Feature de producto: **ledger de gasto público** extraído del boletín, acumulado y contrastado con el presupuesto vigente (Ley 11.088). No es un KPI de suma bruta de `analisis.monto_numerico`.

Primera sesión: slices **P.7.1** (clasificar) + **P.7.2** (escribir `ejecucion_presupuestaria` al cerrar el pipeline). Dejar P.7.3 (cargar partidas) y P.7.4 (UI %) si el tiempo no alcanza.

## Contexto mínimo

- Corte analizado: [gasto-publico-actos.md](gasto-publico-actos.md) — $458 mil M brutos, $315 mil M tipos de gasto dedup, S-511 × 8 = 44% del bruto, ledger vacío.
- P.1–P.6 ya están en código (`etl_analisis_to_ejecucion.py`, API `/presupuesto/ejecucion`, página frontend). Falta clasificar, extraer `numero_acto`, cablear el ETL, cargar 2026.
- Runtime local: `.\scripts\start-backend-local.ps1`. No hay `make` en PowerShell. Docker Desktop bloqueado hasta instalar WSL2. Ollama en GPU; embeddings MiniLM en CPU.
- No commitear `sqlite.db` / `*.db-wal`. No subir Neo4j heap en `docker-compose.yml` base (GCE e2-medium).

## DoR

- [x] Historia con criterio de aceptación testeable
- [x] Estimación (8 pts; slices 2+3+2+1)
- [x] Dependencias: H.1 en `main`; PDF presupuesto 2026 solo para P.7.3
- [ ] Working tree limpio al **arrancar** (verificar `git status`)
- [ ] `main` actualizado (`git pull`)
