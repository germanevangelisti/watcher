# Propuesta de discusión — alcance MVP Watcher

**Para:** Germán Evangelisti (PO)  
**Fecha:** 2026-09-24  
**Tipo:** discusión de alcance (no plan de implementación)  
**Canónico de salida:** [mvp.md](mvp.md) (M1–M7 + **MB**; archivo aún **untracked**)  
**Estado operativo:** [status.md](../current/status.md) · tip `main` = `b8b4c8e` (al día con `origin/main`)

> **Actualización PO (2026-09-24):** Germán aprobó **Opción B** (expansión mínima del mismo MVP). Must B estrecho aprobado: **techo Ley por finalidad 1/2/3 (+ sin_clasificar)** con disclaimers. **No** Must ahora: sancionado≠vigente, BO como Devengado, CGE en el mismo cociente, V.7/V.8, Índice de Alteración completo. Canónico reescrito: [mvp.md](mvp.md) (fila **MB** pendiente) + [mvp-m6-checklist.md](mvp-m6-checklist.md). Spike: [mvp-b-minimal-slice.md](mvp-b-minimal-slice.md). **Siguiente:** implementar MB (API+UI+copy) → ejecutar M6 → trackear mvp.md solo con OK final del PO. Este archivo queda como historial de la discusión A/B; las decisiones abiertas D1–D5 de abajo se consideran resueltas hacia B / M6+MB, no hacia redefinir el MVP.

> Objetivo de esta nota: alinear Must / Should / Won't, separar **hecho con evidencia** de **aspiracional**, y dejar 3–5 decisiones A/B concretas. No implementa features ni propone commits.

---

## 1. Must / Should / Won't (recomendación)

