# V.3 Honestidad del contraste

**Épica:** V — Verificación / ground truth (capa B: ledger vs Ley)
**Puntos:** 8 (tomar por slices)
**Estado:** hecho — V.3.1 ✅ · V.3.2 ✅ · V.3.3 ✅
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

### H4 — CORREGIDO: el par de $34.026.000.000 NO es una duplicación

> **Corrección (2026-09-18, al mirar el texto y no sólo el monto).** Afirmé acá
> que estas dos filas eran el mismo acto contado dos veces y que colapsarlas
> cerraba la última alerta. **Es falso.** Son dos obras distintas:

| fila | organismo | acto | qué es |
|---|---|---|---|
| id=399 | SECRETARIA DE ASUNTOS INSTITUCIONALES | `Licitación Pública N° 660649` | "plataforma de trabajo en altura para el Área de Infraestructura del Poder Judicial" |
| id=411 | Secretaría General de la Gobernación - Ministerio de Economía y Gestión Pública | `Licitación Pública EXPEDIENTE N° 0378-219684/2026` | "adquisición de leche en polvo y contratación de servicio de logística y cadetería" |

Comparten el monto al peso y nada más. Lo que parece un problema de dedup es un
problema de **atribución del monto**: $34.026.000.000 por una plataforma de
trabajo en altura es absurdo; por leche en polvo y logística para una provincia
es plausible. Al menos una de las dos filas tiene el monto mal extraído, y eso es
un problema de **extracción** (fuera de alcance de V.3, como el recall).

Lección de método: agrupar por monto y concluir "misma obra" es un atajo que
falla. El texto es el que decide. Este error de diagnóstico sobrevivió una sesión
entera porque comparé números sin leer las descripciones.

### H5 — La duplicación que el acto no puede ver: código de obra

Hay obras que el boletín republica con **otro número de acto**, así que ni
normalizando el organismo se juntan. Pero todas citan el **código de obra**
(`S-511`, `S-283`), que sí sobrevive a la republicación:

| familia | filas | canónicas antes | monto real |
|---|---:|---:|---:|
| `S-511` (caminos, Las Peñas Sud – Las Isletillas) | 7 | **4** | $25.341.354.989 |
| `S-283` (mejora camino, Gral. Roca) | 3 | **3** | $16.064.411.752 |

En S-511 conviven dos identificadores (`S-511` y `RESOLUCION 056/2026`) bajo
cuatro organismos distintos, cada fila con el monto completo: la barra de
compromiso cargaba **$101,37B por una obra de $25,34B**. La familia S-283
($32,13B contados por una obra de $16,06B) no aparecía en ningún diagnóstico
previo porque todas sus filas tienen el mismo organismo — el acto era lo único
distinto.

#### Por qué la capa nueva es por código de obra y no por similitud de texto

El primer diseño que consideré fue "mismo monto + texto parecido → misma obra".
**Es peligroso y lo descarté con datos.** EPEC publicó "ZONA III SUROESTE" y
"ZONA IV SURESTE" con el **mismo** $4.623B y textos que difieren en dos palabras:
cualquier umbral de Jaccard las fusiona, y son licitaciones distintas (verificado
leyendo ambas). La clave por acto las separa bien (`5558` ≠ `5560`).

El código de obra no tiene ese modo de falla: sólo existe cuando el boletín nombra
la obra. Los textos de las ZONA III/IV no contienen código, así que la capa nueva
no los toca. Medido: la capa produjo **2 grupos en todo el corpus**, ambos
correctos, y ningún organismo distinto se fusionó.

### H4bis — La alerta que sobrevive no es de dedup ni de match

Tras V.3.1 y V.3.2 queda **1** alerta, `MINISTERIO DE ECONOMÍA MINISTERIO Y
GESTIÓN PÚBLICA` 145,25% ($34.450.820.322 / $23.718.656.000), y su monto **no
cambió** con el dedup. Su causa: id=411 ($34,03B "leche en polvo") matchea
`substring score=0.53` contra `pb_id=35`, un organismo **trunco** de $1,37B
(programa *16 - APORTES AGENCIA PARA LA*). O sea: un monto real contra un techo
que no es un techo.

No se silencia (regla de la historia). Queda visible como lo que es —
**denominador trunco**, no sobre-ejecución— y se documenta acá. Cerrarla requiere
decidir si `MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA` es un organismo
o un stub del parser de Mapas (`is_truncated_organismo` hoy lo acepta porque sus
tokens distintivos no están vacíos). Es una decisión de modelo, no de dedup.

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

