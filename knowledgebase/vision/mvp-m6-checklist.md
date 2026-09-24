# M6 — Checklist demo salida MVP (≤ 10 pasos)

**Fecha:** 2026-09-24  
**Canónico de alcance:** [mvp.md](mvp.md)  
**Estado:** borrador untracked — **no ejecutado** como evidencia de salida  
**Corte de datos declarado:** feb–sep 2026 (según `status.md` cabecera 2026-09-19; no inventar cortes más nuevos)

> Objetivo Cooperledge: un humano ejecuta este checklist una vez; anota fecha/hora y resultado. Techo ≤ 10 pasos (no “exactamente 10”).

## Honestidad de alcance

| Bloque | Estado | Notas |
|--------|--------|-------|
| Pasos 1–9 | **Ejecutables hoy** | Cubren M3, M4, M5 (arranque), M7 |
| Paso 10 (MB) | **Pendiente de UI/API** | Aspiracional hasta implementar Must **MB**; no marcar MVP+B cerrado sin este paso en verde |

---

## Checklist

### A — Runnable ahora (M3 / M4 / M5 / M7)

1. **Arrancar backend** (API local según README Quick Start / `make` o Compose documentado del repo).
2. **Arrancar frontend** (UI v2 contra esa API).
3. **Abrir** el dashboard de presupuesto / contraste vs Ley 11.088 (ruta de ejecución / organismos documentada en UI v2).
4. **Verificar período + techo:** la UI declara **período medido** (N de 12; corte feb–sep u el que diga `status.md`) y el **techo** es verificable; programas sin dueño no están escondidos.
5. **Confirmar barras** **Publicado / Comprometido / Ejecución** distintas; **no** mezclar “pagado CGE” en el mismo cociente.
6. **Abrir alertas >100%** y ver las del corte (V.5: 3 estructurales) **con causa**; no silenciadas.
7. **Correr** `check_match_drift.py` en el corte de salida → **exit 0** (0 filas de drift).
8. **Confirmar huecos M7** visibles o documentados (p.ej. 2026-01; ~$404,52B / 364 actos sin denominador) — no cero silencioso.
9. **Anotar** fecha/hora (America/Cordoba), commit/tip si aplica, y resultado (pass/fail por paso) en nota de demo o línea en `status.md` cuando el PO lo pida.

### B — Cuando exista UI MB (Must pendiente)

10. **Abrir** la card/vista **Finalidad — techo Ley (1 / 2 / 3 + sin_clasificar)**; verificar totales de participación del techo y leer el disclaimer: **`inicial=vigente` en este corte; no es crédito modificado ni caja CGE**. Si hay proxy BO matched/techo, confirmar que **no** se llama “Devengado” y que hay banner de cobertura.

*(Si el paso 4 ya muestra período+techo en una sola pantalla, no duplicar verificación: el techo del checklist es ≤ 10.)*

---

## Criterio de “M6 hecho”

- [ ] Pasos 1–9 ejecutados una vez por un humano con resultado anotado.  
- [ ] Paso 10 ejecutado **después** de que MB (API+UI+copy) esté implementado — hasta entonces M6 puede documentarse, pero **salida con Ampliación B** sigue bloqueada por MB.  
- [ ] Sin silenciar alertas ni inventar sancionado≠vigente / Devengado BO.

## Fuera de este checklist

- V.7 / V.8, ingesta 2026-01, auth Épica 7, re-index Chroma, barra CGE en el cociente BO.