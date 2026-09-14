# V.1 Verificar pipeline vs realidad

**Épica:** V — Verificación / ground truth  
**Puntos:** 8 (tomar por slices; no implementar el epígrafe entero en un solo PR)  
**Estado:** refinado · **por hacer**  
**Rama sugerida:** `feature/V.1-verificar-pipeline-vs-realidad` desde `main`  
**Depende de:** P.7 mergeada (ledger vivo + Ley 11.088 + UI de contraste)  
**Handoff:** [next-session.md](../current/next-session.md)  
**Evidencia de corpus actual:** [gasto-publico-actos.md](../current/gasto-publico-actos.md)

---

## Objetivo

Consumir las fuentes oficiales mínimas para decidir, con evidencia, si Watcher:

1. **No pierde el boletín** — lo publicado en el Boletín Oficial está en la DB.
2. **No inventa ni deforma el acto** — lo extraído coincide con el PDF.
3. **Ancla el % contra la Ley** — `presupuesto_base` es el denominador correcto.
4. **No confunde aviso con caja** — el ledger de boletines no se vende como ejecución SIGAF/CGE.

Hoy el corpus local es un recorte (feb–mar 2026 + 1 día de septiembre, ~150 boletines, 11 failed / 1 pending). Cualquier % vs Ley 11.088 está sesgado por **cobertura**, no solo por calidad del extractor.

## Por qué es producto

P.7 ya clasifica gasto, alimenta el ledger al cerrar el pipeline y muestra compromiso vs ejecución contra `monto_vigente`. Eso es coherencia **interna**. El valor ciudadano es poder decir: *esta pantalla refleja lo que salió publicado, y no pretende ser la tesorería*.

Sin calendario vs DB, gold set y un trimestral oficial, no hay forma de defender los $188 mil M de compromiso ni los $228 M de ejecución.

## Dos chequeos (no mezclar)

