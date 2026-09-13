# Gasto público extraído de actos — corte 2026-09-13

**Fuente:** `watcher-backend/sqlite.db` en cooperledge.  
**Corpus:** 150 boletines, 29 días feb–mar 2026 + 1 sep, 5.667 filas en `analisis`.  
**Artefacto:** canvas `gasto-publico-actos` (abrir junto al chat).

## Hallazgo

La suma bruta de `monto_numerico` es **$458,4 mil millones ARS**. Eso **no** es gasto ejecutado: mezcla llamados a licitación, republicaciones, remates judiciales, actos societarios y modificaciones de partidas. `presupuesto_base`, `ejecucion_presupuestaria` y `vinculos_acto_presupuesto` están **vacíos**, así que no hay contraste con la Ley 11.088 en esta base.

Un solo pliego (pavimento S-511 Las Peñas–Isletillas, $25.341 M) publicado **8 veces** suma **$202,7 mil M = 44% del bruto**.

## Números

| Métrica | Valor |
|---|---|
| Actos | 5.667 |
| Con monto &gt; 0 | 1.701 (30%) |
| Suma bruta | $458,4 mil M |
| Dedup desc+monto (todos los tipos) | $413,6 mil M (1.610 montos distintos) |
| Tipos de gasto, dedup | $315,4 mil M (245 claves) |
| Boletines con al menos un acto | 135 / 150 |
| Status boletines | 138 completed, 11 failed, 1 pending |

Tipos de gasto = `licitacion`, `subsidio`, `transferencia`, `decreto`, `resolucion`.

### Por tipo_acto (bruto)

| tipo_acto | Actos | Con monto | Suma |
|---|---:|---:|---:|
| licitacion | 150 | 136 | $305,5 mil M |
| otro | 5.032 | 1.423 | $100,2 mil M |
| resolucion | 221 | 53 | $26,6 mil M |
| decreto | 47 | 9 | $23,9 mil M |
| subsidio | 80 | 70 | $2,3 mil M |
| transferencia | 31 | 4 | $27 M |
| designacion | 106 | 6 | ~$2.600 |

### Por sección

| Sección | Actos | Suma | Lectura |
|---|---:|---:|---|
| S4 Licitaciones | 618 | $296,1 mil M | 65% del dinero; compromiso, no pago |
| S3 Sociedades | 2.535 | $48,1 mil M | capital / escisiones, no gasto público |
| S2 Judiciales | 2.158 | $46,6 mil M | edictos y remates |
| S5 Municipales | 170 | $42,0 mil M | fuera de la Ley provincial |
| S1 Legislación | 186 | $25,5 mil M | incluye republicación S-511 |

### Riesgo

Riesgo `bajo` (256 actos) carga **$390,7 mil M**. `alto` son 8 actos / $8,8 mil M — umbral de monto, no irregularidad.

## 1 de septiembre 2026

| Sección | Actos | Monto |
|---|---:|---:|
| S4 | 16 | $20,62 mil M |
| S2 | 17 | $34,5 M |
| S5 | 7 | $0 |
| S1, S3 | 0 | — |

S4 relevante: ACIF (escuelas Capital, agua Serrano, pavimento Villa Cornú), CCU contribución por mejoras $6,71 mil M, Policía (balizas, contenedores, alfalfa). S2 es ejecución fiscal y un remate Galicia/Toyota. S5 Cosquín/Malagueño sin monto.

Calidad ese día: dos obras ACIF distintas con el **mismo** $2.114.469.923; un pliego de Policía en portugués; `numero_acto` null en todos los S4.

## Contaminación del acumulado

1. **Republicación:** S-511 × 8; EPEC James Craik $20.028 mil M × 2.
2. **No-gasto:** remates $13.500 mil M × 3; escisión Buen Credit; aumento de capital El Aguante.
3. **Modificación ≠ ejecución:** La Cumbre compensación de partidas $5.964 mil M × 4.
4. **Licitación ≠ devengado:** presupuesto oficial del pliego.
5. **Organismo sucio:** `UNIDAD EJECUTORA`, el tramo de ruta, jueces, CCU — no matchean partida.
6. **Fuera de jurisdicción provincial:** municipios S5, CCU, remates.

## Feature de producto (P.7)

Registrar **gasto acumulado detallado** y contrastarlo con presupuesto. P.1–P.6 ya están en código (parser 2026, ETL, alias, `is_duplicate`, API, página Ejecución). Falta:

1. Clasificar `is_gasto_publico` + etapa + jurisdicción.
2. Extraer `numero_acto` en S4 para que el dedup del ETL funcione.
3. Cablear el ETL al cierre del pipeline.
4. Cargar `presupuesto_base` 2026 y ampliar alias (ACIF, EPEC, Policía).
5. UI: `% monto_acumulado / monto_vigente`, alerta &gt;100%, separar compromiso de ejecución.

Orden de magnitud (no KPI): $315 mil M vs ~11,4 billones de la Ley 11.088 ≈ 2,8%, sobre ~30 días hábiles y casi todo compromiso de obra. No publicar ese % hasta filtrar y anclar partidas.

Historia: [P.7-gasto-acumulado-presupuesto.md](../backlog/P.7-gasto-acumulado-presupuesto.md).  
Próxima sesión: [next-session.md](next-session.md).
