# Estado Actual — Watcher Agent

**Última actualización:** 2026-09-13
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> Rama activa: `main` (H.1 mergeado). Próxima sesión: [P.7](../backlog/P.7-gasto-acumulado-presupuesto.md) — [handoff](next-session.md).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 (pipeline hardware local) |
| Estado | Núcleo e2e en código; runtime local-first en development |
| Stack LLM | Gemini (cloud) + LocalPro/Ollama (default en development si `OLLAMA_BASE_URL`) |
| Pendiente inmediato | P.7.1+P.7.2 ledger gasto vs presupuesto (ver next-session.md) |

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
| Épica P: Presupuesto | Hecho + P.7 idea | Código P.1–P.6; ledger vacío en SQLite local |

---

## Corte gasto público (2026-09-13)

5.667 actos en `analisis`; **$458,4 mil M** brutos de `monto_numerico`; **$315,4 mil M** en tipos de gasto deduplicados. Un pliego (S-511) republicado 8 veces = 44% del bruto. `presupuesto_base` y `ejecucion_presupuestaria` = 0 filas. Ver [gasto-publico-actos.md](gasto-publico-actos.md) y P.7.

---

## Bloqueos

Ninguno activo. Notion MCP no disponible en la sesión que abrió H.1.

---

## Deuda técnica conocida

1. Re-indexado operativo Chroma (Google o local) contra corpus real.
2. `ProvincialPipeline.extract()` no descarga; sigue en `sync_service`.
3. Fixture async de `indexing_service`.
4. DS Lab scoring a nivel documento vs per-acto.
5. CI (`requirements.txt`, Py 3.10, tests `continue-on-error`).
6. UI v2 sin compliance / menciones / jurisdicciones / mapa.

---

## Próximos pasos

1. **P.7.1 + P.7.2** — clasificar `is_gasto_publico` y escribir `ejecucion_presupuestaria` al cerrar el pipeline. Handoff: [next-session.md](next-session.md).
2. P.7.3 cargar Ley 11.088; P.7.4 UI `%` vs `monto_vigente`.
3. Reintentar S1/S3 del 2026-09-01 (sin actos en analisis).
4. UI huérfana y CI.
