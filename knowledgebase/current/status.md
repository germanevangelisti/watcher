# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-18
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> **V.2 mergeada a `main`** (`7a366b0`) el 2026-09-18, sin `sqlite.db`: el binario se dio de baja del índice (`git rm --cached`) porque estaba trackeado pese a `*.db` en `.gitignore`. Handoff: [next-session.md](next-session.md).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 + P.7 + V.1 + V.2 + V.3 |
| Estado | V.3 hecho (V.3.1/32/33); **1** alerta >100%, documentada como denominador trunco |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (`qwen2.5:7b`) |
| Pendiente inmediato | Mergear la rama V.3 a `main`. Ingesta mayo–septiembre. |

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
| Épica V: Ground truth | V.1 + V.2 + V.3 hechos | El dato persistido y la pantalla ahora dicen lo mismo que el matcher |

---

## Corte V.3 (2026-09-18)

Historia: [V.3-honestidad-contraste.md](../backlog/V.3-honestidad-contraste.md).
Tres slices: revalidar el match persistido, dedup robusto, UI honesta.

| Slice | Qué cambió | Medido |
|---|---|---|
| V.3.1 | El ETL re-corre el matcher: `presupuesto_base_id` deja de ser un campo que nadie revalida | Alertas **3 → 1**; deriva 18 filas/$86,11B → **0** |
| V.3.2 | Dedup por organismo canónico + código de obra | **$166,34B** de doble conteo eliminado; 369 → **346** filas canónicas |
| V.3.3 | Cobertura visible + `llamado` separado de compromiso real | **47** organismos en pantalla (antes 17); $104,13B sin denominador a la vista |

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
7. ✅ Resuelto (DT-4/DT-5, 2026-09-18): la suite colecta entera. `reindex_google_embeddings.py` ya no hace `sys.exit(1)` al importarse; los 3 módulos con prefijo `watcher_monolith` se revivieron y los 3 de `kba_agent`/`raga_agent` usan `importorskip`. Suite: **15 failed, 652 passed, 7 skipped** (los 15 son DT-2/DT-3, pre-existentes; verificado por A/B con `git stash`).
8. Lint: causa raíz resuelta (DT-6 — `ruff.toml` tapaba `pyproject.toml`). Deuda real medida: **8.327 → 642 errores**. `make lint` **sigue sin pasar**: el residual (DT-7) es `E501` 439 + `B904` 97 + `N806` 34, sin autofix, diferido a historia propia. V.3 no agregó ninguno (A/B: 642 antes y después).

---

## Próximos pasos

1. ✅ V.2 mergeada a `main` sin `sqlite.db` (2026-09-18).
2. **Honestidad del contraste** — el número que muestra la UI no es el que dice ser (ver *Hallazgos del corte*, abajo).
3. Sanear `presupuesto_base`: el denominador tiene basura del parser.
4. Ingesta mayo–septiembre: el producto muestra abril y hoy es septiembre.
5. DT-7 (residual de lint) e ingest CGE T2 cuando Hacienda publique.

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