## Resultado V.3.2 — dedup robusto (2026-09-18)

Dos cambios en `presupuesto_matching.py`, compartidos por el ETL y el ledger vivo:

1. **Organismo canónico en la clave.** `_resolve_alias()` (tabla de alias +
   colapso de sufijo societario/paréntesis) se extrajo de `match_organismo` y
   ahora alimenta también `_dedup_organismo()`. Matcher y dedup coinciden en
   cuándo dos grafías son el mismo organismo. El comportamiento de
   `match_organismo` no cambió (refactor puro, cubierto por los tests de V.2).
2. **Capa por código de obra.** `dedup_keys()` devuelve una lista de claves
   (acto y/u obra); una fila es duplicada si **cualquiera** coincide. La clave de
   obra es `("OBRA", código, monto_redondeado)`.

| Métrica | V.3.1 | V.3.2 parte A | V.3.2 parte B |
|---|---:|---:|---:|
| Filas canónicas provinciales | 369 | 351 | **346** |
| Compromiso medido | $704,78B | $646,59B | **$538,44B** |
| Gasto provincial sin denominador | $212,28B | $212,28B | **$104,13B** |
| Alertas `sobre_compromiso` | 1 | 1 | **1** |
| Deriva de match | 0 | 0 | **0** |

**Doble conteo eliminado en V.3.2: $166,34B** ($704,78B → $538,44B), 23 filas
canónicas de menos. Parte A colapsó las republicaciones con grafía distinta
(EPEC con/sin `(EPEC)`, Poder Judicial, `acto=1255`, `acto=1243`); parte B las
familias por código de obra (S-511: 4 → 1 fila, $25,341B **no** $101,37B; S-283:
3 → 1 fila, $16,064B). Los $108,15B de la parte B salieron del **compromiso**:
eran montos inflados, no gasto sin denominador.

Verificación de que la capa no se pasó de larga: produjo **2 grupos** en todo el
corpus, ambos revisados leyendo las descripciones. Las ZONA III/IV de EPEC
(mismo monto, texto casi idéntico, licitaciones distintas) **no** se fusionaron.
El par de $34.026B **tampoco**, y está bien que no: no es una duplicación (H4).

Cumulative: el dedup pasó de ver el acto a ver el organismo y la obra. Lo que
**no** puede ver —y por eso queda documentado y no silenciado— es un monto mal
extraído.

## Resultado V.3.3 — UI honesta (2026-09-18)

Dos cambios en el contrato del endpoint (aditivos: ningún campo cambió de
significado, así que ninguna alerta se retiró por la puerta de atrás) y tres en
la pantalla.

**1. La lista ya no esconde lo que no tiene denominador.** `por_organismo` siempre
devolvió los organismos sin match (`matched=false`, `monto_vigente=null`); el
filtro `filter(item.matched)` de `organismo-contrast.tsx` los borraba. Ahora la
lista muestra **47 organismos: 17 con denominador y 30 sin**, y una barra de
cobertura arriba:

| Métrica | Valor |
|---|---:|
| Gasto medido (canónico provincial) | $501,85B |
| Con denominador | $397,72B · 79,25% |
| **Sin denominador** | **$104,13B · 20,75% · 53 actos** |

**2. "Compromiso" dejó de mentir.** El hallazgo más grande de V.3, y no lo
habíamos medido: de los $397,08B publicados contra un denominador, **$397,08B
son `llamado`** — llamados a licitación, o sea intención. El compromiso asumido
(adjudicación + contrato) es **$0,55B = 0,14%**. La barra ámbar rotulada
"Compromiso" sobreafirmaba el compromiso real por un factor de ~720×, en todos
los organismos menos dos.

| Organismo (top) | publicado | de eso, llamado | comprometido |
|---|---:|---:|---:|
| EPEC | $180,9B | $180,9B | $0,0B |
| ACIF | $151,6B | $151,6B | $0,0B |
| MINISTERIO DE ECONOMÍA | $34,5B | $34,0B | $0,4B |
| PODER JUDICIAL | $17,6B | $17,6B | $0,0B |
| **TOTAL (con denominador)** | **$397,1B** | **$397,1B (99,86%)** | **$0,55B (0,14%)** |