| Capa | Pregunta | Fuente de verdad | Qué no es |
|---|---|---|---|
| **A. Pipeline vs boletín** | ¿Ingestamos y extraemos lo publicado? | [boletinoficial.cba.gov.ar](https://boletinoficial.cba.gov.ar) + PDF | Salud de Neo4j/Chroma |
| **B. Ledger vs Ley** | ¿El % usa el denominador correcto? | Ley 11.088 + Mapas-por-Programas + arts. 11/15 | Ejecución de caja |
| **C. Boletín vs Estado** | ¿El orden de magnitud cierra con Hacienda? | Informe de ejecución trimestral (CGE) | Acto a acto vs SIGAF |

El boletín es **proxy de compromisos publicados**. La ejecución real vive en informes CGE / SIFEP. El toggle de P.7.4 (compromiso vs ejecución) no debe ganar un tercer número mezclado en la misma barra.

## Criterio de aceptación (epígrafe)

- [ ] Script o informe reproducible: días hábiles publicados (fecha × sección S1–S5) vs filas en `boletines` (status). Lista de huecos y `failed`/`pending`.
- [ ] Gold set versionado: ≥ 12 PDFs etiquetados a mano (acto, monto, organismo, `numero_acto`, etapa). Métricas: recall/precisión de actos, error de monto, % S4 con número.
- [ ] Un mes calendario cerrado (marzo 2026) cubierto: failed re-bajados o justificados; ledger estable al reprocesar.
- [ ] Totales EPEC/ACIF y sample de 15 programas de `presupuesto_base` contrastados contra PDF/ley. Bitácora de unmatched provinciales y del falso positivo S-511 → `DIRECCIÓN DE MINISTERIO`.
- [ ] Un informe trimestral oficial 2026 (tipo `ejecucion_trimestral`) contrastado a mano contra 8 organismos del ledger. El resultado se documenta como **orden de magnitud**, no como join acto a acto.
- [ ] `knowledgebase/current/` actualizado con el corte (cobertura, gold set, CGE). No se commitea `sqlite.db`.

## Slices (orden de implementación)

| Slice | Pts | Entrega | Estado |
|---|---|---|---|
| **V.1.1** Inventario calendario vs DB | 2 | Diff días/secciones publicados vs `boletines`; lista de huecos y failed | ⬜ por hacer |
| **V.1.2** Gold set de extracción | 2 | 12 PDFs etiquetados + planilla precisión/recall/monto/`numero_acto` | ⬜ por hacer |
| **V.1.3** Cerrar un mes | 2 | Marzo 2026 completo (re-bajar failed, reprocesar, ledger idempotente) | ⬜ por hacer |
| **V.1.4** Ancla Ley 11.088 | 1 | Totales + 15 programas + bitácora unmatched / 295% | ⬜ por hacer |
| **V.1.5** Trimestral CGE | 1 | Subir T1 2026 (o el publicado) como `ejecucion_trimestral`; tabla 8 organismos | ⬜ por hacer |

No completar abr–dic 2026 antes de V.1.1 + V.1.2: se multiplica basura.

## Fuentes a consumir

| Fuente | Tipo ya modelado | Uso |
|---|---|---|
| Boletín Oficial de Córdoba (diario, S1–S5) | `boletin_diario` | Completitud de ingesta + gold set |
| PDFs locales en `boletines/` (gitignored) | — | Extracción vs sumario |
| Ley 11.088 + `watcher-doc/data/2026/Mapas-por-Programas.pdf` | `presupuesto_anual` | Denominador (ya parseado en P.7.3) |
| Informe de ejecución trimestral CGE / Hacienda | `ejecucion_trimestral` | Orden de magnitud por organismo |
| Portal de compras / pliegos (opcional, V.1.5+) | — | 20 n.º de licitación EPEC/Policía/ACIF existen fuera del PDF |

El panel de Fuentes de dato ya tiene los tres tipos. V.1.5 es el primer consumo real de `ejecucion_trimestral`; no hace falta un scraper SIGAF.

## Métricas mínimas (V.1.1–V.1.2)

| Métrica | Dónde |
|---|---|
| % días hábiles cubiertos (rango elegido) | inventario |
| % secciones presentes por día publicado | inventario |
| count `completed` / `failed` / `pending` | inventario |
| Δ actos vs sumario del PDF | gold set |
| % S4 con `numero_acto` no nulo | gold set |
| Error de monto (actos del gold set) | gold set |
| Drift al reprocesar el mismo `boletin_id` | V.1.3 (paridad P.7.2) |

KPI prohibido: suma cruda de `analisis.monto_numerico` (S-511 × 8 avisos). Usar ledger canónico + `is_gasto_publico`.

## Fuera de alcance

- Completar el año 2026 de boletines antes del gold set.
- Scraper SIGAF / tesorería a nivel acto.
- Mezclar “pagado según CGE” en la misma barra que compromiso/ejecución del boletín.
- Re-entrenar el LLM; el clasificador de gasto sigue siendo reglas.
- Neo4j, reindex Chroma, UI huérfana, CI, JWT.
- Municipales S5 como claim de producto (salvo que V.1.1 revele un agujero de sync provincial).
- Silenciar el 295% de `DIRECCIÓN DE MINISTERIO` sin confirmar matching vs acto real (V.1.4).

## DoR de la próxima sesión

- [x] Historia en `knowledgebase/backlog/` con criterio de aceptación
- [x] Estimación (8 pts, 5 slices)
- [x] Dependencia P.7 resuelta al mergear esta sesión
- [ ] Working tree limpio al **arrancar** V.1 (este merge lo deja así)
- [ ] Rama `main` actualizada
- [x] Criterio testeable

Arrancar por **V.1.1**: script de cobertura calendario vs DB. Es la mayor señal por hora.

## Notas para agentes

- Código en inglés, docs en español. Línea ≤ 100 (ruff).
- No commitear `sqlite.db`, `*.db-wal`, `uv.lock`, PDFs de `boletines/` ni Mapas-por-Programas.
- Matching y dedup siguen en `app/services/presupuesto_matching.py`. V.1 no reimplementa el ledger.
- Clasificador: patrones **sin tildes** (`_strip_accents`).
- No mezclar compromiso + ejecución en un solo %.
- Gold set: versionar la planilla en `knowledgebase/` o `watcher-doc/` (CSV/Markdown), no el PDF entero si ya está en disco local.
- Descarga provincial hoy vive en `sync_service`, no en `ProvincialPipeline.extract()` (ticket 1.1 parcial). El inventario debe contar lo que `sync` realmente bajó.
- Notion: MCP no estuvo disponible en P.7; actualizar tablero si el MCP vuelve.

## Cómo seguir

```powershell
cd C:\Users\germa\watcher
git checkout main
git pull   # si hay remoto
git checkout -b feature/V.1-verificar-pipeline-vs-realidad
# arrancar V.1.1 — inventario calendario vs DB
```

Corpus local (no borrar, no commitear): `watcher-backend/sqlite.db` con ~150 boletines, 5.667 `analisis`, 480 `presupuesto_base`, ledger P.7.
