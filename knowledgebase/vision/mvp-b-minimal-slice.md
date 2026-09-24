# Spike read-only — Opción B (slice mínimo) · asimetría fiscal

**Fecha:** 2026-09-24 (America/Cordoba)  
**Máquina:** cooperledge · `C:\Users\germa\watcher`  
**Tipo:** evidencia de readiness (no implementación)  
**Canónico de salida:** [mvp.md](mvp.md) — reescrito 2026-09-24 post-decisión B (este spike sigue siendo evidencia RO; no es el canónico)  
**Borrador hermano:** [mvp-scope-discussion.md](mvp-scope-discussion.md)

> Pregunta: ¿el ledger / ETL / APIs de hoy ya exponen lo necesario para un Must **mínimo** de asimetría fiscal (finalidad + sancionado/vigente + devengado + tasas)?  
> Respuesta corta: **no completo**. Hay proxy usable para un slice B estrecho; faltan extracción/API para sancionado≠vigente y para devengado real por finalidad.

---

## 1. Disponible hoy (con evidencia)

| Concepto Germán | Qué hay | Evidencia |
|---|---|---|
| Techo Ley / denominador | `presupuesto_base.monto_vigente` (ejercicio 2026, 480 programas, Σ $7.531.907.153.000) | `app/db/models.py` `PresupuestoBase`; DB local; `knowledgebase/current/ancla-ley-11088.md` |
| “Inicial” en schema | `monto_inicial` expuesto en API `/programas/` y `/organismos/` | `schemas/presupuesto.py`; endpoint organismos suma ambos |
| Numerador BO (proxy) | Ledger `ejecucion_presupuestaria` con `etapa_gasto` → buckets compromiso/ejecución | `ejecucion_contrast.py`; ETL `etl_analisis_to_ejecucion.py` |
| Barras UI | **Publicado / Comprometido / Ejecución** vs `monto_vigente` por organismo | `organismo-contrast.tsx` (tones `publicado`/`comprometido`/`ejecucion`); V.3 |
| Período + techo honestos | `cobertura_temporal`, `denominador` sin dueño, alertas >100% | API `GET /ejecucion/resumen/`; V.4 |
| Código fin/fun/det en DB | Columna PDF `fin_fun_det` → se guarda en `partida_presupuestaria` (`1.6.0`, `2.1.0`, …) | `parse_pdf_presupuesto_2026.py` `_COL_BOUNDS` + `_normalize_fin_fun_det` |
| Proxy finalidad (1er dígito) medido en DB | 1≈$568B · 2≈$268B · 3≈$2.388T · 4≈$3.066T · 5≈$86B (+ ruido EMPTY/Recursos/Cuentas) | Query RO `sqlite.db` 2026-09-24 |
| Devengado CGE (ad-hoc) | Parser Excel CGE T1: vigente/compromiso/devengado/pagado para 8 organismos | `cge_trimestral.py`; `cge-trimestral.md` — **no** endpoint de producto |

**Cortes ledger (RO, canónicos `is_duplicate=0`):** llamado 770 / pago 162 / contrato 25 / adjudicación 15. Sin `presupuesto_base_id`: 364 actos / ~$404,5B (hueco ya declarado M7).

## 2. Parcial / proxy

1. **Finalidad / clasificador:** el dígito de `partida_presupuestaria` alinea con el clasificador oficial (1 Administración Gubernamental, 2 Servicios de Seguridad, 3 Servicios Sociales, …) en muestras (Seguridad→2, Salud/Educación/Desarrollo Social→3, Gobernación/Legislativo→1). **No** hay labels ni endpoint `/finalidades/`. ~37 filas EMPTY + “Recursos”/“Cuentas” + fin=6 ensucian. Ledger join por fin deja mucha masa en partida vacía o unmatched.
2. **“Vigente” del MVP ≠ crédito modificado:** `monto_inicial == monto_vigente` en **480/480** filas 2026 (`n_diff=0`). Ambos se seedearon con el **mismo monto** de Mapas/Ley (`parse_pdf_presupuesto_2026.py` asigna `monto_inicial=monto` y `monto_vigente=monto`). Variación vigente−sancionado = **0 por construcción**.
3. **Devengado:** el producto muestra **Ejecución = pagos/transferencias del BO**, no DEVENGADO SIGAF. Docs (P.7, V.1, `cge-trimestral.md`) lo dicen explícito: boletín = proxy de compromisos publicados. CGE devengado existe solo como contraste de orden de magnitud, no como barra del dashboard.
4. **Tasas:** sí hay `pct_compromiso` / `pct_ejecucion` = numerador BO / `monto_vigente` **por organismo**. No por finalidad. “Variación crédito” no computable.

