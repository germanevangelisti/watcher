# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-18
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> **V.2 mergeada a `main`** (`7a366b0`) el 2026-09-18, sin `sqlite.db`: el binario se dio de baja del índice (`git rm --cached`) porque estaba trackeado pese a `*.db` en `.gitignore`. Handoff: [next-session.md](next-session.md).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 + P.7 + V.1 + V.2 |
| Estado | V.2 hecho; 0 alertas >100% en el corte abril |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (`qwen2.5:7b`) |
| Pendiente inmediato | Mergear V.2 **sin** `sqlite.db`. Mayo+ opcional. |

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
| Épica V: Ground truth | V.1 + V.2 hechos | Matching/denominador: 0 alertas >100% |

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
7. ✅ Resuelto (DT-4/DT-5, 2026-09-18): la suite colecta entera. `reindex_google_embeddings.py` ya no hace `sys.exit(1)` al importarse; los 3 módulos con prefijo `watcher_monolith` se revivieron y los 3 de `kba_agent`/`raga_agent` usan `importorskip`. Suite: **15 failed, 637 passed, 7 skipped** (antes 6 errores de colección y ~50 tests que nunca corrían).
8. Lint: causa raíz resuelta (DT-6 — `ruff.toml` tapaba `pyproject.toml`). Deuda real medida: **8.327 → 643 errores**. `make lint` **sigue sin pasar**: el residual (DT-7) es `E501` 439 + `B904` 97 + `N806` 34, sin autofix, diferido a historia propia.

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
| **"Compromiso" es 99,7% `llamado`** | $701.8B de $703.7B son licitaciones publicadas. Compromiso legal real (adjudicación + contrato) = **$1.9B = 0,27%** de la barra |
| **34,7% del gasto no tiene denominador** | unmatched $244.0B / 141 filas vs matched $460.8B / 228 |
| **La barra de ejecución está vacía** | `pago` = $1.115B contra $703.7B de compromiso (57 filas) |
| **Denominador con artefactos** | 29 filas / **$1.09T (14,5% del presupuesto)** con texto en `partida_presupuestaria` (`'Recursos'`, `'Cuentas'`, `''`); caso 755 de Seguridad con fila basura ($94.45B) + fila real ($90.01B) para el mismo programa |
| **Cobertura temporal** | `boletines` hasta 2026-04; hoy 2026-09-18 |
| **Recall de extracción** | 44,4% (gold set) — se mide la mitad de los actos |
