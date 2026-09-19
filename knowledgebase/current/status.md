# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-19
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> **V.5 cerrada** (2026-09-19): el producto pasa de medir **3 a 8 meses** (feb–sep).
> Extracción cerrada (`ok=469 fail=0`), ledger reconstruido, gate de drift en 0.
> **No cambió una línea de código**: es una operación sobre `sqlite.db`.
> Handoff: [next-session.md](next-session.md).
>
> **V.4 mergeada a `main`** (2026-09-18): el cociente deja de mentir por período y por
> techo. Handoff: [next-session.md](next-session.md).
>
> Contexto: V.3 (`4a28e2e`) ya está en `main`; V.2 se mergeó en `7a366b0` sin
> `sqlite.db` (el binario se dio de baja del índice con `git rm --cached` porque
> estaba trackeado pese a `*.db` en `.gitignore`).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 + P.7 + V.1 + V.2 + V.3 + V.4 + V.6 + V.5 |
| Estado | **V.5 hecha (2026-09-19)**: 8 de 12 meses medidos; **3** alertas >100%, todas con causa medida |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (`qwen2.5:7b`) |
| Pendiente inmediato | **2026-01** es el único mes vencido sin ingesta. Después: V.7 (columnas del extractor) y V.8 (monto del aviso vecino), que necesitan re-extracción y son decisión de costo. |

---

## Estado por épica

| Épica | Estado | Notas |
|---|---|---|
| Épica 0: Migración Gemini | Hecho | Reindex operativo Google aún pendiente si se sigue en 3072-d |
| Épica 1: Ingesta | Hecho (parcial) | Transform provincial ahora paralelo (nproc-2); **feb–sep ingeridos, 2026-01 no** |
| Épica 2: Extracción | Hecho | Free / Pro / **LocalPro**; gold set recall 44.4% |
| Épica 3: Feature Engineering | Hecho | Sin cambios en H.1 |
| Épica 4–5: Índice / retrieval | Hecho | Rerank local-first; colección local separada |
| Épica 6: Agentes | Hecho | Sin cambios de canales |
| Épica 7: Prod | En curso | H.1; CI/auth/UI huérfana siguen abiertos |
| H.1 Hardware local | Hecho | Workers nproc-2, overlay Compose, LocalPro |
| Épica P: Presupuesto | P.1–P.7.4 en `main` | Ledger + Ley 11.088 + UI dos barras |
| Épica V: Ground truth | V.1 … V.6 hechos | El dato persistido y la pantalla dicen lo mismo que el matcher; el cociente declara período y techo; **y ahora el período es feb–sep** |

---

## Corte V.5 (2026-09-19)

Historia: [V.5-ingesta-mayo-septiembre.md](../backlog/V.5-ingesta-mayo-septiembre.md).
Ingesta de los 5 meses vencidos. **Sin cambios de código**, así que los gates de
DoD miden el árbol tal como estaba.

| | antes | después |
|---|---|---|
| Meses medidos | 3 de 12 (feb–abr) | **8 de 12 (feb–sep)** |
| Días faltantes | 0 | **0** |
| Boletines may–sep | 372 `pending` | **472 `completed` / 33 `justified:` / 0 en vuelo** |
| Ledger | 430 filas · $538,44B canónicos | **1220 filas · 972 canónicas · $1.776,41B** |
| Alertas >100% | 5 (2 de extracción) | **3**, ninguna nueva |
| Gasto sin denominador | $140,72B / 140 actos | **$404,52B / 364 actos** |
| Techo (Ley 11.088) | $7,531907T · 0 sin dueño | **$7,531907T · 0 sin dueño** (idéntico) |
| Gate de drift | exit 1 · 9 filas · $14,30B | **exit 0 · 0 filas** |

**Titular del corte:** el ciudadano veía **3 meses de gasto divididos por la Ley de
12**. Ahora ve **8**, con el mismo techo anual y sin prorratear la Ley (regla de
V.4). Las dos alertas >100% que **desaparecen** eran defectos de extracción con
reparación probada contra el PDF; las **3 que quedan** son estructurales
(granularidad del denominador) y siguen a la vista, no silenciadas.

**Corrección a números ya publicados (declarada, no silenciosa):** feb–abr baja de
**$538,44B a $519,57B** canónicos (**−$18,87B**). No lo causa la ingesta: es la
dedup de V.6 sobre licitaciones republicadas, que hasta ahora sólo corría al
reconstruir el ledger por lotes. Sobre el corpus final el A/B de V.6 da
**−$313,32B** en total (julio −$240,65B, de los cuales **$237,29B son un solo acto
de EPEC contado dos veces**, la licitación 5576). Los tres meses publicados dan
idéntico al centavo que en la medición parcial de V.6.

