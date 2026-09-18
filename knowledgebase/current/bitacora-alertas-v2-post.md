# Bitácora alertas — post V.2 matching/denominador

Capa B: compromisos del Boletín vs `presupuesto_base` (Ley 11.088). No es caja CGE. Reproducible con `uv run python scripts/bitacora_alertas_v2.py`.

Alertas `sobre_compromiso` (filtro provincial, canónicos): **3**.

| Organismo UI | compromiso | vigente | % | n |
|---|---:|---:|---:|---:|
| SECRETARÍA DE DESARROLLO | $50,613,330,422 | $1,872,024,000 | 2703.67% | 4 |
| MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA | $34,450,820,322 | $23,718,656,000 | 145.25% | 3 |
| DIRECCIÓN DE MINISTERIO | $25,341,354,989 | $8,578,475,000 | 295.41% | 1 |

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
| SECRETARIA DE ASUNTOS INSTITUCIONALES | 1 | $34,026,000,000 | unmatched pb_id=— score=0.00 →  |
| SECRETARÍA GENERAL DE HÁBITAT Y DESARROLLO EMPRENDEDOR | 1 | $16,064,411,753 | unmatched pb_id=— score=0.00 →  |
| SECRETARIA DE PLANEAMIENTO FÍSICO | 1 | $397,532,869 | jaccard pb_id=136 score=0.50 → DIRECCIÓN GENERAL DE PLANEAMIENTO |
| SECRETARÍA DE PLANEAMIENTO FÍSICO | 1 | $125,385,800 | jaccard pb_id=136 score=0.50 → DIRECCIÓN GENERAL DE PLANEAMIENTO |

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
| Secretaría General de la Gobernación - Ministerio de Economía y Gestión Pública | 1 | $34,026,000,000 | substring pb_id=35 score=0.53 → MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA |
| MINISTRO DE ECONOMÍA Y GESTIÓN PÚBLICA | 1 | $391,286,760 | jaccard pb_id=35 score=0.75 → MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA |
| MINISTERIO DE ECONOMÍA Y GESTIÓN PÚBLICA | 1 | $33,533,562 | exact pb_id=367 score=1.00 → MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA |

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
| DIRECCIÓN DE INTELIGENCIA FISCAL | 1 | $25,341,354,989 | unmatched pb_id=— score=0.00 →  |

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
