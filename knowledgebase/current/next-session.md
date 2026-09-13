# Próxima sesión — Watcher Agent

**Fecha del handoff:** 2026-09-13  
**Trabajo cerrado:** P.7.1 (clasificador de gasto) + P.7.2 (ledger al cerrar el pipeline) en `feature/P.7-gasto-acumulado-presupuesto`, **sin mergear**.  
**Trabajo siguiente:** [P.7.3 Anclar la Ley 11.088](../backlog/P.7-gasto-acumulado-presupuesto.md) y después P.7.4 (UI).

---

## Dónde quedó

El ledger de gasto ya se escribe solo. Al cerrar un boletín, `_analyze_document` clasifica cada acto y upserta `ejecucion_presupuestaria`: no hace falta correr el ETL a mano.

Sobre el corpus local (145 boletines, feb–mar 2026):

| | |
|---|---|
| Actos con monto | 1.680 |
| Gasto público | **131** (1.549 excluidos) |
| Ledger canónico | **$205,9 mil M** (de $437,8 mil M brutos) |
| Provincial | $188,5 mil M |
| Republicaciones marcadas | 19 · $87,5 mil M |
| Compromiso vs ejecución | $188,3 mil M vs $0,2 mil M |

Ese último renglón es el hallazgo de producto: el boletín publica casi exclusivamente **compromisos** (licitaciones), no pagos. Una sola cifra de "gasto" sería engañosa.

## Qué implementar

**P.7.3** es el bloqueo real: `presupuesto_base` tiene 0 filas, así que el match organismo→programa da 0% y el `% monto_acumulado / monto_vigente` no tiene denominador. Todo lo demás para P.7.4 ya está en la tabla (`etapa_gasto`, `jurisdiccion`, `analisis_id`, acumuladores).

1. **Conseguir el PDF del presupuesto 2026.** No está en el repo: `watcher-doc/data/2026/` no existe y `watcher-doc/data/` sólo tiene material 2025 (`Ley-de-Presupuesto-L-11014.pdf` es la **Ley 11.014 de 2025**, no la 11.088 de 2026). Hay que bajar Mapas-por-Programas / Ley 11.088 del portal de la Provincia antes de poder correr nada.
2. Correr `uv run python scripts/parse_pdf_presupuesto_2026.py` para poblar `presupuesto_base` con `ejercicio=2026`.
3. Agregar alias en `_ORGANISMO_ALIASES` (`app/services/presupuesto_matching.py`, **no** en el script) para los organismos que realmente aparecen en el ledger: `ACIF`, `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA`.
4. Re-correr `uv run python scripts/etl_analisis_to_ejecucion.py` y mirar el `% match`.

Después P.7.4: dos barras (compromiso vs ejecución), alerta &gt;100%, filtro de jurisdicción.

## Contexto mínimo

- La clave de dedup y el matching viven en `app/services/presupuesto_matching.py`, compartidos por el ETL batch y el ledger vivo. Hay paridad verificada entre ambos; no los dupliques.
- El clasificador (`app/services/gasto_classifier.py`) corre sobre texto **sin acentos**. Patrones nuevos, sin tildes.
- Runtime local: `.\scripts\start-backend-local.ps1`. No hay `make` en PowerShell. Docker Desktop bloqueado hasta instalar WSL2.
- No commitear `sqlite.db` / `*.db-wal`. No subir Neo4j heap en `docker-compose.yml` base.
- Backup del SQLite previo a P.7: `%TEMP%\sqlite-p7-backup.db`.

## Estado de la suite

158 tests de P.7 en verde. La suite completa da **475 passed / 11 failed**, y esos 11 fallan idénticos en `main` (6 son la deuda DT-2 del fixture de `indexing_service`). Para correrla hay que ignorar 7 módulos que no colectan por imports legacy — ver deuda técnica 7 en `status.md`.

## DoR para P.7.3

- [x] Historia con criterio de aceptación testeable
- [x] Dependencias de código: P.7.1 y P.7.2 en la rama
- [ ] ❌ **PDF del presupuesto 2026 NO está en el repo.** DoR incumplida: hay que bajarlo antes de arrancar P.7.3. Es el único bloqueo.
- [ ] Working tree limpio al arrancar (`git status`; `sqlite.db` aparece modificado, es artefacto de runtime)