**Predicciones escritas antes de medir, y su veredicto:** 6 de 8 se cumplen. Las
dos que fallan tienen causa medida y **ninguna expectativa se ajustó**: la caída
del canónico se había derivado mal ($2.990,14B contra $3.299,79B reales, porque
omitía la dedup) y "feb–abr no se mueve" era falso contra un snapshot que no
distinguía ingesta de dedup. Ambas quedaron escritas como fallas en la historia.

**Lo que queda declarado y no arreglado:**
1. **2026-01** es el único mes vencido sin ingesta (anterior al período que el
   producto declara).
2. **123 boletines `completed` perdieron su PDF** en disco. El **texto** de los 123
   está en `chunk_records` (123/123), así que la auditoría por texto es corpus-wide;
   lo que no se puede re-verificar es la **geometría** (columnas).
3. **V.7** (fuga de monto entre columnas) y **V.8** (el monto del aviso vecino en el
   modelo) son historias abiertas, con el caso catastrófico de V.8 reparado contra
   el PDF ($3,0B en una fila, 62% del corte de ese momento). Arreglarlas obliga a
   **re-extraer**: decisión de costo explícita.
4. **$404,52B sin denominador** (364 actos): entidades que no están en la Ley,
   fuera de alcance por diseño, o el matcher. Tiene causas por organismo medidas.
5. DT-7 (lint, 642) y los 15 tests pre-existentes (DT-2/DT-3).

**DoD medido (sin `make`):** tests **15 failed / 670 passed / 7 skipped** — los 15
en los mismos 5 archivos de DT-2/DT-3, cero nuevos (y no podían serlo: no se tocó
código); los `passed` suben de 663 a 670 por los tests que **V.6** agregó.
Lint **642 errores = DT-7**, cero nuevos.



---

## Corte V.4 (2026-09-18)

Historia: [V.4-limites-del-cociente.md](../backlog/V.4-limites-del-cociente.md).
Tres slices: declarar el período, declarar el techo sin dueño, recuperar los nombres.

| Slice | Qué cambió | Medido |
|---|---|---|
| V.4.1 | El % declara su período y su calendario | "3 de 12 meses" (feb–abr) contra la **Ley anual**; 58 días publicados + 2 feriados justificados, **0 faltantes** |
| V.4.2 | El techo se parte en verificable y sin dueño | $706,6B / **74 programas (9,38%)** separados del techo verificable ($6,825T). El % no se toca |
| V.4.3 | Los nombres perdidos se recuperan de la fuente | **74 truncos → 0**; denominador sin dueño **9,38% → 0%**; alertas **1 → 0** |

**Titular del corte:** el `%` que ve el ciudadano dividía **3 meses de gasto por la
Ley de 12** y nadie lo decía, y el techo contra el que dividía incluía **$706,6B
(9,4%) de presupuesto cuyo organismo el parser había perdido**. Ninguna de las dos
cosas era un error de datos: eran límites sin declarar. Ahora la pantalla dice el
período, dice el techo verificado y lista los programas sin dueño.

**La última alerta, resuelta con medición:** el 145,25% de V.3 se apoyaba en
`MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA`, un nombre que el parser
armó pegando la unidad de organización con la cola de la jurisdicción. Reparado a
`MINISTERIO DE ECONOMIA Y GESTION PUBLICA` (su jurisdicción real, la que declara el
PDF), su techo pasó de $23,72B a **$80,86B** y el mismo acto de $34,45B da
**42,61%**. El numerador nunca se movió. **No se silenció: se midió y se declaró.**

Reparo (`--repair-db`), con backup y diff fila por fila: 480 filas → 480, ids
idénticos, total **$7,531907T idéntico**, 375 rótulos de organismo reescritos. De
los 89 organismos del contraste, **exactamente uno** cambia de denominador (el
fantasma). Los otros 294 son re-normalizaciones sin acentos que no mueven ningún %, y
el docstring del flag ahora declara ese alcance.

**Lo que no se pudo recuperar, y por qué:** la unidad ejecutora exacta está en el PDF
pero repartida en 2–3 líneas de la misma celda, y el agrupado por tolerancia tira la
tercera. Dos reagrupados alternativos movían el total entre **$3,2T y $3,5T** —
descartados. La jurisdicción es el dueño más preciso que la fuente sostiene.

