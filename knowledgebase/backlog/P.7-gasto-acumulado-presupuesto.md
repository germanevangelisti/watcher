# P.7 Gasto acumulado detallado vs presupuesto

**Épica:** P — Presupuesto y Ejecución  
**Puntos:** 8 (tomar por slices; no implementar el epígrafe entero en un solo PR si se va de scope)  
**Estado:** en progreso · **P.7.1 y P.7.2 hechas** (2026-09-13) · P.7.3 y P.7.4 pendientes  
**Rama:** `feature/P.7-gasto-acumulado-presupuesto` desde `main`  
**Handoff de sesión:** [next-session.md](../current/next-session.md)  
**Evidencia del corte:** [gasto-publico-actos.md](../current/gasto-publico-actos.md)

## Objetivo

Registrar el gasto público extraído de boletines como un **ledger acumulado** (organismo, programa, partida, etapa, jurisdicción) y contrastarlo con `presupuesto_base.monto_vigente`.

La suma cruda de `analisis.monto_numerico` **no** es esa feature. En cooperledge (2026-09-13) vale $458,4 mil M y está inflada por republicaciones, remates y actos societarios. Un solo pliego (S-511) × 8 avisos = 44% del bruto.

## Por qué es producto

Watcher ya extrae actos con monto. El valor ciudadano es poder decir: *este organismo lleva comprometido X% de su programa vigente*, no un total del PDF. P.1–P.6 construyeron parser, ETL, API y página Ejecución; **el ledger no se alimenta** al cerrar el pipeline y `presupuesto_base` está vacío en el SQLite local.

## Criterio de aceptación (epígrafe)

- [x] Cada acto persistido lleva `is_gasto_publico` (bool) y `etapa_gasto` (`llamado` | `adjudicacion` | `contrato` | `pago` | `modificacion` | `no_aplica`).
- [x] S2 edictos/remates, S3 sociedades y modificaciones de partidas quedan `is_gasto_publico=false`.
- [x] Al completar el pipeline de un boletín se upserta `ejecucion_presupuestaria` (no hace falta un ETL manual posterior).
- [x] Dedup con la clave ya definida en `etl_analisis_to_ejecucion.py` (organismo normalizado, monto a 1 M, `numero_acto`); duplicados marcan `is_duplicate=1` y **no** suman a `monto_acumulado_*`.
- [x] `numero_acto` se extrae en S4 — `numero` pasó a `required` en el schema + fallback regex determinista. Sólo 3 de 131 filas del ledger quedan sin número.
- [ ] `presupuesto_base` 2026 (Ley 11.088) cargado; match organismo/programa con alias (ACIF, EPEC, Policía, CCU). → **P.7.3**
- [ ] UI `/presupuesto/ejecucion` muestra `% monto_acumulado / monto_vigente` y alerta de sobre-compromiso, **separando** licitación (compromiso) de pago/transferencia (ejecución). → **P.7.4**
- [x] Filtro de jurisdicción: provincial vs municipal vs fuera del presupuesto (judicial-privado). Persistido en `analisis.jurisdiccion_gasto` y `ejecucion_presupuestaria.jurisdiccion`.

## Slices (orden de implementación)

| Slice | Pts | Entrega | Estado |
|---|---|---|---|
| **P.7.1** Clasificar | 2 | Flag + etapa + jurisdicción en `analisis` (reglas; sin reentrenar LLM) | ✅ hecho — `app/services/gasto_classifier.py`, 56 tests |
| **P.7.2** Ledger al cerrar pipeline | 3 | Tras `_analyze_document`, upsert `ejecucion_presupuestaria`; extraer `numero_acto` en S4 | ✅ hecho — `app/services/ejecucion_ledger.py`, 18 tests |
| **P.7.3** Anclar Ley 11.088 | 2 | Cargar `presupuesto_base` 2026 + alias ACIF/EPEC/Policía/CCU | ⬜ **bloqueada** — el PDF 2026 no está en el repo |
| **P.7.4** Contrastar en UI | 1 | `%` vs `monto_vigente` + alerta &gt;100% + toggle compromiso/ejecución | ⬜ pendiente — el ledger ya tiene datos y `etapa_gasto` |