## 3. Ausente (haría falta para Must B “completo”)

- Campo/API **finalidad** con etiqueta oficial y agregación estable (limpiar EMPTY/parse noise).
- Serie **crédito modificado / vigente post-modificaciones** distinta del sancionado (Excel CGE o SIFEP; hoy no cargada en `presupuesto_base`).
- **Devengado** persistido y contrastable por finalidad (no solo script T1 de 8 organismos).
- Matching ledger→finalidad de calidad (hoy muchos matched tienen partida vacía; unmatched $404B).
- UI/API slice de asimetría (no existe pantalla “1 vs 2 vs 3”).
- `metricas_gestion` / `vinculos_acto_presupuesto`: **0 filas** en DB local.

## 4. Must mínimo recomendado (opción B, sin V.7/V.8 / full index)

**Un solo slice concreto:**

> **“Asimetría de techo Ley por finalidad (1 / 2 / 3)”** — lectura ciudadana: cuánto del presupuesto sancionado (Mapas/Ley 11.088) cae en Administración Gubernamental vs Servicios de Seguridad vs Servicios Sociales.

**Alcance del slice:**

1. API read-only `GET /presupuesto/finalidades/?ejercicio=2026` que agrupe `presupuesto_base` por primer dígito de `partida_presupuestaria`, con labels fijos + bucket `sin_clasificar` (EMPTY/Recursos/Cuentas/otros).
2. UI: una card/tabla de 3+1 barras de **participación del techo** (no % de ejecución). Copy explícito: “techo Ley / Mapas; `inicial=vigente` en este corte; no es crédito modificado ni caja CGE”.
3. Opcional delgado (Should, no Must B): debajo, **proxy** “publicado BO matched a programas de esa finalidad / techo finalidad”, con banner de cobertura (unmatched + partida vacía). **No** rotularlo Devengado.

**Fuera del Must B mínimo:** V.7/V.8, re-index Chroma, 2026-01, scraper SIGAF, tercera barra pagado CGE, variación sancionado≠vigente.

## 5. Impacto M6 (checklist ≤10 pasos bajo B)

Mantener pasos 1–10 de `mvp-scope-discussion.md` (arranque, contraste M3/M4, alertas, drift, huecos). **Sustituir o fusionar** un paso de verificación genérica por:

- Abrir vista/card **Finalidad (techo Ley)**.
- Verificar totales 1 / 2 / 3 (+ sin_clasificar) y el disclaimer `inicial=vigente` / no-CGE.
- Si el proxy BO está en el slice: confirmar que **no** se llama “devengado”.

Techo sigue ≤10 (fusionar 4+5 de período/techo si hace falta).

## 6. Riesgos si se promete sancionado / vigente / devengado por finalidad *ahora*

| Promesa | Riesgo |
|---|---|
| Sancionado ≠ vigente | Falso: diff=0; inventaría variación |
| Devengado por finalidad | Confunde pago BO o CGE T1 parcial con caja; viola Won't de mezclar CGE |
| % ejecución por finalidad “listo” | Matching + partida vacía + unmatched $404B → % engañoso |
| Labels “Servicios Sociales” sin bucket ruido | Subdeclara techo o mete basura de parseo |
| Empujar V.7/V.8 “para que B cierre” | Costo de re-extracción; pierde reparaciones (caso V.8) — fuera de B mínimo |

## Fuentes (esta spike)

- `knowledgebase/vision/mvp.md`, `mvp-scope-discussion.md`, `product-vision.md`
- `knowledgebase/backlog/P.7-*.md`, `V.3-*.md`, `V.4-*.md`
- `knowledgebase/current/ancla-ley-11088.md`, `cge-trimestral.md`, `status.md`
- `watcher-backend/app/db/models.py`, `schemas/presupuesto.py`, `api/.../presupuesto.py`, `services/ejecucion_contrast.py`, `services/cge_trimestral.py`
- `scripts/parse_pdf_presupuesto_2026.py`
- `watcher-frontend/.../organismo-contrast.tsx`, `pages/presupuesto/ejecucion.tsx`
- Queries RO a `watcher-backend/sqlite.db` (no escrituras)

**No modificado:** código tracked ni `mvp.md`. Este archivo es borrador **nuevo untracked**.