**Lo que queda declarado y no arreglado:** el gasto sin denominador sigue en
**$140,72B / 140 actos** (26,13% del medido); la ejecución (pagos) sigue siendo
$1,12B; y faltan **5 meses** de ingesta (may–sep) — eso es la etapa siguiente.

---

## Corte V.3 (2026-09-18)

Historia: [V.3-honestidad-contraste.md](../backlog/V.3-honestidad-contraste.md).
Tres slices: revalidar el match persistido, dedup robusto, UI honesta.

| Slice | Qué cambió | Medido |
|---|---|---|
| V.3.1 | El ETL re-corre el matcher: `presupuesto_base_id` deja de ser un campo que nadie revalida | Alertas **3 → 1**; deriva 18 filas/$86,11B → **0** |
| V.3.2 | Dedup por organismo canónico + código de obra | **$166,34B** de doble conteo eliminado; 369 → **346** filas canónicas |
| V.3.3 | Cobertura visible + `llamado` separado de compromiso real | **47** organismos en pantalla (antes 17); $104,13B sin denominador a la vista |

> **Superado por V.4:** la "1 alerta >100%" del cierre de V.3 (145,25% en
> MINISTERIO DE ECONOMÍA) ya no existe, y el motivo está medido: el denominador no
> era un stub de $1,37B sino un **nombre fantasma** del parser (5–6 filas,
> $23,72B). Reparado el nombre, el techo real es $80,86B y el mismo acto da
> **42,61%**. El numerador nunca se tocó. Ver *Corte V.4*.

**Titular del corte:** el gasto medido es **$501,85B**, de los cuales **$397,72B
(79,25%) tiene denominador** y **$104,13B (20,75%, 53 actos) no**. De lo que tiene
denominador, **99,86% es `llamado`** — licitación publicada, no compromiso
asumido—; el compromiso real (adjudicación + contrato) es **$0,55B (0,14%)**. La
barra ámbar rotulada "Compromiso" sobreafirmaba el compromiso por ~720×; la
pantalla ahora muestra Publicado / Comprometido / Ejecución por separado.

Nuevo gate: `scripts/check_match_drift.py` (read-only, exit 1 si el matcher vivo
discrepa del `presupuesto_base_id` persistido).

Queda **1** alerta >100% (MINISTERIO DE ECONOMÍA, 145,25%). **No se silencia:** el
denominador es un stub trunco de $1,37B (`pb_id=35`) y el monto es real. Ver H4bis
en la historia.

---

## Cortes V.1 (2026-09-14)

| Slice | Evidencia |
|---|---|
| V.1.1 | [cobertura-calendario.md](cobertura-calendario.md) — 188/188 slots publicados feb–mar `completed` |
| V.1.2 | [goldset.md](goldset.md) — 12 PDFs / 18 actos; recall 44.4%; MAE 0%; S4 con número 6/13 |
| V.1.3 | Marzo 98/98 `completed`; lote 7B `ok=48 fail=0`; ledger `stable=True` |
| V.1.4 | [ancla-ley-11088.md](ancla-ley-11088.md) — EPEC/ACIF = JSON |
| V.1.5 | [cge-trimestral.md](cge-trimestral.md) — T1 2026 vs 8 organismos |

## Corte abril (2026-09-15)

| Campo | Valor |
|---|---|
| Ingesta | `ingest_month.py --month 202604` → 98 filas (12 slots lun–vie no publicados / feriado) |
| Extracción | `process_pending.py --month 202604`: S4 20/20; mes 98/98 `completed` |
| Scripts | `lote_status.py`, `ingest_month.py`, `process_pending.py` |
| UI | [corte-abril-ui.md](corte-abril-ui.md) — $703.7B compromiso / $1.1B ejecución; **0 alertas >100%** (V.2) |

No commitear `sqlite.db`.

---

## Ledger de gasto público (2026-09-15)

La UI sigue separando compromiso de ejecución. El % vs Ley es **legible** en EPEC (9.1%), ACIF (26.4%), Economía (42.6%) y Poder Judicial (17.6%). S-511 / Inteligencia Fiscal y Secretaría de Asuntos Institucionales quedan unmatched explícitos. La alerta >100% no se silenció: dejó de disparar porque el denominador y el match son los correctos.

Ver [P.7](../backlog/P.7-gasto-acumulado-presupuesto.md), [V.1](../backlog/V.1-verificar-pipeline-vs-realidad.md), [V.2](../backlog/V.2-matching-denominador.md).

