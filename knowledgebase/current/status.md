# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-14
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> Rama activa al cerrar sesión: `main` (P.7 mergeada). Próxima historia: [V.1](../backlog/V.1-verificar-pipeline-vs-realidad.md). Handoff: [next-session.md](next-session.md).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 + P.7 |
| Estado | Núcleo e2e en código; runtime local-first en development |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (default en development si `OLLAMA_BASE_URL`) |
| Pendiente inmediato | **V.1.1** inventario calendario vs DB |

---

## Estado por épica

| Épica | Estado | Notas |
|---|---|---|
| Épica 0: Migración Gemini | Hecho | Reindex operativo Google aún pendiente si se sigue en 3072-d |
| Épica 1: Ingesta | Hecho (parcial) | Transform provincial ahora paralelo (nproc-2) |
| Épica 2: Extracción | Hecho | Free / Pro / **LocalPro** |
| Épica 3: Feature Engineering | Hecho | Sin cambios en H.1 |
| Épica 4–5: Índice / retrieval | Hecho | Rerank local-first; colección local separada |
| Épica 6: Agentes | Hecho | Sin cambios de canales |
| Épica 7: Prod | En curso | H.1; CI/auth/UI huérfana siguen abiertos |
| H.1 Hardware local | Hecho | Workers nproc-2, overlay Compose, LocalPro, embeddings/rerank locales |
| Épica P: Presupuesto | P.1–P.7.4 en `main` | Ledger + Ley 11.088 + UI `%` vs vigente |
| Épica V: Ground truth | V.1 refinado | Calendario, gold set, mes cerrado, Ley, trimestral CGE |

---

## Ledger de gasto público (2026-09-14, post P.7.4)

De 1.680 actos con monto, **131 son gasto público**. `presupuesto_base` 2026: **480 programas**. Match 90/131. La UI separa compromiso (~$188,3 mil M) de ejecución (~$0,23 mil M). EPEC 2,87% del vigente. Un falso positivo (S-511 → `DIRECCIÓN DE MINISTERIO`) dispara la alerta &gt;100%.

Montos de presupuesto en API van en **millones de ARS** (el frontend escala a pesos). No commitear `sqlite.db`.

Ver [P.7](../backlog/P.7-gasto-acumulado-presupuesto.md).

---

## Bloqueos

Ninguno de producto para arrancar V.1. Notion MCP no disponible — el tablero quedó sin actualizar.

---

## Deuda técnica conocida

1. Re-indexado operativo Chroma (Google o local) contra corpus real.
2. `ProvincialPipeline.extract()` no descarga; sigue en `sync_service`.
3. Fixture async de `indexing_service` (6 tests fallan; DT-2).
4. DS Lab scoring a nivel documento vs per-acto.
5. CI (`requirements.txt`, Py 3.10, tests `continue-on-error`).
6. UI v2 sin compliance / menciones / jurisdicciones / mapa.
7. 6 módulos de test no colectan: `watcher_monolith` / `kba_agent` no existen. `test_reindex_embeddings.py` rompe la colección entera porque `reindex_google_embeddings.py` hace `sys.exit(1)` al importarse sin `GOOGLE_API_KEY`.
8. `ruff check .` da 2.668 errores de base (config `[tool.ruff]` de `pyproject.toml` no se aplica con ruff 0.16; usa los defaults). `make lint` no pasa desde antes de P.7.

---

## Próximos pasos

1. **V.1.1** inventario calendario boletinoficial.cba.gov.ar vs `boletines`.
2. V.1.2 gold set (12 PDFs) antes de completar abr–dic 2026.
3. UI huérfana y CI (paralelo, no bloquean V.1).
