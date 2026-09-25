# Investigación: Jev (TypeSafe) como capa de decisión en extracción — Watcher

**Fecha:** 2026-09-25  
**Autor sesión:** PM (coordinación portfolio) + Germán  
**Estado:** nota de investigación **archivada**  
**Prioridad:** **ninguna** — no entra a cola semanal, no hay spike, no se implementa ahora  
**Dueño de producto:** bot watcher  

---

## Pregunta

¿Es viable usar [Jev](https://www.jevtypesafeai.com/) (TypeSafe System One) para mejorar la toma de decisiones al momento de extraer contenido de boletines?

## Respuesta corta

**Parcialmente sí, y solo como juez tipado — no como extractor.**  
Jev no genera texto: no puede inventar montos, expedientes ni tipologías. Encaja *después* de que regex / layout / LLM proponen candidatos. Germán decidió **no** priorizar implementación ni spike (2026-09-25).

---

## Qué es Jev

- Modelo System One: `state` + preguntas tipadas → respuestas tipadas.
- Tres formas: `choice` (opción cerrada), `score` (rúbrica 2–10), `noul` (probabilidad sí/no).
- Latencia típica ~70–500 ms; salida gratis; entrada ~US$0.042 / MTok (oficial TypeSafe; hay capa metered intermedia).
- No alucina *forma* (siempre cumple el tipo); **sí puede equivocarse en el significado**. La confianza no es garantía.
- Acceso: waitlist TypeSafe o API hosted metered.

Fuentes revisadas (2026-09-25): docs Jev / TypeSafe, paquetes `jev` / `jevclient` en PyPI, análisis Zyte sobre scraping, Beam sobre verificación post-extracción.

---

## Cómo decide Watcher hoy

1. **PDF → texto** (`ExtractorRegistry`: PyPDF2 / pdfplumber).
2. **Inteligencia:** Free (keywords/regex), Pro (Gemini structured), LocalPro (Ollama).
3. **Post-reglas:** `gasto_classifier` (¿es gasto? etapa, jurisdicción) — sin LLM.

Dolor medido (no es JSON mal formado):

| Hallazgo | Qué pasa |
|---|---|
| **V.7** | Página a 2 columnas aplanada → el modelo toma el monto / expediente del acto *de al lado* |
| **V.8** | Monto del aviso vecino, tasa de publicación BO, o coma decimal ×100 → llega al ledger |
| **Gold set** | Recall ~44 % (18 actos; 8 matcheados) |

Raíz de V.7/V.8: geometría del PDF / texto aplanado + decisión del modelo sobre adyacencias falsas. Eso **no** se arregla solo con un modelo de decisión.

---

## Dónde Jev encajaría (si algún día se retoma)

Patrón recomendado por TypeSafe/Zyte: **código propone, Jev elige**.

1. Regex / layout extrae 2–5 montos candidatos en la página → `choice` elige el del acto.
2. Tras LocalPro/Gemini: `noul` «¿este monto pertenece a este acto?» → gate antes del ledger.
3. `score` de calidad de extracción → auto-aceptar / escalar a humano.
4. Clasificaciones ambiguas donde Free se queda corto — **sin** reemplazar `gasto_classifier` donde las reglas ya bastan.

## Dónde no encaja

- Sustituir el extractor PDF o el LLM generativo.
- Arreglar V.7 de raíz (hace falta extracción con layout/columnas).
- Reemplazar null checks y reglas baratas.
- Confiar ciegamente en `confidence` sin medir en corpus Watcher (español jurídico BO).

Riesgos: dependencia hosted + clave; calibración desconocida en BO Córdoba; contenido adversario / páginas que «argumentan» su clasificación; no es frontera de seguridad.

---

## Decisión de portfolio (2026-09-25)

- Queda **solo** esta nota.
- **No** spike.
- **No** historia en kanban ni Must.
- La prioridad de mejora de extracción sigue en el camino ya abierto (V.7/V.8, layout, gold set) cuando Germán lo encole.

## Si se retoma (checklist futuro, no comprometido)

1. Spike acotado a casos V.7/V.8 ya medidos + gold set.
2. Éxito: atrapar cruces de monto sin subir falsos positivos en matcheados con error 0 %.
3. Comparar costo/latencia vs segundo pase LocalPro.
4. Solo entonces plantear historia `work: impl` con gate testing manual.

---

## Referencias internas

- `knowledgebase/backlog/V.7-monto-del-acto-de-al-lado.md`
- `knowledgebase/backlog/V.8-monto-del-aviso-vecino.md`
- `knowledgebase/current/goldset.md`
- `knowledgebase/architecture/overview.md` (tiers Free / Pro / LocalPro)
- `watcher-backend/app/services/intelligence_provider.py`
- `watcher-backend/app/services/gasto_classifier.py`
