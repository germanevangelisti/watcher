# P.7 Gasto acumulado detallado vs presupuesto

**Épica:** P — Presupuesto y Ejecución  
**Puntos:** 8 (tomar por slices; no implementar el epígrafe entero en un solo PR si se va de scope)  
**Estado:** idea · DoR lista para arrancar  
**Rama sugerida:** `feature/P.7-gasto-acumulado-presupuesto` desde `main`  
**Handoff de sesión:** [next-session.md](../current/next-session.md)  
**Evidencia del corte:** [gasto-publico-actos.md](../current/gasto-publico-actos.md)

## Objetivo

Registrar el gasto público extraído de boletines como un **ledger acumulado** (organismo, programa, partida, etapa, jurisdicción) y contrastarlo con `presupuesto_base.monto_vigente`.

La suma cruda de `analisis.monto_numerico` **no** es esa feature. En cooperledge (2026-09-13) vale $458,4 mil M y está inflada por republicaciones, remates y actos societarios. Un solo pliego (S-511) × 8 avisos = 44% del bruto.

## Por qué es producto

Watcher ya extrae actos con monto. El valor ciudadano es poder decir: *este organismo lleva comprometido X% de su programa vigente*, no un total del PDF. P.1–P.6 construyeron parser, ETL, API y página Ejecución; **el ledger no se alimenta** al cerrar el pipeline y `presupuesto_base` está vacío en el SQLite local.

## Criterio de aceptación (epígrafe)

- [ ] Cada acto persistido lleva `is_gasto_publico` (bool) y `etapa_gasto` (`llamado` | `adjudicacion` | `contrato` | `pago` | `modificacion` | `no_aplica`).
- [ ] S2 edictos/remates, S3 sociedades y modificaciones de partidas quedan `is_gasto_publico=false`.
- [ ] Al completar el pipeline de un boletín se upserta `ejecucion_presupuestaria` (no hace falta un ETL manual posterior).
- [ ] Dedup con la clave ya definida en `etl_analisis_to_ejecucion.py` (organismo normalizado, monto a 1 M, `numero_acto`); duplicados marcan `is_duplicate=1` y **no** suman a `monto_acumulado_*`.
- [ ] `numero_acto` se extrae en S4 (hoy sale `null` en el 1 sep 2026; sin eso el ETL no deduplica llamados).
- [ ] `presupuesto_base` 2026 (Ley 11.088) cargado; match organismo/programa con alias (ACIF, EPEC, Policía, CCU).
- [ ] UI `/presupuesto/ejecucion` muestra `% monto_acumulado / monto_vigente` y alerta de sobre-compromiso, **separando** licitación (compromiso) de pago/transferencia (ejecución).
- [ ] Filtro de jurisdicción: provincial vs municipal vs fuera del presupuesto (judicial-privado).

## Slices (orden de implementación)

| Slice | Pts | Entrega | DoD mínimo |
|---|---|---|---|
| **P.7.1** Clasificar | 2 | Flag + etapa + jurisdicción en `analisis` (reglas; sin reentrenar LLM) | Tests de casos S2 remate, S3 capital, S4 licitación, S5 municipal, modificación de partidas |
| **P.7.2** Ledger al cerrar pipeline | 3 | Tras `_analyze_document`, upsert `ejecucion_presupuestaria`; extraer `numero_acto` en S4 | Un boletín S4 produce filas canónicas; republicar el mismo pliego marca `is_duplicate` |
| **P.7.3** Anclar Ley 11.088 | 2 | Cargar `presupuesto_base` 2026 + alias ACIF/EPEC/Policía/CCU | `python scripts/parse_pdf_presupuesto_2026.py` deja filas 2026; match ≠ `UNIDAD EJECUTORA` |
| **P.7.4** Contrastar en UI | 1 | `%` vs `monto_vigente` + alerta &gt;100% + toggle compromiso/ejecución | Página `/presupuesto/ejecucion` no vacía con el SQLite local |

Primera sesión: **P.7.1 + P.7.2**. P.7.3 necesita el PDF `watcher-doc/data/2026/Mapas-por-Programas.pdf`. P.7.4 espera ledger con datos.

## Fuera de alcance

