# V.2 Matching y denominador vs Ley 11.088

**Épica:** V — Verificación / ground truth (capa B: ledger vs Ley)  
**Puntos:** 5 (tomar por slices)  
**Estado:** hecho  
**Rama sugerida:** `feature/V.2-matching-denominador` desde `main` (o desde V.1 mergeada)  
**Depende de:** V.1 hecho + abril 2026 procesado  
**Handoff:** [next-session.md](../current/next-session.md)  
**Evidencia del corte:** [corte-abril-ui.md](../current/corte-abril-ui.md)

---

## Objetivo

Que el `%` de `/presupuesto/ejecucion` use el **denominador correcto** (organismo / programa de la Ley 11.088) y no dispare sobre-compromiso por matching basura.

Hoy la pantalla mide bien **qué** (compromiso BO vs ejecución BO). V.2 corrigió **contra quién**: 0 alertas >100% en el corte abril post-repair + ETL.

## Por qué es producto

El valor ciudadano es: *EPEC lleva llamado el 9% de su techo de la Ley*. Si Secretaría de Desarrollo muestra 2703% porque el vigente es un programa de $1.9B, la alerta deja de ser creíble y se silencia el 295% de S-511 que sí hay que ver hasta corregirlo.

P.7.4 agrupó por organismo cuando hay match. Abril demostró que el match apunta a un **programa chico** o a un **organismo equivocado**.

## Criterio de aceptación (epígrafe)

- [x] Los 4 sobre-compromiso del corte 2026-09-15 tienen bitácora reproducible (query + `presupuesto_base_id` + vigente vs CGE/Ley).
- [x] Pliego S-511 / `UNIDAD EJECUTORA` / Las Peñas **no** matchea `DIRECCIÓN DE MINISTERIO` (pb_id 54). Tras re-upsert, la alerta 295% desaparece o queda unmatched explícito.
- [x] Poder Judicial usa el vigente de la **jurisdicción/organismo** (~programas PJ en `presupuesto_base`), no un programa de ~$11B. El % deja de ser 163% por denominador.
- [x] Nombres truncos (`MINISTERIO DE`, `SECRETARÍA DE DESARROLLO`) no cuelgan $50B de un programa de $1.9B. O se corrige el parser de Mapas, o el match exige nombre de organismo completo.
- [x] Tests en `presupuesto_matching` / `ejecucion_contrast` cubren S-511, PJ y un trunco. No se silencia la alerta >100% en UI.
- [x] `knowledgebase/current/` actualizado (corte UI + ancla). No se commitea `sqlite.db`.

## Slices (orden)

| Slice | Pts | Entrega | Estado |
|---|---|---|---|
| **V.2.1** Bitácora de las 4 alertas | 1 | Script/query: organismo UI → filas ledger → `pb_id` → vigente | ✅ |
| **V.2.2** S-511 / Unidad Ejecutora | 1 | Blocklist o regla: no pegar a Inteligencia Fiscal | ✅ |
| **V.2.3** Denominador por organismo | 2 | `%` vs suma `monto_vigente` del organismo canónico (o programa correcto) | ✅ |
| **V.2.4** Truncados en `presupuesto_base` | 1 | `MINISTERIO DE` / secretarías partidas: parser o filtro de match | ✅ |

No ingest de mayo–dic en esta historia. No mezclar CGE en la barra. No re-entrenar el LLM.

## Fuera de alcance

- Cerrar 2026 de boletines.
- Tercera barra “pagado CGE”.
- Scraper SIGAF acto a acto.
- Silenciar alertas >100% reales.
- Gold set / recall 44.4% (sigue siendo deuda de extracción, no de matching).

## DoR de la próxima sesión

- [x] Historia en `knowledgebase/backlog/` con criterio de aceptación
- [x] Estimación (5 pts, 4 slices)
- [x] Dependencia V.1 + abril cerrado
- [ ] Working tree: mergear V.1 **sin** `sqlite.db` antes o en paralelo
- [x] Criterio testeable
- [x] Arrancar por **V.2.1** (reproducir las 4 alertas, no adivinar el fix)

## Notas para agentes

- Matching único: `app/services/presupuesto_matching.py`. No duplicar en el ETL.
- Contraste: `app/services/ejecucion_contrast.py`. El % se calcula ahí; la UI no inventa denominador.
- Clasificador de gasto no se toca salvo que S-511 esté mal clasificado (no lo está: es gasto público; el bug es el `pb_id`).
- Código en inglés, docs en español. Línea ≤ 100.
- No commitear `sqlite.db`, PDFs, xlsx CGE.

## Cómo operar el denominador

```powershell
cd C:\Users\germa\watcher\watcher-backend
uv run python scripts/parse_pdf_presupuesto_2026.py --repair-db
uv run python scripts/etl_analisis_to_ejecucion.py
uv run python scripts/bitacora_alertas_v2.py
uv run python scripts/ancla_ley_11088.py
# UI: http://localhost:5173/presupuesto/ejecucion
```

No commitear `sqlite.db`. El matching nuevo aplica igual sin `--repair-db`; el techo de Economía/PJ queda completo después del repair.
