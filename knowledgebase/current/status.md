# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-13
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> Rama activa: `feature/P.7-gasto-acumulado-presupuesto` (P.7.1 + P.7.2 hechas, sin mergear). Próxima sesión: [P.7.3](../backlog/P.7-gasto-acumulado-presupuesto.md) — [handoff](next-session.md).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 (pipeline hardware local) |
| Estado | Núcleo e2e en código; runtime local-first en development |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (default en development si `OLLAMA_BASE_URL`) |
| Pendiente inmediato | P.7.3 cargar Ley 11.088 en `presupuesto_base` (el ledger ya tiene datos, falta el denominador) |

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
| Épica P: Presupuesto | P.1–P.6 + P.7.1/P.7.2 hechos | Ledger vivo y poblado; falta `presupuesto_base` (P.7.3) y UI (P.7.4) |

---

## Ledger de gasto público (2026-09-13, post P.7.1/P.7.2)

De 1.680 actos con monto, **131 son gasto público**: el ledger canónico vale **$205,9 mil M** ($188,5 mil M provinciales) contra $437,8 mil M brutos. Se excluyeron 1.549 actos (S2 judicial, S3 societario, modificaciones de partidas) y se marcaron 19 republicaciones por $87,5 mil M.

**El boletín es casi todo compromiso:** $188,3 mil M en licitaciones/adjudicaciones contra $0,2 mil M de pagos. La UI de P.7.4 tiene que mostrar dos barras.

`presupuesto_base` sigue en 0 filas → el `%` contra `monto_vigente` todavía no se puede calcular. Ver [P.7](../backlog/P.7-gasto-acumulado-presupuesto.md) y el corte previo en [gasto-publico-actos.md](gasto-publico-actos.md).

---

## Bloqueos

**P.7.3 bloqueada:** el PDF del presupuesto 2026 no está en el repo. `watcher-doc/data/2026/` no existe y `watcher-doc/data/` sólo tiene material 2025 (`Ley-de-Presupuesto-L-11014.pdf` = Ley 11.014 de 2025, no la 11.088 de 2026). Hay que descargarlo del portal provincial.

Notion MCP no disponible en esta sesión ni en la que abrió H.1 — el tablero quedó sin actualizar.

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

1. **P.7.3** — cargar Ley 11.088 en `presupuesto_base` + alias ACIF/EPEC. Handoff: [next-session.md](next-session.md).
2. P.7.4 UI `%` vs `monto_vigente` + toggle compromiso/ejecución.
3. Mergear `feature/P.7-gasto-acumulado-presupuesto` a `main`.
4. UI huérfana y CI.
