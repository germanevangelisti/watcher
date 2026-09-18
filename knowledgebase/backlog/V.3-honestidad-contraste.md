# V.3 Honestidad del contraste

**Épica:** V — Verificación / ground truth (capa B: ledger vs Ley)
**Puntos:** 8 (tomar por slices)
**Estado:** pendiente
**Rama sugerida:** `feature/V.3-honestidad-contraste` desde `main`
**Depende de:** V.2 hecho (matcher canónico) — **pero V.2 nunca aplicó su fix a los datos**
**Handoff:** [next-session.md](../current/next-session.md)
**Evidencia del corte:** [bitacora-alertas-v2-post.md](../current/bitacora-alertas-v2-post.md)

---

## Objetivo

Que lo que la pantalla afirma sea **cierto**. V.2 arregló el matcher; V.3 hace que
el **dato persistido** y la **lectura ciudadana** estén a la altura de ese matcher.

Tres afirmaciones que hoy son falsas o invisibles:

1. Las 3 alertas `>100%` de la pantalla son **artefactos de matches viejos**, no
   sobre-ejecución. Una de ellas (2703%) contradice el titular de V.2.
2. Una obra de **$25,34B** se cuenta **4 veces** ($101,37B) porque el dedup no ve
   que cuatro nombres distintos son el mismo acto.
3. El **34,7%** del gasto medido ($244B) no tiene denominador y la lista de la UI
   lo **oculta** (filtra `matched`), así que el ciudadano no sabe que falta.

## Por qué es producto

El objetivo es *medir gasto público provincial vs presupuesto*. Un contraste que
sólo muestra lo que matchea, con denominadores viejos y montos contados cuatro
veces, no mide: opina. Y una alerta de 2703% que ya sabemos falsa es peor que
ninguna alerta — entrena a ignorar el panel.

El titular de V.2 fue "0 alertas >100%". Contra la DB de hoy hay **3**. La
credibilidad del producto se arregla acá, no en una historia nueva de features.

## Hallazgos del corte 2026-09-18 (medidos, no inferidos)

Base: `watcher-backend/sqlite.db`, `jurisdiccion='provincial'`, `is_duplicate=0`,
`monto>0`. Reproducible con `uv run python scripts/bitacora_alertas_v2.py`.

| Hecho | Número |
|---|---|
| Filas canónicas provinciales | 282 · $668,2B |
| Filas con `presupuesto_base_id` que el matcher vivo **ya no asigna** | **14 · $80,72B · 12,1%** |
| Alertas `sobre_compromiso` | **3 · las 3 son artefacto de las 14** |
| Gasto sin denominador | $244,0B · 34,7% · 141 filas |
| Obra contada 4 veces | $101,37B sobre una obra de $25,34B |

### H1 — El fix de V.2 está en el código pero no en los datos

El criterio de aceptación de V.2 decía textualmente *"**Tras re-upsert**, la alerta
295% desaparece o queda unmatched explícito"*. El re-upsert **nunca se corrió**.
`presupuesto_base_id` es un campo persistido y nada lo revalida contra el matcher
actual: el ETL sólo lo escribe cuando reconstruye toda la tabla.

Las 3 alertas, con su match en vivo:

| Alerta UI | compromiso / vigente | % | Filas | Match vivo |
|---|---:|---:|---:|---|
| SECRETARÍA DE DESARROLLO | $50.613.330.422 / $1.872.024.000 | 2703,67% | 4 | 2 filas **unmatched** `score=0.00`, con `pb_id=7` viejo |
| DIRECCIÓN DE MINISTERIO | $25.341.354.989 / $8.578.475.000 | 295,41% | 1 | **unmatched** `score=0.00`, `pb_id=54` viejo |
| MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA | $34.450.820.322 / $23.718.656.000 | 145,25% | 3 | 1 fila `substring score=0.53` → `pb_id=35` |

`DIRECCIÓN DE MINISTERIO` ($8,58B, programa *156 - Agentes De R.G.P. INTELIGENCIA
FISCAL*) es exactamente el denominador basura que V.2.2 debía bloquear. El bloqueo
existe (`match_organismo` devuelve `None`), pero la fila `id=97` conserva `pb_id=54`.

