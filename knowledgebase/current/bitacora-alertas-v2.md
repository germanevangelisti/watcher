# Bitácora alertas >100% — V.2.1

> **Post V.2 (2026-09-15):** 0 alertas `sobre_compromiso`. Ver [bitacora-alertas-v2-post.md](bitacora-alertas-v2-post.md) y [corte-abril-ui.md](corte-abril-ui.md). Lo que sigue es el diagnóstico **antes** del fix.

Capa B: compromisos del Boletín vs `presupuesto_base` (Ley 11.088). No es caja CGE. Reproducible con `uv run python scripts/bitacora_alertas_v2.py` (escribe el corte post-fix).

Alertas `sobre_compromiso` (filtro provincial, canónicos): **4**.

| Organismo UI | compromiso | vigente | % | n |
|---|---:|---:|---:|---:|
| SECRETARÍA DE DESARROLLO | $50,613,330,422 | $1,872,024,000 | 2703.67% | 4 |
| MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA | $34,450,820,322 | $23,718,656,000 | 145.25% | 3 |
| DIRECCIÓN DE MINISTERIO | $25,341,354,989 | $8,578,475,000 | 295.41% | 1 |
| PODER JUDICIAL | $18,188,665,592 | $11,163,852,000 | 162.92% | 16 |

## SECRETARÍA DE DESARROLLO

- compromiso $50,613,330,422 / vigente $1,872,024,000 = **2703.67%**

### Programas `presupuesto_base` con este organismo

| pb_id | programa | vigente |
|---:|---|---:|
| 7 | 556 - CIRCULAR AMBIENTE- RECURSOS | $936,012,000 |
| 8 | 556 - CIRCULAR AMBIENTE- RECURSOS | $599,512,000 |
| 9 | 556 - CIRCULAR AMBIENTE- RECURSOS | $336,500,000 |

### Filas ledger (top 25 por monto)

| id | org ledger | número | monto | etapa | pb_id | org pb | programa pb |
|---:|---|---|---:|---|---:|---|---|
| 388 | SECRETARIA DE ASUNTOS INSTITUCIONALES | Licitación Pública N° 660649 | $34,026,000,000 | llamado | 7 | SECRETARÍA DE DESARROLLO | 556 - CIRCULAR AMBIENTE- RECURSOS |
| 444 | SECRETARÍA GENERAL DE HÁBITAT Y DESARROLLO EMPRENDEDOR | MEJORAMIENTO CAMINO S-283 – TR: T259-18 –R.N. N°7. DPTO: GRAL ROCA | $16,064,411,753 | llamado | 7 | SECRETARÍA DE DESARROLLO | 556 - CIRCULAR AMBIENTE- RECURSOS |
| 387 | SECRETARIA DE PLANEAMIENTO FÍSICO | Licitación Pública N° 659660 | $397,532,869 | llamado | 7 | SECRETARÍA DE DESARROLLO | 556 - CIRCULAR AMBIENTE- RECURSOS |
| 222 | SECRETARÍA DE PLANEAMIENTO FÍSICO | 40/2026 | $125,385,800 | llamado | 7 | SECRETARÍA DE DESARROLLO | 556 - CIRCULAR AMBIENTE- RECURSOS |

### Nombres en el ledger que cuelgan de este organismo UI

| organismo ledger | n | monto | match en vivo |
|---|---:|---:|---|
| SECRETARIA DE ASUNTOS INSTITUCIONALES | 1 | $34,026,000,000 | jaccard pb_id=7 score=0.40 → SECRETARÍA DE DESARROLLO |
| SECRETARÍA GENERAL DE HÁBITAT Y DESARROLLO EMPRENDEDOR | 1 | $16,064,411,753 | jaccard pb_id=7 score=0.43 → SECRETARÍA DE DESARROLLO |
| SECRETARIA DE PLANEAMIENTO FÍSICO | 1 | $397,532,869 | jaccard pb_id=7 score=0.40 → SECRETARÍA DE DESARROLLO |
| SECRETARÍA DE PLANEAMIENTO FÍSICO | 1 | $125,385,800 | jaccard pb_id=7 score=0.40 → SECRETARÍA DE DESARROLLO |

## MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA

- compromiso $34,450,820,322 / vigente $23,718,656,000 = **145.25%**

### Programas `presupuesto_base` con este organismo

| pb_id | programa | vigente |
|---:|---|---:|
| 367 | 780 - PROYECTOS ESTRATÉGICOS | $10,510,284,000 |
| 43 | 131 - APORTES A LA AGENCIA CONECTIVIDAD | $7,200,000,000 |
| 44 | 150 - MINISTERIO DE ECONOMÍA Y GESTIÓN | $2,650,106,000 |
| 36 | 19 - APORTES AGENCIA CÓRDOBA INNOVAR Y | $1,988,085,000 |
| 35 | 16 - APORTES AGENCIA PARA LA | $1,370,181,000 |
| 41 | 84 - APORTES A AGENCIA CÓRDOBA DE | $0 |

### Filas ledger (top 25 por monto)

| id | org ledger | número | monto | etapa | pb_id | org pb | programa pb |
|---:|---|---|---:|---|---:|---|---|
| 395 | Secretaría General de la Gobernación - Ministerio de Economía y Gestión Pública | Licitación Pública EXPEDIENTE N° 0378-219684/2026 | $34,026,000,000 | llamado | 35 | MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA | 16 - APORTES AGENCIA PARA LA |
| 445 | MINISTRO DE ECONOMÍA Y GESTIÓN PÚBLICA | RESOLUCION 144 - Letra:D | $391,286,760 | contrato | 35 | MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA | 16 - APORTES AGENCIA PARA LA |
| 20 | MINISTERIO DE ECONOMÍA Y GESTIÓN PÚBLICA | 37 | $33,533,562 | contrato | 35 | MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA | 16 - APORTES AGENCIA PARA LA |

### Nombres en el ledger que cuelgan de este organismo UI

| organismo ledger | n | monto | match en vivo |
|---|---:|---:|---|
| Secretaría General de la Gobernación - Ministerio de Economía y Gestión Pública | 1 | $34,026,000,000 | jaccard pb_id=35 score=0.55 → MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA |
| MINISTRO DE ECONOMÍA Y GESTIÓN PÚBLICA | 1 | $391,286,760 | jaccard pb_id=35 score=0.71 → MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA |
| MINISTERIO DE ECONOMÍA Y GESTIÓN PÚBLICA | 1 | $33,533,562 | jaccard pb_id=35 score=1.00 → MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA |

## DIRECCIÓN DE MINISTERIO

- compromiso $25,341,354,989 / vigente $8,578,475,000 = **295.41%**

### Programas `presupuesto_base` con este organismo

| pb_id | programa | vigente |
|---:|---|---:|
| 54 | 156 - Agentes De R.G.P. INTELIGENCIA FISCAL | $8,578,475,000 |

### Filas ledger (top 25 por monto)

| id | org ledger | número | monto | etapa | pb_id | org pb | programa pb |
|---:|---|---|---:|---|---:|---|---|
| 97 | DIRECCIÓN DE INTELIGENCIA FISCAL | RESOLUCION 056/2026 | $25,341,354,989 | llamado | 54 | DIRECCIÓN DE MINISTERIO | 156 - Agentes De R.G.P. INTELIGENCIA FISCAL |

### Nombres en el ledger que cuelgan de este organismo UI

| organismo ledger | n | monto | match en vivo |
|---|---:|---:|---|
| DIRECCIÓN DE INTELIGENCIA FISCAL | 1 | $25,341,354,989 | jaccard pb_id=54 score=0.40 → DIRECCIÓN DE MINISTERIO |

