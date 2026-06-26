# Estado Actual — Watcher Agent

**Última actualización:** 2026-06-26
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> Sincronizado a partir de los commits hasta `da098b7` (changelog v2.0.0 + vertical de presupuesto 2026).

---

## 🏃 Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 — Architecture Overhaul (Fases 0–4 completas) + vertical Presupuesto 2026 |
| Estado | 🟢 Núcleo funcional end-to-end (ingesta → extracción → indexación → retrieval → agentes) |
| Stack LLM | Google Gemini (migración desde OpenAI **completada** en código) |
| Pendiente inmediato | Normalizar modelo de embeddings y re-indexar ChromaDB de forma consistente |

---

## 📊 Estado por épica (vs. código real)

| Épica | Estado | Notas |
|---|---|---|
| Épica 0: Migración Gemini | 🟢 Hecho (1 ajuste) | OpenAI eliminado del backend; falta unificar modelo de embeddings |
| Épica 1: Ingesta | 🟢 Hecho (1 parcial) | ABC + `IngestionRun` + upload SHA256; descarga provincial vive en `sync_service` |
| Épica 2: Extracción / Análisis | 🟢 Hecho | `IntelligenceProvider` (Free/Pro) + `DocumentIntelligenceAgent` |
| Épica 3: Feature Engineering | 🟡 Parcial | Chunking/enricher/transparency repartidos en servicios; sin auditoría detallada |
| Épica 4: Indexación / Búsqueda | 🟢 Hecho | Neo4j (`Entidad`/`Boletin`/`MENCIONADO_EN`) + ChromaDB + FTS5 (triple index) |
| Épica 5: Retrieval / Consulta | 🟢 Hecho | Semantic + Hybrid (RRF) + re-ranking + graph traversal |
| Épica 6: Sistema multi-agente | 🟢 Hecho | Orchestrator + Anomaly + Learning + Insight + Verification |
| Épica 7: Producción / Hardening | 🟢 Mayormente hecho | Suite de tests (~181 pasando), APScheduler, frontend v2 shadcn/ui |
| Presupuesto 2026 (fuera de plan) | 🟢 Hecho | Parser PDF + ETL análisis→ejecución + dedup + API + UI |

---

## 🚧 Bloqueos

*Ninguno activo.*

---

## ⚠️ Deuda técnica conocida

1. **Modelo de embeddings inconsistente:** producción usa `gemini-embedding-001` (3072 dims) mientras `scripts/reindex_google_embeddings.py` usa `text-embedding-004` (768 dims). Hay que unificar y re-indexar ChromaDB.
2. **Comentarios desactualizados** en `embedding_service.py` (aún mencionan `text-embedding-004`).
3. **`ProvincialPipeline.extract()`** descubre PDFs locales; la descarga remota está en `sync_service.download_boletines_task` (no dentro del pipeline).

---

## 🔮 Próximos pasos

1. Unificar el modelo de embeddings y ejecutar re-indexación consistente de ChromaDB.
2. Auditar y formalizar Épica 3 (Feature Engineering): transparency scoring, red flags, normalización de entidades.
3. Documentar formalmente la vertical de Presupuesto 2026 en el backlog/arquitectura.
4. Medir cobertura de tests para cerrar Épica 7.
