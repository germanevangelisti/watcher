# Knowledge Base — Watcher Agent

🗂️ Documentación del producto siguiendo metodologías ágiles (Scrumban adaptado a equipo unipersonal).

---

## 📂 Estructura

| Directorio | Propósito |
|---|---|
| [`vision/`](vision/) | Visión del producto, stakeholders, roadmap |
| [`architecture/`](architecture/) | Decisiones de diseño (ADRs), diagramas de flujo |
| [`backlog/`](backlog/) | Épicas desglosadas en historias de usuario |
| [`sprints/`](sprints/) | Planificación + retrospectiva por sprint |
| [`standups/`](standups/) | Daily standups (un archivo por día) |
| [`current/`](current/) | Snapshot vivo del estado del proyecto |
| [`workflows/`](workflows/) | Procesos: DoD, DoR, convenciones, guías |

---

## 🗺️ Navegación rápida

- [Visión del producto](vision/product-vision.md)
- [Estado actual](current/status.md)
- [Backlog](backlog/)
- [Arquitectura](architecture/overview.md)
- [DoD](workflows/definition-of-done.md)
- [DoR](workflows/definition-of-ready.md)

---

## 🧠 Convenciones

- **Idioma:** Código en inglés, documentación en español
- **Formato:** Markdown puro (versionable en git)
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- **Estimaciones:** Puntos de historia (1 punto ≈ medio día de trabajo enfocado)
- **Ritmo:** Sin ceremonies fijas; los commits marcan el pulso. Retrospectiva al cierre de cada sprint.
- **Nomenclatura de ADR:** `ADR-NNN-titulo-breve.md` — numeración secuencial global del proyecto.

---

> *"La KB está viva — si algo no se usa en 2 sprints, se archiva o se borra."*