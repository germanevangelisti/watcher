# MVP — Watcher Agent

**Fecha:** 2026-09-24  
**Definición de salida:** Un ciudadano (o el PO) puede, en ≤ 10 pasos documentados, ver el **gasto publicado vs Ley 11.088** de la Provincia de Córdoba con **período y techo declarados**, alertas >100% **visibles y no silenciadas**, corpus de boletines **feb–sep 2026** (u otro corte declarado) con gate de drift en verde, y el **techo Ley por finalidad 1/2/3 (+ sin_clasificar) visible con disclaimer** (`inicial=vigente` en este corte; no es crédito modificado ni caja CGE) — sin reescribir la historia pre-v1.1.

> **Nota de alcance:** el README aún marca “MVP v1.1” (pipeline + UI v2). Este `mvp.md` define la **salida de MVP ahora** (post v1.1 + vertical Presupuesto P.* + honestidad V.1–V.6 + **Ampliación B** mínima): el producto deja de ser “pipeline que corre” y pasa a ser “contraste fiscal verificable”, con lectura ciudadana de asimetría de techo por finalidad.
>
> **Decisión PO (2026-09-24):** Opción **B** — expansión mínima del mismo MVP (M1–M7 + **MB**), no redefinición ni solo post-MVP. Evidencia de readiness: [mvp-b-minimal-slice.md](mvp-b-minimal-slice.md). Discusión previa: [mvp-scope-discussion.md](mvp-scope-discussion.md).

## Problema

Los boletines oficiales de Córdoba son extensos (100–300 páginas/día). Leerlos a mano no escala; además un cociente gasto/presupuesto **sin declarar período ni techo** miente al ciudadano aunque los números “cuadren” en pantalla. Tampoco alcanza ver solo el techo agregado: sin desglose por **finalidad** (Administración Gubernamental / Seguridad / Servicios Sociales) el ciudadano no puede leer la asimetría del presupuesto sancionado.

## Usuario

- **Germán Evangelisti** (PO + arquitectura): control ciudadano y transparencia.  
- **Ciudadanía / periodismo** (futuro cercano): acceso a gasto e irregularidades accionables sin planillar el BO.

## Must have

| ID | Capacidad | Criterio de aceptación | Estado | Evidencia |
|----|-----------|------------------------|--------|-----------|
| M1 | Pipeline ingesta → extracción | Mes vencido ingerible (`ingest_month` / sync) y procesable a `completed`; fallos justificados o cero fallos sin justificar en el corte declarado. | hecho (feb–sep) | V.5: 472 completed / 33 justified / 0 en vuelo; `ok=469 fail=0` |
| M2 | Ledger de gasto canónico | ETL reconstruye ledger; dedup de licitaciones republicadas; total canónico reproducible; **no** versionar `sqlite.db` en git. | hecho | V.6; `etl_analisis_to_ejecucion.py`; 972 canónicas / $1.776,41B (corte V.5) |
| M3 | Contraste honesto vs Ley 11.088 | UI/API declaran **período medido** (N de 12) y **techo verificable**; programas sin dueño separados, no escondidos; barras Publicado / Comprometido / Ejecución distintas. | hecho | V.3 / V.4; ancla Ley 11.088 |
| **MB** | **Asimetría de techo por finalidad (Ampliación B)** | API + UI + copy: techo Ley / Mapas agrupado por finalidad **1 / 2 / 3** (+ bucket **sin_clasificar**); disclaimer visible: `inicial=vigente` en este corte; **no** es crédito modificado ni caja CGE; **no** rotular numerador BO como Devengado. | **pendiente** | Spike RO 2026-09-24: proxy `partida_presupuestaria` 1er dígito medible; **no** hay endpoint `/finalidades/` ni UI aún ([mvp-b-minimal-slice.md](mvp-b-minimal-slice.md)) |
| M4 | Alertas y gate de drift | Alertas >100% listadas con causa; `check_match_drift.py` exit 0 en el corte de salida; **prohibido** silenciar alertas sin medición. | hecho | V.5: 3 alertas estructurales visibles; drift 0 filas |
| M5 | Dashboard operable (UI v2) | Frontend shadcn/TanStack sirve el contraste y el listado de actos/alertas contra API local; build de frontend en verde. | hecho / en curso | UI v2; CI build frontend verde (2026-09-23); auth/UI huérfana siguen abiertos (Épica 7) |
| M6 | Demo ≤ 10 pasos | Checklist explícito de salida MVP (arranque + M3–M4–M7 + paso MB cuando exista UI) documentado y ejecutable por un humano. | pendiente | [mvp-m6-checklist.md](mvp-m6-checklist.md); README Quick Start existe; falta ejecución humana + evidencia |
| M7 | Huecos declarados | Todo mes vencido **fuera** del corte (p.ej. 2026-01) y gasto sin denominador aparecen como hueco medido, no como cero silencioso. | hecho (declarado) | status.md / next-session: 2026-01 + $404,52B sin denominador |

### Ampliación B — detalle del Must **MB** (estrecho)

**Slice aprobado (PO, 2026-09-24):**

> “Asimetría de techo Ley por finalidad (1 / 2 / 3)” — lectura ciudadana: cuánto del presupuesto sancionado (Mapas/Ley 11.088) cae en Administración Gubernamental vs Servicios de Seguridad vs Servicios Sociales (+ `sin_clasificar`).