P.7.3 está bloqueada por datos, no por código: `watcher-doc/data/2026/` no existe y `watcher-doc/data/` sólo tiene PDFs 2025 (`Ley-de-Presupuesto-L-11014.pdf` es la Ley 11.014 de 2025). Hay que bajar Mapas-por-Programas / Ley 11.088 del portal provincial. P.7.4 ya tiene ledger con datos: sólo le falta `monto_vigente` como denominador.

## Resultado medido sobre el corpus real (2026-09-13)

ETL corrido sobre el SQLite local (145 boletines, 20260202–20260312, 5.627 actos):

| Métrica | Valor |
|---|---|
| Actos con monto &gt; 0 | 1.680 |
| Clasificados como gasto público | **131** (excluidos 1.549) |
| Filas canónicas en el ledger | 112 |
| Duplicados marcados | 19 |
| Bruto `analisis` | $437,8 mil M |
| Ledger canónico | **$205,9 mil M** |
| Provincial canónico | **$188,5 mil M** |
| Excluido por republicación | $87,5 mil M |

Exclusiones por motivo: S3 sociedades 586 + societario por keyword 371, S2 judicial 147 + judicial por keyword 405, sin señal de gasto 39, modificación de partidas 1.

**Compromiso vs ejecución (provincial, canónico):** 78 actos / $188,3 mil M de compromiso contra 4 actos / $0,2 mil M de ejecución. El boletín es casi enteramente compromiso — confirma que la UI necesita dos barras y que publicar una sola cifra sería engañoso.

La republicación del pliego de pavimento ($25,34 mil M) quedó cubierta dos veces: las apariciones en S1 son *aperturas de Registro de Opositores* (no son etapa de gasto, `is_gasto_publico=false`) y las repetidas en S4 caen por `is_duplicate`.

**Paridad verificada:** correr `upsert_boletin_ejecucion` sobre un boletín real ya procesado por el ETL batch produce filas idénticas (monto, etapa, jurisdicción, `is_duplicate`, acumuladores).

## Fuera de alcance

- Sustituir la ejecución oficial en Excel (SIFEP). El boletín es un **proxy de compromisos publicados**.
- Re-entrenar el LLM. Clasificador = reglas + `tipo_acto` + `boletines.section` + keywords.
- Neo4j, reindex Chroma, Docker/WSL, merge H.1 (ya en `main`).

## Archivos tocados (P.7.1 + P.7.2)

| Área | Path | Cambio |
|---|---|---|
| Clasificador | `app/services/gasto_classifier.py` | **nuevo** — reglas, sin LLM |
| Ledger vivo | `app/services/ejecucion_ledger.py` | **nuevo** — upsert async por boletín |
| Matching compartido | `app/services/presupuesto_matching.py` | **nuevo** — extraído del ETL; fuente única de la clave de dedup |
| Schema acto | `app/db/models.py` | `is_gasto_publico`, `etapa_gasto`, `jurisdiccion_gasto` en `Analisis`; `analisis_id`, `etapa_gasto`, `jurisdiccion` en `EjecucionPresupuestaria` |
| Migración | `alembic/versions/add_acto_gasto_classification.py` | **nueva**, idempotente |
| Persistencia | `app/db/crud.py` · `app/db/database.py` | persiste la clasificación; fallback de `numero_acto`; `_ensure_sqlite_columns` ahora cubre dos tablas |
| Extracción | `app/services/analysis_schema.py` | `numero` pasó a `required` + prompt explícito sobre republicaciones |
| Pipeline hook | `app/api/v1/endpoints/pipeline.py` | clasifica en la fase de prepare; upserta el ledger al cerrar el doc (non-fatal) |
| ETL batch | `scripts/etl_analisis_to_ejecucion.py` | importa del módulo compartido; filtra por `is_gasto_publico`; clasifica y persiste filas viejas |
| Desbloqueo | `scripts/parse_excel_presupuesto.py` | `pandas` pasa a import perezoso (bloqueaba la colección de `test_etl_presupuesto.py`) |
| Tests | `tests/tests/unit/test_gasto_classifier.py` · `tests/tests/test_ejecucion_ledger.py` · `tests/tests/test_etl_presupuesto.py` | 74 tests nuevos |

