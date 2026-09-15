# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-15
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> Rama activa: `feature/V.1-verificar-pipeline-vs-realidad`. Handoff: [next-session.md](next-session.md). Próxima historia: [V.2](../backlog/V.2-matching-denominador.md).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 + P.7 + V.1 |
| Estado | V.1 hecho; abril 2026 cerrado en DB; **siguiente = V.2 matching** |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (`qwen2.5:7b`) |
| Pendiente inmediato | V.2.1 bitácora de las 4 alertas >100%. Mergear V.1 **sin** `sqlite.db`. |

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
| Épica V: Ground truth | V.1 hecho; V.2 refinada | Matching/denominador |

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
| UI | [corte-abril-ui.md](corte-abril-ui.md) — $703.7B compromiso / $1.1B ejecución; 4 alertas >100% |

No commitear `sqlite.db`.

---

## Ledger de gasto público (2026-09-15)

La UI sigue separando compromiso de ejecución. El % vs Ley es **legible** en EPEC (9.1%) y ACIF (26.3%). Las alertas Secretaría de Desarrollo 2703%, Economía 145%, Dirección de Ministerio 295% (S-511), Poder Judicial 163% son **matching/denominador**, no sobre-ejecución de caja.

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
7. 6 módulos de test no colectan: `watcher_monolith` / `kba_agent` no existen. `test_reindex_embeddings.py` rompe la colección entera porque `reindex_google_embeddings.py` hace `sys.exit(1)` al importarse sin `GOOGLE_API_KEY`.
8. `ruff check .` da 2.668 errores de base (config `[tool.ruff]` de `pyproject.toml` no se aplica con ruff 0.16). `make lint` no pasa desde antes de P.7.

---

## Próximos pasos

1. **V.2** matching y denominador (las 4 alertas). No mayo+ hasta que el % sea defendible.
2. Mergear V.1 **sin** `sqlite.db`.
3. CGE T2 cuando Hacienda publique (contraste aparte, no tercera barra).
4. UI huérfana y CI (paralelo).
