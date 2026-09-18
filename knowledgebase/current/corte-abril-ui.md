# Corte UI presupuesto — post V.2 matching (abril 2026)

**Fecha:** 2026-09-15  
**Pantalla:** `/presupuesto/ejecucion` (filtro provincial, solo canónicos)  
**Corpus:** feb–abr 2026 en `sqlite.db` (no commitear). Abril: 98/98 `completed`.

Capa B: compromisos del Boletín vs Ley 11.088. No es caja CGE.

V.2.1 diagnóstico (las 4 alertas): [bitacora-alertas-v2.md](bitacora-alertas-v2.md).  
Corte post-fix: [bitacora-alertas-v2-post.md](bitacora-alertas-v2-post.md).

## Totales en pantalla

| Métrica | Valor |
|---|---|
| Actos canónicos | 369 (KPI; lista incluye paginación) |
| Compromiso (llamados, adjudicaciones, contratos) | $703.7B |
| Ejecución (pagos y transferencias del BO) | $1.1B |
| Sobre-compromiso (alerta >100%) | **0 organismos** |
| Duplicados | 46 (−$243.6B, no suman) |

## Organismos (lectura post V.2)

| Organismo | Compromiso / vigente | % | Lectura |
|---|---|---:|---|
| EPEC | $238.5B / $2627.8B | 9.1% | Denominador Ley art. 11; usable |
| ACIF | $151.6B / $573.3B | 26.4% | Denominador Ley art. 15 |
| Min. Economía y Gestión Pública | $34.5B / $80.9B | 42.6% | Techo canónico del ministerio (antes 145% contra $23.7B) |
| Poder Judicial | $18.2B / $103.3B | 17.6% | `PODER JUDICIAL` + `PODER JUDICIAL -` (antes 163% contra $11.2B) |
| Dirección de Inteligencia Fiscal | $25.3B / — | unmatched | S-511 ya no pega a Inteligencia Fiscal / Dirección de Ministerio |
| Secretaría de Asuntos Institucionales | $34.0B / — | unmatched | Ya no cuelga de Secretaría de Desarrollo ($1.9B) |
| UNIDAD EJECUTORA / Las Peñas | $25.3B / — | unmatched | Blocklist; explícito |

La alerta >100% **sigue activa** en UI (`sobre_compromiso`). Hoy no dispara porque el matching/denominador dejó de inventar techos chicos.

## Qué no cambiar

- Dos barras (compromiso ≠ ejecución). No meter pagado CGE en la misma.
- Mostrar alerta >100% cuando vuelva a ser cierta.
- Filtro default provincial.
- No commitear `sqlite.db`. Operar: `python scripts/parse_pdf_presupuesto_2026.py --repair-db` y `python scripts/etl_analisis_to_ejecucion.py`.

Historia: [V.2](../backlog/V.2-matching-denominador.md).
