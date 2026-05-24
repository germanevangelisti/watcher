# Estado Actual — Watcher Agent

**Última actualización:** 2026-05-24  
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `sprints/`.

---

## 🏃 Sprint en curso

| Campo | Valor |
|---|---|
| Sprint | Épica 0 — Migración OpenAI → Google Gemini |
| Objetivo | Migrar todo el stack de LLM + embeddings de OpenAI a Google, re-indexar ChromaDB |
| Inicio | 2026-02 |
| Estado | 🟡 En progreso (ticket 0.7: config en curso) |
| Historias completadas | 1/7 (0.1: SDK instalado) |

---

## 📊 Backlog activo

| Épica | Estado | Próxima historia |
|---|---|---|
| Épica 0: Migración Gemini | 🟡 En curso | 0.7 → 0.3 → 0.4 → 0.5 → 0.6 → 0.9 |
| Épica 1: Ingesta | ⬜ Pendiente | — |
| Épicas 2-7 | ⬜ Pendiente | — |

---

## 🚧 Bloqueos

*Ninguno activo.*

---

## 🔮 Próximos pasos

1. Completar ticket 0.7 (config GOOGLE_API_KEY)
2. Migrar EmbeddingService (0.3)
3. Migrar DocumentProcessor (0.4)
4. Migrar WatcherService e InsightAgent (0.5 + 0.6)
5. Re-indexar ChromaDB (0.9)