Pendiente para P.7.3/P.7.4: `scripts/parse_pdf_presupuesto_2026.py`, `app/api/v1/endpoints/presupuesto.py`, `watcher-frontend/src/pages/presupuesto/ejecucion.tsx`.

No hizo falta tocar `local_intelligence.py` ni `watcher_service.py`: ambos tiers ya comparten `analysis_schema.py`, así que exigir `numero` alcanzó a Gemini y a LocalPro a la vez.

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

## Cómo seguir (P.7.3)

```powershell
cd C:\Users\germa\watcher
git checkout feature/P.7-gasto-acumulado-presupuesto
cd watcher-backend
uv run python scripts/parse_pdf_presupuesto_2026.py   # necesita el PDF Mapas-por-Programas
uv run python scripts/etl_analisis_to_ejecucion.py    # re-matchea el ledger ya poblado
```

`presupuesto_base` sigue en 0 filas, así que el match cae a 0% y `% monto_acumulado / monto_vigente` no se puede calcular todavía. Ese es exactamente el bloqueo de P.7.3.

Alias a agregar en `_ORGANISMO_ALIASES` (vistos como organismos reales del ledger): `ACIF`, `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA` (EPEC), `UNIDAD EJECUTORA` ya está en la blocklist.

## Notas para agentes

- La clave de dedup y el matching viven en `app/services/presupuesto_matching.py`. **No** duplicarlos: el ETL batch y el ledger vivo tienen que coincidir, y hay un test que compara ambos.
- No correr el ETL sobre `monto_numerico > 0` sin `is_gasto_publico`: mete remates y capital social.
- El clasificador corre sobre texto **sin acentos** (`_strip_accents`). Si agregás patrones, escribilos sin tildes: la extracción de PDF las pierde de forma inconsistente ("Adjudícase" vs "Adjudicase").
- El default del clasificador es `is_gasto_publico=false`. Es deliberado: el ledger es una afirmación sobre dinero público, y un acto no clasificable no debe inflar el total.
- Código en inglés, docs en español. Línea ≤ 100 (ruff).
- Notion: MCP no estuvo disponible en la sesión de P.7.1/P.7.2 — el tablero quedó sin actualizar.
- Tests: `uv run pytest tests/tests/unit/test_gasto_classifier.py tests/tests/test_ejecucion_ledger.py tests/tests/test_etl_presupuesto.py -q` (158 tests).

## Decisiones tomadas en P.7.1/P.7.2

1. **Municipal se clasifica, no se descarta.** Un acto municipal genuino queda `is_gasto_publico=true` con `jurisdiccion='municipal'`; lo que lo excluye del contraste provincial es la jurisdicción, no el flag. Así se cumple el filtro de tres valores del criterio de aceptación sin perder información.
2. **`modificacion` se evalúa antes que todo lo demás.** "Transferencia de partidas" matchearía `pago` por la palabra "transferencia"; el orden lo evita.
3. **`adjudicacion` gana sobre `llamado`.** Un acto que adjudica una licitación es adjudicación aunque el texto siga diciendo "Licitación Pública".
4. **Los acumuladores están acotados a `fecha_boletin <= fecha del boletín`**, no al año entero. Reprocesar un boletín viejo no debe sumarle gasto publicado después; además así coincide con el ETL batch, que recorre en orden de fecha.
5. **El hook del ledger es non-fatal.** Si falla, hace `rollback` y loguea: los actos ya guardados no se pierden.