Montos de presupuesto en API van en **millones de ARS** (el frontend escala a pesos).

---

## Bloqueos

Ninguno de producto. Notion MCP no disponible — el tablero quedó sin actualizar.

---

## Deuda técnica conocida

1. Re-indexado operativo Chroma (Google o local) contra corpus real.
2. `ProvincialPipeline.extract()` no descarga; sigue en `sync_service`.
3. Fixture async de `indexing_service` (6 tests fallan; DT-2).
4. DS Lab scoring a nivel documento vs per-acto.
5. CI (`requirements.txt`, Py 3.10, tests `continue-on-error`).
6. UI v2 sin compliance / menciones / jurisdicciones / mapa.
7. ✅ Resuelto (DT-4/DT-5, 2026-09-18): la suite colecta entera. `reindex_google_embeddings.py` ya no hace `sys.exit(1)` al importarse; los 3 módulos con prefijo `watcher_monolith` se revivieron y los 3 de `kba_agent`/`raga_agent` usan `importorskip`. Suite tras **V.5** (2026-09-19): **15 failed, 670 passed, 7 skipped**; los 15 son los mismos 5 archivos pre-existentes de siempre (DT-2/DT-3), cero nuevos — y no podían serlo, V.5 no tocó código. Los `passed` suben de 663 (V.4) a 670 por las **70 líneas de test que agregó V.6** (commit `5cd4cc9`, verificado en el `--stat`), posterior al cierre de V.4.
8. Lint: causa raíz resuelta (DT-6 — `ruff.toml` tapaba `pyproject.toml`). Deuda real medida: **8.327 → 642 errores**. `make lint` **sigue sin pasar**: el residual (DT-7) es `E501` 439 + `B904` 97 + `N806` 34, sin autofix, diferido a historia propia. Ni V.3, ni V.4, ni V.5/V.6 agregaron ninguno (V.5 da **642** excluyendo el scratch: idéntico a la línea base). **Y ojo con el verde falso:** el target `make lint` corre `ruff check .` envuelto en `command -v ruff || echo "⚠️ ruff not installed"`, así que **pasa en vacío** cuando el binario no está en el PATH. Un `make lint` verde no prueba nada por sí solo.

---

## Próximos pasos

1. ✅ V.2 mergeada a `main` sin `sqlite.db` (2026-09-18).
2. ✅ **Honestidad del contraste** (V.3/V.4) — el número que muestra la UI dice su período y su techo.
3. ✅ Saneado (V.4.3): 74 organismos truncos reparados desde la jurisdicción del PDF.
4. ✅ **Ingesta mayo–septiembre** (V.5, 2026-09-19) — de 3 a **8 meses** medidos. Queda **2026-01** como único mes vencido sin ingesta.
5. **V.7** (la fuga de monto entre columnas) y **V.8** (el monto del aviso vecino en el modelo): son la causa de fondo de los peores errores de monto del corpus, están medidos y declarados, y arreglarlos obliga a **re-extraer** — decisión de costo explícita.
6. DT-7 (residual de lint) e ingest CGE T2 cuando Hacienda publique.
7. Tercera barra "pagado CGE" (no mezclar con el BO) sigue fuera de alcance.

---

## Hallazgos del corte (2026-09-18)

Medido sobre el ledger canónico del corte abril (`is_duplicate=0`):

| Hallazgo | Evidencia |
|---|---|
| **"Compromiso" es 99,86% `llamado`** | $397,08B de $397,08B con denominador son licitaciones publicadas. Compromiso legal real (adjudicación + contrato) = **$0,55B = 0,14%** de la barra. *(Corregido por V.3.3; los números pre-dedup eran $701,8B/$703,7B y $1,9B.)* |
| **20,75% del gasto no tiene denominador** | unmatched $104,13B / 53 filas vs matched $397,72B. *(Era 34,7% / $244,0B / 141 filas antes del dedup de V.3.2: parte del "sin denominador" era doble conteo.)* |
| **La barra de ejecución está vacía** | `pago` = $1.115B contra $703.7B de compromiso (57 filas) |
| **Denominador con artefactos** | 29 filas / **$1.09T (14,5% del presupuesto)** con texto en `partida_presupuestaria` (`'Recursos'`, `'Cuentas'`, `''`); caso 755 de Seguridad con fila basura ($94.45B) + fila real ($90.01B) para el mismo programa |
| **Cobertura temporal** | `boletines` hasta 2026-04; hoy 2026-09-18 |
| **Recall de extracción** | 44,4% (gold set) — se mide la mitad de los actos |