Alineado a M1–M7 de `mvp.md` y al estándar Cooperledge (Must bloquea salida; Should no; Won't explícito).

### Must (bloquean salida de MVP)

| ID | Capacidad | Recomendación | Evidencia citada en KB / git |
|----|-----------|---------------|------------------------------|
| **M1** | Pipeline ingesta → extracción (corte declarado) | **Mantener Must** · tratar como **hecho** en el corte feb–sep | V.5: 472 `completed` / 33 `justified:` / 0 en vuelo; `ok=469 fail=0` (`status.md`, `mvp.md`) |
| **M2** | Ledger canónico + dedup; no versionar `sqlite.db` | **Mantener Must** · **hecho** | V.6; ETL; 972 canónicas / $1.776,41B (corte V.5) |
| **M3** | Contraste honesto vs Ley 11.088 (período + techo) | **Mantener Must** · **hecho** | V.3 / V.4; ancla Ley; barras Publicado / Comprometido / Ejecución |
| **M4** | Alertas >100% visibles + gate drift exit 0 | **Mantener Must** · **hecho** en corte V.5 | 3 alertas estructurales visibles; drift 0 filas |
| **M5** | Dashboard operable (UI v2 + API local) | **Mantener Must** · **casi hecho**; no exigir auth/Épica 7 completa para salida | UI v2; CI build frontend + gate ruff en verde (`b8b4c8e`, 2026-09-23). Auth/UI huérfana siguen abiertos en Épica 7 |
| **M6** | Demo ≤ 10 pasos documentada | **Mantener Must** · **único Must claramente pendiente** | README tiene Quick Start genérico; **falta checklist explícito “salida MVP”** enlazado a M3–M4 (`mvp.md`) |
| **M7** | Huecos declarados (no ceros silenciosos) | **Mantener Must** · **hecho (declarado)** | 2026-01 + $404,52B sin denominador listados en status/next-session |

**Definición de salida (frase de `mvp.md`, sin reescribirla):** ciudadano/PO ve gasto publicado vs Ley 11.088 con período y techo declarados, alertas >100% visibles, corpus feb–sep (u otro corte declarado) con drift en verde — en ≤ 10 pasos documentados.

### Should (nice; no bloquean salida)

- Cerrar **2026-01** (único mes vencido sin ingesta).
- **V.7 / V.8** tras **decisión explícita de costo** de re-extracción (next-session: pierden reparaciones manuales si se re-extrae).
- Subir recall gold set (> 44,4 %) sin romper honestidad.
- Re-indexado Chroma operativo sobre corpus real.
- DT-2/DT-3 (15 tests rojos preexistentes) — no introducir fallos nuevos.
- Graph Explorer / Pipeline Health / mapa / menciones UI v2.
- Cerrar residuales Épica 7 (auth, UI huérfana) **después** de M6 si no bloquean la demo.

### Won't (no reabrir en esta salida)

- Silenciar o “limpiar” alertas >100% para que el MVP se vea limpio.
- Mezclar barra “pagado CGE” con el BO en el mismo cociente.
- App mobile / multi-tenant SaaS / roles como requisito de salida.
- Exigir 12/12 meses + recall perfecto + cero unmatched para llamar salida.
- Tratar Hermes/Cooperledge/Notion como fuente de verdad del producto Watcher.
- Reescribir el badge README “MVP v1.1” como si este alcance post-vertical Presupuesto + V.* no existiera (canónico = `mvp.md`).

---

## 2. Hecho vs aspiracional (solo evidencia)

### Hecho (con evidencia en git / KB)

| Qué | Evidencia |
|-----|-----------|
| `main` limpia vs `origin/main` | `git status`: up to date; único untracked = `knowledgebase/vision/mvp.md` |
| Tip reciente CI | `b8b4c8e` cierra DT-7 (ruff gate producto); `c9b7fc7` build frontend |
| Vertical V.1–V.6 + V.5 en `main` | log + `status.md` (V.5 2026-09-19: 8/12 meses; drift exit 0) |
| Honestidad del cociente | V.3/V.4 mergeados; período y techo declarados |
| Alertas no silenciadas | 3 alertas >100% con causa (granularidad denominador) |
| Huecos declarados | 2026-01; $404,52B / 364 actos sin denominador |
| MVP canónico escrito | `mvp.md` existe en disco (fecha 2026-09-23) pero **aún no trackeado** |

### Aspiracional / incompleto / desalineado

| Qué | Evidencia de gap |
|-----|------------------|
| **M6 checklist ≤ 10 pasos** | `mvp.md` lo marca pendiente; README Quick Start arranca stack pero **no** verifica contraste/alertas/drift como demo de salida |
| **M5 “100% cerrado”** | `mvp.md`: “hecho / en curso”; Épica 7 auth/UI huérfana abiertas |
| **status.md frescura** | Cabecera “Última actualización: 2026-09-19”; CI/DT-7 del 2026-09-23 aparece en git y en notas internas, no como corte reescrito arriba |
| **README vs producto** | Badge “MVP v1.1”; arquitectura README aún menciona OpenAI/GPT-4 en diagramas — drift vs stack Gemini/LocalPro del KB |
| **product-vision roadmap** | Actualizado 2026-09-15; no refleja corte V.5 de 8 meses como foco de salida |
| **Portfolio Cooperledge** | `overview.md` (2026-09-23): Watcher aún “MVP v1.1 en README; consolidar mvp.md canónico” — no “MVP alcanzado” |
| **V.7 / V.8, 2026-01, recall 44,4 %, 123 PDFs faltantes** | Explicitados como abiertos / Should / riesgos; **no** Must de salida según `mvp.md` |

---

## 3. Decisiones abiertas (A/B para Germán)

### D1 — ¿Cuándo se declara “MVP alcanzado”?
- **A)** Ahora: M1–M5+M7 con evidencia + **cerrar solo M6** (checklist ≤10 pasos ejecutado una vez por un humano). Luego marcar fecha en `status.md` y reflejar en portfolio.
- **B)** Más tarde: no declarar hasta ingerir **2026-01** y/o acometer V.7/V.8.

### D2 — ¿V.7 / V.8 dentro o fuera del camino crítico?
- **A)** **Fuera** (Should): documentar riesgo y reparaciones manuales; no re-extraer antes de la demo de salida.
- **B)** **Dentro** (promover a Must): aceptar costo de re-extracción y pérdida de reparaciones ya declaradas (caso V.8).

### D3 — ¿Qué alcanza para M5 en la demo?
- **A)** UI v2 local contra API + contraste M3/M4 visible (auth/Épica 7 **fuera**).
- **B)** Exigir auth / cierre Épica 7 antes de llamar salida.

### D4 — ¿2026-01?
- **A)** Queda como **hueco declarado** (M7); Should post-MVP.
- **B)** Must: no hay salida sin enero ingerido.

