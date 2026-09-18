# Ancla Ley 11.088 — V.1.4 / V.2

Denominador = `presupuesto_base` ejercicio 2026 (parser de `Mapas-por-Programas.pdf`, organismos reparados en V.2 con `--repair-db`). No es caja CGE. El JSON parseado conserva nombres pre-repair; el Δ de organismo en el sample 15 es esperado.

## Totales

| Fuente | Programas | Suma `monto_vigente` |
|---|---:|---:|
| `presupuesto_base` | 480 | $7,531,907,153,000 |
| JSON parseado | 487 | $7,572,703,493,000 |
| Δ | -7 | $-40,796,340,000 |

## EPEC / ACIF

| Organismo | DB | JSON parseado |
|---|---:|---:|
| EPEC | $2,627,774,687,000 | $2,627,774,687,000 |
| ACIF | $573,294,933,000 | $573,294,933,000 |

## Sample 15 programas (los de mayor vigente en DB)

| Organismo | Programa | vigente DB | vigente JSON | Δ |
|---|---|---:|---:|---:|
| EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA | 993 - EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA | $2,627,774,687,000 | $2,627,774,687,000 | $0 |
| AGENCIA CORDOBA DE INVERSION Y FINANCIAMIENTO | Agencia Córdoba de Inversión y Financiamiento | $573,294,933,000 | $573,294,933,000 | $0 |
| MINISTERIO DE BIOAGROINDUSTRIA | 267 - 10.467 DESARROLLO | $98,797,409,000 | — |  |
| MINISTERIO DE SEGURIDAD | 755 - ESPECIAL LEY 10.571 (C.E.) SEGURIDAD VIAL Y | $94,452,572,000 | $4,441,170,000 | $90,011,402,000 |
| SECRETARIA DE COORDINACION Y GESTION | 450 - ACTIVIDADES CENTRALES DEL | $94,394,966,000 | — |  |
| DIRECCION GENERAL DE EDUCACION SUPERIOR | 357 - EDUCACIÓN SUPERIOR: JERARQUIZACIÓN DE LA | $91,691,299,000 | — |  |
| MINISTERIO DE SEGURIDAD | 755 - ESPECIAL LEY 10.571 (C.E.) SEGURIDAD VIAL Y | $90,011,402,000 | $4,441,170,000 | $85,570,232,000 |
| FINANCIERA | 702 - INTERPROVINCIALES DEUDA PÚBLICA | $86,049,790,000 | $86,049,790,000 | $0 |
| MINISTERIO DE BIOAGROINDUSTRIA | 267 - 10.467 DESARROLLO | $80,388,913,000 | — |  |
| SECRETARIA DE SALUD | 456 - ACTIVIDADES COMUNES DE LA SECRETARÍA DE | $75,903,986,000 | — |  |
| DIRECCION GENERAL DE EDUCACION DE JOVENES Y ADULTOS | 366 - EDUCACIÓN PERMANENTE DE | $72,759,622,000 | — |  |
| SECRETARIA DE SALUD | 456 - ACTIVIDADES COMUNES DE LA SECRETARÍA DE | $71,297,298,000 | — |  |
| SECRETARIA DE MINISTERIO ADMISTRACION FINANCIERA | 717 - FINANCIAMIENTO MUNICIPIOS Y COMUNAS | $66,989,303,000 | $66,989,303,000 | $0 |
| DIRECCION GENERAL DE EDUCACION SUPERIOR | 358 - FORMACION DOCENTE | $66,519,376,000 | — |  |
| MINISTERIO DE EDUCACION | 10 - APORTES UNIVERSIDAD PROVINCIAL DE | $65,769,269,000 | — |  |

## Matching S-511 / UNIDAD EJECUTORA / DIRECCIÓN DE MINISTERIO

En este corte el pliego S-511 (pavimento Las Peñas–Isletillas, ~$25.341 M) entra al ledger como `UNIDAD EJECUTORA`, el tramo de ruta o `DIRECCIÓN DE INTELIGENCIA FISCAL`. V.2 deja esos nombres unmatched; `DIRECCIÓN DE MINISTERIO` ya no es un target de matching.