## PODER JUDICIAL

- compromiso $18,188,665,592 / vigente $11,163,852,000 = **162.92%**

### Programas `presupuesto_base` con este organismo

| pb_id | programa | vigente |
|---:|---|---:|
| 442 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $5,580,901,000 |
| 446 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $2,126,870,000 |
| 447 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $1,083,850,000 |
| 444 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $887,800,000 |
| 451 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $746,880,000 |
| 443 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $399,230,000 |
| 445 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $200,230,000 |
| 452 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $76,160,000 |
| 449 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $24,480,000 |
| 448 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $22,061,000 |
| 450 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $8,940,000 |
| 453 | 922 - PROGRAMA DE APOYO AL SERVICIO DE | $4,400,000 |
| 458 | 925 - LA PROVINCIA (C.E.) | $2,050,000 |
| 440 | 920 - ADMINISTRACIÓN DE JUSTICIA - ACTIVIDADES | $0 |

### Filas ledger (top 25 por monto)

| id | org ledger | número | monto | etapa | pb_id | org pb | programa pb |
|---:|---|---|---:|---|---:|---|---|
| 221 | TRIBUNAL SUPERIOR DE JUSTICIA | 1296 | $7,728,052,200 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 90 | Poder Judicial de la Provincia de Córdoba | 02/2026 | $4,116,420,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 80 | Poder Judicial de la Provincia de Córdoba | N° 02/2026 | $4,116,420,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 47 | Poder Judicial de la Provincia de Córdoba | 01/2026 | $602,111,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 40 | Tribunal Superior de Justicia | 01/2026 | $602,111,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 312 | Tribunal Superior de Justicia | Licitación Pública N° 04/2026 | $444,624,021 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 217 | TRIBUNAL SUPERIOR DE JUSTICIA | 2026/000069 | $125,385,800 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 207 | Tribunal Superior de Justicia | COMPULSAS ABREVIADAS CONSORCIO CAMINERO N° 13 | $125,385,800 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 44 | TRIBUNAL SUPERIOR DE JUSTICIA | 2026/000031 | $52,800,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 177 | Tribunal Superior de Justicia de Córdoba | 03/2026 | $51,692,986 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 194 | TRIBUNAL SUPERIOR DE JUSTICIA | Compulsas Abreviadas N° 03/2026 | $51,692,985 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 38 | TRIBUNAL SUPERIOR DE JUSTICIA | COMPULSA ABREVIADA ELECTRÓNICA – SOLICITUD DE COTIZACIÓN N° 2026/000023 | $50,000,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 29 | TRIBUNAL SUPERIOR DE JUSTICIA | 2026/000023 | $50,000,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 101 | TRIBUNAL SUPERIOR DE JUSTICIA | 2026/000067 | $33,569,800 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 84 | TRIBUNAL SUPERIOR DE JUSTICIA | N° 2026/000032 | $19,200,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| 78 | TRIBUNAL SUPERIOR DE JUSTICIA | 2026/000032 | $19,200,000 | llamado | 458 | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |

### Nombres en el ledger que cuelgan de este organismo UI

| organismo ledger | n | monto | match en vivo |
|---|---:|---:|---|
| Poder Judicial de la Provincia de Córdoba | 3 | $8,834,951,000 | alias+exact pb_id=458 score=1.00 → PODER JUDICIAL |
| TRIBUNAL SUPERIOR DE JUSTICIA | 9 | $8,129,900,785 | alias+exact pb_id=458 score=1.00 → PODER JUDICIAL |
| Tribunal Superior de Justicia | 3 | $1,172,120,821 | alias+exact pb_id=458 score=1.00 → PODER JUDICIAL |
| Tribunal Superior de Justicia de Córdoba | 1 | $51,692,986 | alias+exact pb_id=458 score=1.00 → PODER JUDICIAL |

## Nombres cortos / truncos en `presupuesto_base`

