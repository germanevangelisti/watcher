# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-18
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

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
| Release | v2.0.0 + H.1 + P.7 + V.1 + V.2 + V.3 + V.4 |
| Estado | V.4 hecho (V.4.1/42/43); **0** alertas >100%; el % declara su período y su techo |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (`qwen2.5:7b`) |
| Pendiente inmediato | Ingesta mayo–septiembre: el producto mide feb–abr y hoy es septiembre. |

---

## Estado por épica

| Épica | Estado | Notas |
|---|---|---|
| Épica 0: Migración Gemini | Hecho | Reindex operativo Google aún pendiente si se sigue en 3072-d |
| Épica 1: Ingesta | Hecho (parcial) | Transform provincial ahora paralelo (nproc-2) |
| Épica 2: Extracción | Hecho | Free / Pro / **LocalPro**; gold set recall 44.4% |
| Épica 3: Feature Engineering | Hecho | Sin cambios en H.1 |
| Épica 4–5: Índice / retrieval | Hecho | Rerank local-first; colección local separada |
| Épica 6: Agentes | Hecho | Sin cambios de canales |
| Épica 7: Prod | En curso | H.1; CI/auth/UI huérfana siguen abiertos |
| H.1 Hardware local | Hecho | Workers nproc-2, overlay Compose, LocalPro |
| Épica P: Presupuesto | P.1–P.7.4 en `main` | Ledger + Ley 11.088 + UI dos barras |
| Épica V: Ground truth | V.1 + V.2 + V.3 + V.4 hechos | El dato persistido y la pantalla ahora dicen lo mismo que el matcher; y el cociente declara su período y su techo |

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
7. ✅ Resuelto (DT-4/DT-5, 2026-09-18): la suite colecta entera. `reindex_google_embeddings.py` ya no hace `sys.exit(1)` al importarse; los 3 módulos con prefijo `watcher_monolith` se revivieron y los 3 de `kba_agent`/`raga_agent` usan `importorskip`. Suite tras V.4: **15 failed, 663 passed, 7 skipped**; los 15 son los mismos 5 archivos pre-existentes de siempre (DT-2/DT-3), cero nuevos.
8. Lint: causa raíz resuelta (DT-6 — `ruff.toml` tapaba `pyproject.toml`). Deuda real medida: **8.327 → 642 errores**. `make lint` **sigue sin pasar**: el residual (DT-7) es `E501` 439 + `B904` 97 + `N806` 34, sin autofix, diferido a historia propia. Ni V.3 ni V.4 agregaron ninguno (A/B con `git stash`, archivo por archivo).

---

## Próximos pasos

1. ✅ V.2 mergeada a `main` sin `sqlite.db` (2026-09-18).
2. **Honestidad del contraste** — el número que muestra la UI no es el que dice ser (ver *Hallazgos del corte*, abajo).
3. ✅ Saneado (V.4.3): 74 organismos truncos reparados desde la jurisdicción del PDF.
4. **Ingesta mayo–septiembre** — el producto muestra abril y hoy es septiembre. Es la etapa siguiente y la que más mueve la aguja: el gasto medido es un piso de 3 meses.
5. DT-7 (residual de lint) e ingest CGE T2 cuando Hacienda publique.
6. Tercera barra "pagado CGE" (no mezclar con el BO) sigue fuera de alcance.

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