**Consecuencia mecánica:** la UI expone `matched = org in vigente_por_org`. Un
`pb_id` viejo sobre un organismo que sí existe en `presupuesto_base` produce
`matched=True` → se dibuja una barra con denominador. No es un detalle de
etiquetado: **resucita un denominador falso y una alerta falsa.**

### H2 — La misma obra, cuatro nombres, cuatro veces el monto

`_dedup_key(org_norm, monto, acto_norm)` incluye el organismo. Si el boletín
republica el mismo acto con otro nombre, la clave cambia y no deduplica.

Caso S-511, una obra de **$25.341.354.989**, 4 filas canónicas:

| acto | organismo | fila |
|---|---|---|
| `RESOLUCION 056/2026` | DIRECCIÓN DE INTELIGENCIA FISCAL | id=97 |
| `RESOLUCION 056/2026` | Unidad Ejecutora | id=106 |
| `S-511` | LAS PEÑAS SUD – LAS ISLETILLAS | id=85 |
| `S-511` | UNIDAD EJECUTORA | id=93 |

Total canónico: **$101.365.419.956**. Las 4 filas tienen `etapa_gasto='llamado'`,
o sea que **la barra de compromiso misma carga los $101,37B** por una obra de
$25,34B: inflada 4×. (Las otras 3 filas del grupo —ids 109/111/112— sí quedaron
`is_duplicate=1`.)

### H3 — El dedup es ciego a variantes de ortografía

El mismo acto con el nombre del organismo escrito distinto tampoco deduplica. El
caso más caro, `acto=5543`, **$20,03B** en 2 filas canónicas:

- `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA S.A.U (EPEC)` (id=95)
- `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA S.A.U` (id=99)

El sufijo `(EPEC)` cambia `org_norm`. Idéntico patrón en `acto=5560` (8 filas, 3
canónicas) y `acto=5558` (3 canónicas) — ahí las copias con ortografía **idéntica**
sí se deduplicaron, lo que confirma que la falla es la normalización, no el dedup.

### H4 — El mismo acto con dos identificadores distintos es indeduplicable

Peor que H3: hay actos que el boletín republica con **otro número**, así que ni
normalizando el organismo se juntan. El caso de **$34.026.000.000** en 2 filas
canónicas, ambas `etapa_gasto='llamado'` → **$68,05B** en la barra de compromiso:

| fila | organismo | acto |
|---|---|---|
| id=399 | SECRETARIA DE ASUNTOS INSTITUCIONALES | `Licitación Pública N° 660649` |
| id=411 | Secretaría General de la Gobernación - Ministerio de Economía y Gestión Pública | `Licitación Pública EXPEDIENTE N° 0378-219684/2026` |

Mismo monto al peso, mismo tipo de acto, boletines distintos. `_normalize_acto`
las ve como dos actos porque el número y el expediente no coinciden.

**Esta única duplicación es lo que mantiene viva la última alerta.** id=411 es la
que matchea `substring score=0.53` contra `pb_id=35`, un organismo trunco de
$1,37B (`MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA`, programa *16 -
APORTES AGENCIA PARA LA*). Si la duplicación se colapsa, el compromiso de ese
organismo cae de $34,45B a $0,42B → 1,79% → **la alerta de 145,25% desaparece**.
V.3.2 cierra la última alerta sin tocar el matcher.

## Resultado V.3.1 — re-upsert corrido (2026-09-18)

`uv run python scripts/etl_analisis_to_ejecucion.py` (backup previo en
`sqlite.bak.db`). Sin pérdida de filas: 369 canónicas / $704,78B antes y después.

| Métrica | Antes | Después |
|---|---:|---:|
| Alertas `sobre_compromiso` (provincial) | **3** | **1** |
| Deriva de match (`check_match_drift.py`) | 18 filas · $86,11B | **0 · $0,00B** |
| Gasto provincial sin denominador | $142,02B | **$212,28B** |
| Filas sin match en el ETL | — | 163 de 415 (39,3%) |