| organismo | n programas | vigente |
|---|---:|---:|
| SECRETARÍA DE SALUD | 46 | $899,317,158,000 |
| MINISTERIO DE | 25 | $290,736,915,000 |
| SECRETARÍA DE | 14 | $134,135,483,000 |
| SECRETARIA DE MINISTERIO ADMISTRACION FINANCIERA | 6 | $130,641,060,000 |
| SECRETARIA DE COORDINACIÓN Y GESTIÓN | 2 | $110,989,436,000 |
| SECRETARIA DE SALUD | 9 | $106,449,496,000 |
| SECRETARÍA DE MEDICINA | 11 | $106,259,142,000 |
| SECRETARÍA DE POLÍTICAS | 5 | $101,787,069,000 |
| PODER JUDICIAL - | 3 | $92,112,308,000 |
| FINANCIERA | 1 | $86,049,790,000 |
| SECRETARIA DE | 8 | $73,128,469,000 |
| SECRETARIA DE PROMOCION DEL EMPLEO | 6 | $60,630,758,000 |
| SECRETARIA DE NIÑEZ | 1 | $57,964,210,000 |
| PODER LEGISLATIVO | 13 | $55,144,009,000 |
| SUBSECRETARÍA DE | 4 | $49,492,039,000 |
| SECRETARÍA DE MINISTERIO | 1 | $48,281,711,000 |
| SECRETARÍA DE INGRESOS MINISTERIO PÚBLICOS | 2 | $48,280,742,000 |
| SECRETARÍA DE TRANSPORTE | 6 | $32,580,062,000 |
| SECRETARÍA DE ACCIÓN SOCIAL | 5 | $27,022,004,000 |
| SECRETARÍA DE GESTIÓN DE RIESGO CLIMÁTICO - | 3 | $22,729,983,000 |
| SECRETARÍA DE COORDINACIÓN Y GESTIÓN | 1 | $21,033,012,000 |
| SECRETARÍA DE MINISTERIO ADMINISTRACIÓN | 3 | $20,810,330,000 |
| SECRETARÍA DE TRABAJO | 10 | $20,658,558,000 |
| SECRETARÍA DE ECONOMÍA SOCIAL | 2 | $19,340,840,000 |
| SECRETARÍA DE COORDINACIÓN Y | 4 | $19,010,035,000 |
| ADMINISTRATIVA | 8 | $13,202,387,000 |
| SECRETARÍA DE INFRAESTRUCTURA SOCIAL | 1 | $12,874,381,000 |
| SECRETARIA DE NIÑEZ ADOLESCENCIA Y FAMILIA | 3 | $11,235,778,000 |
| PODER JUDICIAL | 14 | $11,163,852,000 |
| SECRETARÍA DE INGRESOS MINISTERIO | 2 | $10,441,548,000 |
| SECRETARIA DE DERECHOS HUMANOS Y DIVERSIDAD | 1 | $7,522,286,000 |
| SECRETARÍA DE ESCRITURACIÓN Y | 2 | $5,161,900,000 |
| SECRETARÍA DE SEGURIDAD | 3 | $3,688,754,000 |
| SECRETARIA DE LA MUJER | 5 | $3,656,040,000 |
| SECRETARÍA DE CIENCIA Y MINISTERIO TECNOLOGÍA | 2 | $3,495,353,000 |
| SECRETARÍA DE GESTIÓN TERRITORIAL | 1 | $3,344,400,000 |
| SECRETARIA DE INFRAESTRUCTURA HÍDRICA Y INFRAESTRUCTURA | 1 | $2,689,975,000 |
| SECRETARÍA DE POLÍTICA MINISTERIO ECONÓMICA | 1 | $2,538,534,000 |
| SECRETARÍA DE INNOVACIÓN DESARROLLO | 1 | $2,024,885,000 |
| SECRETARÍA DE DESARROLLO | 3 | $1,872,024,000 |