| Query | pb_id | score | method | organismo DB | programa |
|---|---:|---:|---|---|---|
| `UNIDAD EJECUTORA` |  | 0.00 |  |  |  |
| `LAS PENAS SUD - LAS ISLETILLAS` |  | 0.00 |  |  |  |
| `DIRECCION DE MINISTERIO` |  | 0.00 |  |  |  |
| `DIRECCION DE INTELIGENCIA FISCAL` |  | 0.00 |  |  |  |
| `EPEC` | 479 | 1.00 | alias+exact | EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA | 993 - EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA |
| `ACIF` | 480 | 1.00 | alias+exact | AGENCIA CORDOBA DE INVERSION Y FINANCIAMIENTO | Agencia Córdoba de Inversión y Financiamiento |
| `MINISTERIO DE SEGURIDAD` | 393 | 1.00 | exact | MINISTERIO DE SEGURIDAD | 774 - ADMINISTRACIÓN DE LOS SERVICIOS |
| `PODER JUDICIAL DE LA PROVINCIA DE CORDOBA` | 458 | 1.00 | alias+exact | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA` | 479 | 1.00 | exact | EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA | 993 - EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA |

## Unmatched provinciales (`is_gasto_publico=1`, sin `presupuesto_base_id`)

| Organismo | n | monto ledger |
|---|---:|---:|
| Unidad Ejecutora Ley 9150 | 11 | $4,884,670 |
| UNIDAD EJECUTORA | 8 | $25,341,355,229 |
| Unidad Ejecutora para el Saneamiento de Títulos | 7 | $0 |
| Caminos de las Sierras S.A. | 7 | $9,327,463,844 |
| Unidad Ejecutora | 5 | $25,341,354,989 |
| Secretaría de Desarrollo Sostenible | 5 | $0 |
| UNIVERSIDAD NACIONAL DE CÓRDOBA | 4 | $79,676,450 |
| SECRETARIA GENERAL DE HABITAT | 4 | $0 |
| EMPRESA PROVINCIAL DE ENERGÍA DE CÓRDOBA (EPEC) | 4 | $0 |
| Compras Públicas de la CBA | 4 | $0 |
| Unidad Ejecutora LEY 9150 | 3 | $3,000,000 |
| Secretaría General de Hábitat y Desarrollo Emprendedor | 3 | $0 |
| EPECO | 3 | $10,739,137,200 |
| Consorcio Caminero N° 10 | 3 | $0 |
| Unidad Ejecutora para el Saneamiento de CONSORCIO CAMINERO N° 13 | 2 | $0 |
| Unidad Ejecutora CCU | 2 | $32,128,823,505 |
| UNIDAD EJECUTORA LEY 9150 | 2 | $250,000 |
| SECRETARÍA DE DESARROLLO SOSTENIBLE | 2 | $0 |
| SECRETARÍA DE ASUNTOS INSTITUCIONALES - SECRETARÍA GENERAL DE LA GOBERNACIÓN - SECRETARIA GENERAL DE SALUD Y DESARROLLO HUMANO - MINISTERIO DE ECONOMÍA Y GESTIÓN PÚBLICA - MINISTERIO DE SALUD | 2 | $150,755,000 |
| SECRETARIA GENERAL DE HABITAT Y DESARROLLO EMPRENDEDOR | 2 | $0 |
| MINISTERIO DE DESARROLLO SOCIAL Y PROMOCIÓN DEL EMPLEO | 2 | $0 |
| Consorcio Caminero N° 259 | 2 | $0 |
| VILLARREAL ALDO ELIAS | 1 | $654,345 |
| Universidad Nacional de Córdoba - Secretaría de Planeamiento | 1 | $64,984 |
| UNIVERSIDAD NACIONAL DE CÓRDOBA - Secretaría de Planeamiento Físico | 1 | $96,567 |
| UNIVERSIDAD NACIONAL DE CÓRDOBA - SECRETARÍA DE PLANEAMIENTO | 1 | $349,006,021 |
| UNIVERSIDAD NACIONAL DE CÓRDOBA - FACULTAD DE DERECHO | 1 | $70,007 |
| Tribunal de Conducta Policial y Penitenciario | 1 | $0 |
| TRIZ | 1 | $997 |
| SECRETARÍA GENERAL DE SALUD Y DESARROLLO HUMANO, MINISTERIO DE SALUD | 1 | $139,425,865 |
| SECRETARÍA GENERAL DE HÁBITAT Y DESARROLLO EMPRENDEDOR | 1 | $16,064,411,753 |
| SECRETARÍA DE INFRAESTRUCTURA, MANTENIMIENTO Y SEGURIDAD DE LA FCEFYN-UNC | 1 | $20,992 |
| SECRETARIA DE ASUNTOS INSTITUCIONALES | 1 | $34,026,000,000 |
| Poder Judicial | 1 | $0 |
| OVIEDO, CARLOS ROBERTO - DNI N° 16.947.426 | 1 | $771 |
| MINISTRO DE ECONOMÍA Y GESTIÓN PÚBLICA | 1 | $0 |
| MENDOZA RUBEN ALBERTO | 1 | $654,371 |
| LLANOS OLEGARIO IGNACIO | 1 | $654,340 |
| LAS PEÑAS SUD – LAS ISLETILLAS | 1 | $25,341,354,989 |
| Juzgado Electoral de la Provincia de Córdoba | 1 | $0 |
| HOSPITAL NACIONAL DE CLÍNICAS, UNIDAD DE FORMACIÓN DE LA FACULTAD DE CIENCIAS MÉDICAS DE LA UNIVERSIDAD NACIONAL DE CÓRDOBA (UNC) | 1 | $4,186 |
| GOBIERNO DE LA PROVINCIA DE CÓRDOBA | 1 | $0 |
| Fundación San Roque | 1 | $0 |
| Facultad de Derecho de la Universidad Nacional de Córdoba | 1 | $27,726 |
| Facultad de Derecho - Universidad Nacional de Córdoba | 1 | $22,086 |
| ENTE INTERMUNICIPAL DE GESTIÓN METROPOLITANA | 1 | $464,565,366 |
| Dirección de Inteligencia Fiscal | 1 | $0 |
| DIRECCIÓN DE INTELIGENCIA FISCAL | 1 | $25,341,354,989 |
| Consorcio Caminero N° 411 | 1 | $0 |
| CAMS | 1 | $2,521,428,000 |
| BUSTOS DANIEL ANGEL | 1 | $654,356 |
| BRISUELA, GISELA SO- DNI N° 17.845.811 | 1 | $432 |
| Agencia Córdoba de Inversión y Financiamiento S.E.M. | 1 | $0 |