### D5 — ¿Qué hacer con `mvp.md` untracked y el badge README?
- **A)** Trackear `mvp.md` como canónico; dejar badge “v1.1” con nota de alcance (como dice Won't de `mvp.md`); actualizar portfolio cuando M6 tenga evidencia.
- **B)** Primero alinear README/portfolio/status a “camino a MVP / alcanzado” en un solo corte documental, y recién entonces trackear.

---

## 4. Riesgos

| Riesgo | Por qué importa ahora |
|--------|------------------------|
| **M6 ausente** | Estándar Cooperledge: sin demo ≤10 pasos no hay “MVP listo” de portfolio, aunque M1–M5+M7 tengan evidencia |
| Re-extraer por V.7/V.8 | Borra reparaciones manuales ya declaradas (V.8); decisión de costo humana |
| 123 boletines `completed` sin PDF en disco | Auditoría geométrica incompleta; texto sí está en `chunk_records` |
| Recall 44,4 % | Se mide ~mitad de actos del gold set — no es umbral de salida, pero limita confianza narrativa |
| `$` sin denominador crece al sumar meses | Esperado ($404,52B); no confundir con regresión silenciosa |
| Drift docs (README / vision / status / portfolio) | Riesgo de declarar MVP en un lado y “v1.1” en otro |
| 15 tests rojos DT-2/DT-3 | Conocidos; métrica de salida = no introducir fallos **nuevos** |

---

## 5. Demo de salida (criterios) — gap M6

**Criterio portfolio (Cooperledge):** todos los Must con evidencia + `status.md` marca MVP alcanzado (fecha) + camino de demo reproducible en README/KB (≤ 10 pasos) + portfolio actualizado.

**Gap confirmado:** existe Quick Start (clonar / `make install` / start backend+frontend / URLs). **No** existe checklist “salida MVP” que, en ≤ 10 pasos, abra el corte presupuestario y verifique M3–M4 (período/techo, alertas visibles, drift verde) enlazado a `mvp.md`.

### Checklist propuesto (borrador para discutir; **no ejecutado aquí**)

Objetivo: ≤ 10 pasos; humano lo corre una vez.

1. Arrancar backend (API local documentada).
2. Arrancar frontend (UI v2).
3. Abrir dashboard de presupuesto / contraste vs Ley 11.088.
4. Verificar que la UI declara **período medido** (N de 12; corte feb–sep u el que diga `status.md`).
5. Verificar que el **techo** es verificable y programas sin dueño no están escondidos.
6. Confirmar barras **Publicado / Comprometido / Ejecución** distintas (no mezclar CGE).
7. Abrir listado de **alertas >100%** y ver las 3 (o las del corte) con causa.
8. Correr `check_match_drift.py` → **exit 0** en el corte de salida.
9. Confirmar huecos declarados visibles o documentados (p.ej. 2026-01; gasto sin denominador) — no cero silencioso.
10. Anotar fecha/hora y resultado en `status.md` (o adjunto de demo) y, si Germán elige D1-A, reflejar en portfolio.

*(Si algún paso se fusiona — p.ej. 4+5 en una sola pantalla — mejor: el techo es ≤ 10, no “exactamente 10”.)*

---

## 6. Recomendación del agente (discutible)

1. Tratar **M6** como el único Must que falta para declarar salida según el propio `mvp.md`.
2. Preferir **D1-A, D2-A, D3-A, D4-A** si el objetivo es “contraste fiscal verificable” ahora, no “corpus perfecto”.
3. **D5-A**: trackear `mvp.md` cuando Germán lo apruebe; no confundir con implementación de features.
4. No promover V.7/V.8 ni 2026-01 a Must sin decisión explícita de costo/alcance.
5. Tras M6 ejecutado: una línea en `status.md` (“MVP alcanzado · fecha”) + update en `cooperledge/docs/portfolio/overview.md`.

---

## Fuentes leídas (esta sesión)

- `C:\Users\germa\watcher` — `git status` / `git log --oneline -15` / branch `main` @ `b8b4c8e`
- `knowledgebase/vision/mvp.md`
- `knowledgebase/current/status.md`
- `knowledgebase/current/next-session.md`
- `knowledgebase/vision/product-vision.md`
- `knowledgebase/backlog/backlog.md` (inicio)
- `README.md` (Quick Start)
- `C:\Users\germa\cooperledge\docs\standards\mvp-documentation-and-planning.md`
- `C:\Users\germa\cooperledge\docs\portfolio\overview.md`

**No modificado:** `mvp.md` ni archivos tracked. Este archivo es borrador nuevo untracked.
