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
| Pendiente inmediato | Ejecutar el re-indexado operativo de ChromaDB en el entorno con datos reales |

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

1. ~~**Modelo de embeddings inconsistente** (`gemini-embedding-001` vs `text-embedding-004`).~~ ✅ **Resuelto (A1):** `scripts/reindex_google_embeddings.py` ahora reutiliza el modelo canónico (`gemini-embedding-001`, 3072 dims), re-indexa la colección in-place con backup, y comentarios de `embedding_service.py` corregidos. Queda como paso **operativo** correr el re-indexado contra ChromaDB con datos reales.
2. **`ProvincialPipeline.extract()`** descubre PDFs locales; la descarga remota está en `sync_service.download_boletines_task` (no dentro del pipeline).
3. **`indexing_service` tests** fallan por usar `await` sobre una sesión SQLAlchemy síncrona en el fixture (bug de test, no de producción).

---

## 🔮 Próximos pasos

1. Ejecutar el re-indexado operativo de ChromaDB (A1 ya unificó el modelo en código).
2. Auditar y formalizar Épica 3 (Feature Engineering): transparency scoring, red flags, normalización de entidades.
3. Documentar formalmente la vertical de Presupuesto 2026 en el backlog/arquitectura.
4. Medir cobertura de tests y arreglar el fixture async de `indexing_service` para cerrar Épica 7.
