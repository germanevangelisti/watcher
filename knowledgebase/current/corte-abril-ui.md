# Corte UI presupuesto — post abril 2026

**Fecha:** 2026-09-15  
**Pantalla:** `/presupuesto/ejecucion` (filtro provincial, solo canónicos)  
**Corpus:** feb–abr 2026 en `sqlite.db` (no commitear). Abril: 98/98 `completed`, 0 pending. 110 slots lun–vie estimados; Δ=12 encaja con Semana Santa (2–3 abr) y huecos de sección.

Capa B: compromisos del Boletín vs Ley 11.088. No es caja CGE.

## Totales en pantalla

| Métrica | Valor |
|---|---|
| Actos canónicos | 369 (lista 389 / $704.8B con paginación; KPI 369) |
| Compromiso (llamados, adjudicaciones, contratos) | $703.7B |
| Ejecución (pagos y transferencias del BO) | $1.1B |
| Sobre-compromiso (alerta >100%) | 4 organismos |
| Duplicados | 46 (−$243.6B, no suman) |

## Serie mensual (canónicos)

| Mes | Compromiso | Actos |
|---|---:|---:|
| feb 26 | $199.8B | 94 |
| mar 26 | $289.6B | 118 |
| abr 26 | $295.3B | 157 |

La serie crece por **S4 llamados**, no por pagos. Completar mayo+ va a inflar la barra ámbar, no la azul.

## Organismos (lectura)

| Organismo | Compromiso / vigente | % | Lectura |
|---|---|---:|---|
| EPEC | $238.5B / $2627.8B | 9.1% | Denominador Ley art. 11; usable |
| ACIF | $150.5B / $573.3B | 26.3% | Denominador Ley art. 15; CGE usa otro perímetro (~$1.82T) |
| Secretaría de Desarrollo | $50.6B / $1.9B | 2703.7% | Denominador de un programa chico / nombre truncado |
| Min. Economía y Gestión Pública | $34.5B / $23.7B | 145.3% | Match a programa, no al techo del ministerio |
| Dirección de Ministerio | $25.3B / $8.6B | 295.4% | Falso positivo S-511 (Las Peñas) → Inteligencia Fiscal |
| Poder Judicial | $18.2B / $11.2B | 162.9% | CGE vigente PJ ~$704B; Watcher pegó un programa de $11.2B |
| Min. Seguridad | $815M / $219.4B | 0.4% | Suelo de avisos; CGE T1 devengado ~$272B |

Ejecución BO ~0% en casi todos: el boletín casi no publica pagos SIGAF.

## Qué no cambiar

- Dos barras (compromiso ≠ ejecución). No meter pagado CGE en la misma.
- Mostrar alerta >100%; no silenciar S-511 sin arreglar el match.
- Filtro default provincial.

Siguiente historia: [V.2](../backlog/V.2-matching-denominador.md).