**Incluye (Must):**

1. API read-only que agrupe `presupuesto_base` por primer dígito de `partida_presupuestaria`, labels fijos + bucket `sin_clasificar`.
2. UI: card/tabla de participación del **techo** (no % de ejecución como promesa de salida).
3. Copy/disclaimer obligatorio: techo Ley/Mapas; `inicial=vigente` en este corte; no crédito modificado; no caja CGE.

**No incluye (rechazado como Must ahora):** sancionado ≠ vigente (diff=0 por construcción, 480/480); rotular pagos BO como Devengado; barra CGE en el mismo cociente; V.7/V.8; Índice de Alteración completo; scraper SIGAF.

**Honestidad del spike (binding):** hoy `monto_inicial == monto_vigente` en todas las filas 2026; “Ejecución” del producto = pagos/transferencias del BO, **no** DEVENGADO SIGAF.

## Should have

- **Proxy** “publicado BO matched a programas de esa finalidad / techo finalidad”, con **banner de cobertura** (unmatched + partida vacía). **No** rotularlo Devengado.  
- Más adelante: **vigente real post-modificaciones** (serie distinta del sancionado) y contraste CGE como historia propia (no mezclar en el cociente BO).  
- Cerrar **2026-01** (único mes vencido sin ingesta del año).  
- **V.7** (fuga de monto entre columnas) y **V.8** (monto del aviso vecino / model) tras **decisión explícita de costo** de re-extracción.  
- Subir recall del gold set (> 44,4 %) sin romper honestidad del contraste.  
- Re-indexado Chroma operativo (Google o local) sobre corpus real.  
- DT-2/DT-3 (15 tests rojos preexistentes) y residual lint si aún aplica.  
- Graph Explorer / Pipeline Health UI (Fase 5 de `task.md`).  
- Mapa geográfico / menciones en UI v2.

## Won't

- Silenciar o redondear alertas >100% “para que el MVP se vea limpio”.  
- Mezclar barra “pagado CGE” con el Boletín Oficial en el mismo cociente (tercera barra = historia propia).  
- Inventar variación **sancionado ≠ vigente** mientras el corte tenga diff=0 por construcción.  
- Rotular numerador BO (pagos/compromisos publicados) como **Devengado**.  
- Narrativa moral / juicio político como requisito de producto (el producto declara números y huecos; no predica).  
- Inventar desvíos o % de ejecución por finalidad “listos” sin matching + coverage honestos.  
- App mobile / multi-tenant SaaS / roles de usuario como requisito de salida.  
- Tratar Hermes/Cooperledge o Notion como fuente de verdad del producto Watcher.  
- Reescribir el alcance histórico de “MVP v1.1” en el README como si este documento no existiera (el badge puede quedar; el canónico es este `mvp.md`).  
- Exigir 12/12 meses + recall perfecto + cero unmatched para llamar salida.  
- Empujar V.7/V.8 o Índice de Alteración completo “para que B cierre”.

## Métricas

| Métrica | Umbral de salida MVP |
|---------|----------------------|
| Meses medidos del año declarado | ≥ 8/12 **o** el corte que `status.md` declare, con huecos listados |
| Gate drift | exit 0 en el corte de salida |
| Alertas >100% | Todas visibles; cada una con causa (extracción vs denominador) |
| Techo por finalidad (MB) | 1 / 2 / 3 + sin_clasificar visibles en API+UI con disclaimer |
| Demo | Checklist ≤ 10 pasos ejecutado una vez por un humano ([mvp-m6-checklist.md](mvp-m6-checklist.md)) |
| Tests | No introducir fallos nuevos fuera de DT-2/DT-3 conocidos |

## Riesgos

- Re-extraer para V.7/V.8 **borra reparaciones manuales** ya declaradas (caso V.8).  
- 123 boletines `completed` sin PDF en disco → auditoría geométrica incompleta.  
- Recall 44,4 %: se mide ~mitad de actos del gold set.  
- `$` sin denominador crece al sumar meses (esperado; no es regresión silenciosa).  
- README / planes raíz desalineados del KB (deuda de consolidación del estándar).  
- **MB:** ~37 filas EMPTY + “Recursos”/“Cuentas” + fin=6 ensucian el proxy; sin bucket `sin_clasificar` se miente el techo.  
- Prometer % ejecución por finalidad sin banner de cobertura (unmatched $404B + partida vacía) engaña al ciudadano.

## Dependencias

- PDFs del BO Córdoba + Ley 11.088 parseada.  
- Gemini y/o LocalPro/Ollama según tier.  
- Decisión humana de costo para V.7/V.8.  
- **Implementación MB** (API + UI + copy) antes de marcar salida con Ampliación B.  
- Aprobación PO para **trackear** este `mvp.md` (hoy untracked; no commit hasta OK final).  
- Cooperledge portfolio para reflejar “MVP alcanzado” cuando M1–M7+**MB** tengan evidencia y M6 esté ejecutado.

## Demo (M6)

Checklist canónico: [mvp-m6-checklist.md](mvp-m6-checklist.md).  
Pasos 1–9 son ejecutables hoy (M3–M4–M7). El paso de **finalidad / MB** queda marcado como *cuando exista UI MB* hasta que API+UI estén hechos.