- Sustituir la ejecución oficial en Excel (SIFEP). El boletín es un **proxy de compromisos publicados**.
- Re-entrenar el LLM. Clasificador = reglas + `tipo_acto` + `boletines.section` + keywords.
- Neo4j, reindex Chroma, Docker/WSL, merge H.1 (ya en `main`).

## Archivos a tocar

| Área | Path |
|---|---|
| Schema acto | `watcher-backend/app/db/models.py` (`Analisis`, ya tiene `EjecucionPresupuestaria`) |
| Persistencia | `watcher-backend/app/db/crud.py` (`create_analisis`) · `database.py` (`_ensure_sqlite_columns`) |
| Extracción | `watcher-backend/app/services/analysis_schema.py` (prompt: exigir `numero`) |
| Local LLM | `watcher-backend/app/services/local_intelligence.py` |
| Gemini path | `watcher-backend/app/services/watcher_service.py` |
| Pipeline hook | `watcher-backend/app/api/v1/endpoints/pipeline.py` (`_analyze_document`, ~cierre del doc) |
| ETL reutilizar | `watcher-backend/scripts/etl_analisis_to_ejecucion.py` — extraer funciones; no copiar el script |
| Parser 2026 | `watcher-backend/scripts/parse_pdf_presupuesto_2026.py` |
| API | `watcher-backend/app/api/v1/endpoints/presupuesto.py` |
| UI | `watcher-frontend/src/pages/presupuesto/ejecucion.tsx` |
| Tests ETL | `watcher-backend/tests/tests/test_etl_presupuesto.py` |

## Semántica (no negociable)

| Señal en el boletín | `is_gasto_publico` | `etapa_gasto` | ¿Suma al acumulado canónico? |
|---|---|---|---|
| Licitación / llamado S4, presupuesto oficial | sí (provincial) | `llamado` | sí, como **compromiso**; no como ejecución |
| Adjudicación / contrato | sí | `adjudicacion` / `contrato` | sí (compromiso; no duplicar el llamado) |
| Transferencia, subsidio, pago | sí | `pago` | sí, **ejecución** |
| Remate/subasta judicial S2 | no | `no_aplica` | no |
| Escisión / aumento de capital S3 | no | `no_aplica` | no |
| Compensación/incremento de partidas | no | `modificacion` | no (mueve techo, no paga) |
| Municipio S5 / CCU si no está en Ley | no (o jurisdicción municipal) | según tipo | no contra presupuesto **provincial** |

Licitación ≠ devengado. La UI debe mostrar dos barras, no una.

## Datos locales (cooperledge)

`watcher-backend/sqlite.db` es artefacto de runtime (gitignore `*.db`; el blob del repo es el snapshot viejo). El corte analizado vive en [gasto-publico-actos.md](../current/gasto-publico-actos.md), no hace falta commitear la DB.

Para probar P.7.2 contra actos reales: el SQLite local de cooperledge ya tiene 5.667 filas en `analisis`. No borrar. `presupuesto_base` = 0 hasta P.7.3.

## Cómo arrancar la sesión

```powershell
cd C:\Users\germa\watcher
git checkout main
git pull
git checkout -b feature/P.7-gasto-acumulado-presupuesto
# Backend ya conocido:
.\scripts\start-backend-local.ps1
```

Prompt mínimo para el agente: *Implementá P.7.1 y P.7.2 según `knowledgebase/backlog/P.7-gasto-acumulado-presupuesto.md`. No toques heap Neo4j en compose base. No commitees sqlite.db.*

## Notas para agentes

- Reutilizar `_ORGANISMO_ALIASES` y `_dedup_key` del ETL; no reescribir el acumulador.
- No correr el ETL sobre `monto_numerico > 0` sin `is_gasto_publico`: mete remates y capital social.
- `numero_acto` hoy se mapea desde `analisis_data["numero"]` en `crud.create_analisis`. El hueco es el LLM (S4 del 1-sep salió `null`).
- Código en inglés, docs en español. Línea ≤ 100 (ruff).
- Notion: al empezar → `En progreso`; al terminar un slice → `Hecho` si existe el ticket. MCP Notion a menudo no está en la sesión.
- Tests: `uv run pytest tests/tests/test_etl_presupuesto.py tests/tests/unit/test_fragment_priority.py -q` más tests nuevos del clasificador.
