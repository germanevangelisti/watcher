# Trimestral CGE vs ledger — V.1.5

Corte: **acumulado a marzo 2026 (T1)** publicado por Economía y Gestión Pública / CGE. El ledger de Watcher es **proxy de compromisos publicados** en el Boletín Oficial, no tesorería.

- Portal: https://economiaygestionpublica.cba.gov.ar/publicacion/ejecucion-presupuestaria/
- Datos abiertos (zip de Excel): `https://economiaygestionpublica.cba.gov.ar/download/12397/?tmstv=1789410356`
- Informe PDF: `https://economiaygestionpublica.cba.gov.ar/download/12413/?tmstv=1789410356`
- `fuentes_dato`: updated id=3

No mezclar `pagado` CGE en la misma barra que compromiso/ejecución del boletín.

## Ocho organismos (orden de magnitud)

| Organismo | CGE vigente | CGE compromiso | CGE devengado | CGE pagado | Ledger compromiso | Ledger ejecución | n | Lectura |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| EPEC | $2,636,128.3 M | $0.0 M | $539,398.4 M | $0.0 M | $139,890.4 M | $0.0 M | 102 | mismo orden de magnitud (25.9% de CGE) |
| ACIF | $1,820,197.8 M | $0.0 M | $196,792.8 M | $168,688.8 M | $112,825.7 M | $62.7 M | 4 | mismo orden de magnitud (57.4% de CGE) |
| Poder Judicial | $704,483.2 M | $191,537.5 M | $171,384.0 M | $141,479.8 M | $8,835.0 M | $0.0 M | 3 | mismo orden de magnitud (5.2% de CGE) |
| Ministerio de Seguridad | $1,223,164.2 M | $315,558.8 M | $272,046.0 M | $186,557.4 M | $654.6 M | $0.0 M | 5 | Watcher es ~0.2% de CGE (suelo de avisos, no tesorería) |
| Ministerio de Educación | $2,531,943.3 M | $716,789.8 M | $572,909.7 M | $473,351.0 M | $0.0 M | $0.0 M | 0 | Watcher 0 — el boletín no trajo gasto canónico |
| Ministerio de Salud | $1,276,034.8 M | $400,770.0 M | $277,699.4 M | $206,603.2 M | $0.0 M | $139.4 M | 1 | Watcher es ~0.1% de CGE (suelo de avisos, no tesorería) |
| Policía de la Provincia | $1,057,975.6 M | $272,997.8 M | $247,935.7 M | $165,752.7 M | $0.0 M | $0.0 M | 0 | Watcher 0 — el boletín no trajo gasto canónico |
| Dirección de Ministerio / Inteligencia Fiscal | $0.0 M | $0.0 M | $0.0 M | $0.0 M | $25,341.4 M | $0.0 M | 1 | CGE no publica esta unidad; el ledger no es caja |

## Qué significa

- EMAEE (EPEC, ACIF) **no publica COMPROMISO**; el número de caja es DEVENGADO (EPEC) o DEVENGADO+PAGADO (ACIF).
- ACIF vigente CGE (~$1,82 billones) **no coincide** con el vigente Ley 11.088 en `presupuesto_base` (~$0,57 billones): perímetros distintos (fideicomisos / financiamiento vs programa de la Ley). Documentado, no silenciado.
- EPEC vigente CGE ≈ vigente Ley (~$2,63 billones).
- Policía es unidad 199 bajo Ministerio de Seguridad, no una jurisdicción propia.
- `Dirección de Ministerio` / Inteligencia Fiscal **no existe** como unidad CGE. El 295% de P.7 era matching del pliego S-511, no caja.
- Watcher cubre feb–mar 2026 publicado (marzo cerrado). CGE cubre todo el T1 SIGAF. El ledger es **suelo de avisos del BO**, no tesorería: un % alto vs CGE (p.ej. EPEC/ACIF) no es join acto a acto ni caja.

KPI prohibido: sumar `analisis.monto_numerico` crudo.