La pantalla ahora muestra tres barras: **Publicado** (llamado + adjudicación +
contrato), **Comprometido** (sólo adjudicación + contrato) y **Ejecución**
(pagos), con la línea "de ese total, $X es sólo llamado".

Decisión de diseño: `monto_llamado` se **informa, no se resta** del bucket
`compromiso`. Restarlo habría cambiado el %, el umbral y por lo tanto las
alertas — es decir, habría retirado alertas cambiando una definición, que es
exactamente lo que la regla "no silenciar alertas >100% reales" prohíbe. La
alerta de 145,25% sigue viva y sigue significando lo mismo; lo que cambió es que
el ciudadano ahora ve que $34,0B de esos $34,5B son intención.

## Criterio de aceptación (epígrafe)

- [x] **Ninguna fila canónica conserva un `presupuesto_base_id` que el matcher
      actual no asigne.** 18 filas con deriva → **0**. Gate:
      `scripts/check_match_drift.py` (exit 1 si hay deriva).
- [x] **Las 3 alertas artefacto desaparecen** de `bitacora-alertas-v2-post.md` con
      el re-upsert corrido. Queda **1**, y no es artefacto de match ni de dedup:
      es un **denominador trunco** sobre un monto real (H4bis), con su `pb_id` y
      su score documentados. Se muestra, no se silencia.
- [x] **La obra S-511 cuenta 1 vez ($25,34B), no 4 ($101,37B)**, y `acto=5543`
      cuenta 1 vez ($20,03B), no 2. Tests en `TestDedupKey` y `TestObraCodeDedup`
      (`test_same_obra_different_acto_shares_obra_key`, ids 85/93/97/106) y
      `test_alias_variant_collapses` (ids 95/99). Medido en el ETL: S-511 4 → 1.
- [x] **La UI muestra el gasto sin denominador.** El **20,75% ($104,13B, 53 actos)**
      es visible como cobertura arriba de la lista y como lista propia abajo; el
      filtro `filter(item.matched)` se eliminó. No se inventó un denominador: los
      sin-denominador se muestran sin %.
- [x] **Compromiso ≠ llamado.** La UI separa `llamado` (intención) de
      `adjudicación + contrato` (compromiso real: **$0,55B = 0,14%**). Sin esto la
      barra ámbar afirmaba un compromiso que el boletín no publicó, por ~720×.
- [x] `make test` pasa y `make lint` no agrega errores nuevos. Suite: **652
      passed / 15 failed / 7 skipped** — los 15 son DT-2/DT-3 pre-existentes,
      verificados por A/B con `git stash`. Lint backend **642 antes y después**
      (A/B); frontend 0 errores. `make` no existe en este entorno, así que se
      corrieron los targets (`ruff check .`, `npm run lint`) directamente.
- [x] `knowledgebase/current/` (status + bitácora) refleja el corte post-V.3.
      No se commitea `sqlite.db`.

## Slices (orden)

| Slice | Pts | Entrega | Estado |
|---|---|---|---|
| **V.3.1** Revalidar el match persistido | 2 | Re-upsert: el ETL re-corre el matcher y deja `NULL` donde no hay match. Baja las 3 alertas | ✅ |
| **V.3.2** Dedup robusto | 3 | Organismo canónico (`_resolve_alias`) en la clave + capa por código de obra. Eliminó **$166,34B** de doble conteo (369 → 346 filas) | ✅ |
| **V.3.3** UI honesta | 3 | Barra de cobertura (sin denominador) + tres barras: publicado / comprometido / ejecución | ✅ |

Empezar por **V.3.1**: es el que cambia el titular y no requiere diseño nuevo.
V.3.2 toca el ETL y `presupuesto_matching` — **hacer backup de `sqlite.db` antes**
(el ETL hace `DELETE FROM ejecucion_presupuestaria`).

## Fuera de alcance

- Ingest de mayo–diciembre 2026 (la cobertura sigue hasta abril).
- Tercera barra "pagado CGE".
- Scraper SIGAF acto a acto.
- Silenciar alertas >100% reales: si tras V.3.1 queda alguna, se muestra.
- **Corregir montos mal extraídos** (H4: $34,026B sobre "plataforma de trabajo en
  altura"; H4bis: denominador trunco `pb_id=35`). Se documentan y se muestran;
  arreglarlos es trabajo de extracción y de modelo de organismo, no de contraste.
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