Las alertas de **2703,67%** (SECRETARÍA DE DESARROLLO) y **295,41%** (DIRECCIÓN DE
MINISTERIO) desaparecieron: eran denominadores falsos. La de 145,25% sobrevive y
es duplicación (H4), no match — la cierra V.3.2.

Los $70,26B que salieron de denominadores falsos no se "perdieron": ahora se
declaran como gasto sin denominador. Eso es el producto siendo honesto, no el
producto empeorando: antes afirmaba un % sobre un techo que no le correspondía.

Nuevo script: `scripts/check_match_drift.py` (read-only, sale con código 1 si hay
deriva). Es el gate del criterio de aceptación 1.

## Criterio de aceptación (epígrafe)

- [x] **Ninguna fila canónica conserva un `presupuesto_base_id` que el matcher
      actual no asigne.** 18 filas con deriva → **0**. Gate:
      `scripts/check_match_drift.py` (exit 1 si hay deriva).
- [x] **Las 3 alertas artefacto desaparecen** de `bitacora-alertas-v2-post.md` con
      el re-upsert corrido. Quedan **1**, y no es artefacto de match: es
      duplicación (H4), con su `pb_id` y su score documentados.
- [ ] **La obra S-511 cuenta 1 vez ($25,34B), no 4 ($101,37B)**, y `acto=5543`
      cuenta 1 vez ($20,03B), no 2. Test con los ids 85/93/97/106 y 95/99.
- [ ] **La UI muestra el gasto sin denominador.** El 34,7% ($244B) es visible como
      cobertura, no oculto por el filtro `matched`. No se inventa un denominador
      para mostrarlo.
- [ ] **Compromiso ≠ llamado.** La UI separa `llamado` (intención) de
      `adjudicación + contrato` (compromiso real: hoy $1,9B = 0,27%). Sin esto la
      barra ámbar afirma un compromiso que el boletín no publicó.
- [ ] `make test` pasa y `make lint` no agrega errores nuevos.
- [ ] `knowledgebase/current/` (status + bitácora) refleja el corte post-V.3.
      No se commitea `sqlite.db`.

## Slices (orden)

| Slice | Pts | Entrega | Estado |
|---|---|---|---|
| **V.3.1** Revalidar el match persistido | 2 | Re-upsert: el ETL re-corre el matcher y deja `NULL` donde no hay match. Baja las 3 alertas | ✅ |
| **V.3.2** Dedup robusto | 3 | Normalizar organismo (puntuación, tildes, sufijo entre paréntesis) antes de `_dedup_key`; y con identificador fuerte de acto, deduplicar por `(acto, monto)` sin exigir organismo | ⬜ |
| **V.3.3** UI honesta | 3 | Barra de cobertura (sin denominador) + separar `llamado` de compromiso real | ⬜ |

Empezar por **V.3.1**: es el que cambia el titular y no requiere diseño nuevo.
V.3.2 toca el ETL y `presupuesto_matching` — **hacer backup de `sqlite.db` antes**
(el ETL hace `DELETE FROM ejecucion_presupuestaria`).

## Fuera de alcance

- Ingest de mayo–diciembre 2026 (la cobertura sigue hasta abril).
- Tercera barra "pagado CGE".
- Scraper SIGAF acto a acto.
- Silenciar alertas >100% reales: si tras V.3.1 queda alguna, se muestra.
- Recall de extracción (44,4%) y DT-7 (residual de lint).
- Re-entrenar el LLM.

## DoR de esta sesión

- [x] Historia en `knowledgebase/backlog/` con criterio de aceptación
- [x] Estimación (8 pts, 3 slices)
- [x] Diagnóstico medido, no supuesto (bitácora regenerada + queries)
- [x] Criterio testeable
- [x] Backup de `sqlite.db` (`watcher-backend/sqlite.bak.db`, ignorado por git)
- [ ] Working tree limpio antes de ramificar

## Riesgo principal

`sqlite.db` es la **única copia** y no está versionada (por diseño). El ETL de
V.3.1 borra y reconstruye `ejecucion_presupuestaria` entera. Backup hecho; si el
re-upsert empeora las cosas, el rollback es copiar `sqlite.bak.db` sobre `sqlite.db`.
