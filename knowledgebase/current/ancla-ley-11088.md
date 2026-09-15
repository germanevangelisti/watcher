# Ancla Ley 11.088 — V.1.4

Denominador = `presupuesto_base` ejercicio 2026 (parser de `Mapas-por-Programas.pdf`). No es caja CGE.

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
| MINISTERIO DE | 267 - 10.467 DESARROLLO | $98,797,409,000 | $7,002,000,000 | $91,795,409,000 |
| MINISTERIO DE SEGURIDAD | 755 - ESPECIAL LEY 10.571 (C.E.) SEGURIDAD VIAL Y | $94,452,572,000 | $4,441,170,000 | $90,011,402,000 |
| SECRETARIA DE COORDINACIÓN Y GESTIÓN | 450 - ACTIVIDADES CENTRALES DEL | $94,394,966,000 | $94,394,966,000 | $0 |
| DIRECCIÓN GENERAL DE EDUCACIÓN SUPERIOR | 357 - EDUCACIÓN SUPERIOR: JERARQUIZACIÓN DE LA | $91,691,299,000 | $91,691,299,000 | $0 |
| MINISTERIO DE SEGURIDAD | 755 - ESPECIAL LEY 10.571 (C.E.) SEGURIDAD VIAL Y | $90,011,402,000 | $4,441,170,000 | $85,570,232,000 |
| FINANCIERA | 702 - INTERPROVINCIALES DEUDA PÚBLICA | $86,049,790,000 | $86,049,790,000 | $0 |
| MINISTERIO DE | 267 - 10.467 DESARROLLO | $80,388,913,000 | $7,002,000,000 | $73,386,913,000 |
| SECRETARÍA DE SALUD | 456 - ACTIVIDADES COMUNES DE LA SECRETARÍA DE | $75,903,986,000 | $75,903,986,000 | $0 |
| DIRECCION GENERAL DE EDUCACIÓN DE JÓVENES Y ADULTOS | 366 - EDUCACIÓN PERMANENTE DE | $72,759,622,000 | $72,759,622,000 | $0 |
| SECRETARÍA DE SALUD | 456 - ACTIVIDADES COMUNES DE LA SECRETARÍA DE | $71,297,298,000 | $75,903,986,000 | $-4,606,688,000 |
| SECRETARIA DE MINISTERIO ADMISTRACION FINANCIERA | 717 - FINANCIAMIENTO MUNICIPIOS Y COMUNAS | $66,989,303,000 | $66,989,303,000 | $0 |
| DIRECCIÓN GENERAL DE EDUCACIÓN SUPERIOR | 358 - FORMACION DOCENTE | $66,519,376,000 | $66,519,376,000 | $0 |
| MINISTERIO DE EDUCACIÓN | 10 - APORTES UNIVERSIDAD PROVINCIAL DE | $65,769,269,000 | $65,769,269,000 | $0 |

## Matching S-511 / UNIDAD EJECUTORA / DIRECCIÓN DE MINISTERIO

En este corte el pliego S-511 (pavimento Las Peñas–Isletillas, ~$25.341 M) entra al ledger como `UNIDAD EJECUTORA` o el tramo de ruta, no como `DIRECCIÓN DE MINISTERIO`. El 295% de P.7.4 venía de un recorte con 1-sep; acá el falso positivo se reproduce como Jaccard contra el índice, no como fila viva.

| Query | pb_id | score | method | organismo DB | programa |
|---|---:|---:|---|---|---|
| `UNIDAD EJECUTORA` |  | 0.00 |  |  |  |
| `LAS PENAS SUD - LAS ISLETILLAS` |  | 0.00 |  |  |  |
| `DIRECCION DE MINISTERIO` | 54 | 1.00 | exact | DIRECCIÓN DE MINISTERIO | 156 - Agentes De R.G.P. INTELIGENCIA FISCAL |
| `EPEC` | 479 | 1.00 | alias+exact | EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA | 993 - EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA |
| `ACIF` | 480 | 1.00 | alias+exact | AGENCIA CORDOBA DE INVERSION Y FINANCIAMIENTO | Agencia Córdoba de Inversión y Financiamiento |
| `MINISTERIO DE SEGURIDAD` | 393 | 1.00 | exact | MINISTERIO DE SEGURIDAD | 774 - ADMINISTRACIÓN DE LOS SERVICIOS |
| `PODER JUDICIAL DE LA PROVINCIA DE CORDOBA` | 458 | 1.00 | alias+exact | PODER JUDICIAL | 925 - LA PROVINCIA (C.E.) |
| `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA` | 479 | 1.00 | exact | EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA | 993 - EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA |

## Unmatched provinciales (`is_gasto_publico=1`, sin `presupuesto_base_id`)

| Organismo | n | monto ledger |
|---|---:|---:|
| Unidad Ejecutora Ley 9150 | 8 | $2,850,000 |
| UNIDAD EJECUTORA | 8 | $25,341,355,229 |
| Secretaría de Desarrollo Sostenible | 5 | $0 |
| Ente Regulador de los Servicios Públicos de la Provincia de Córdoba (ERSeP) | 4 | $4,912,610,300 |
| EMPRESA PROVINCIAL DE ENERGÍA DE CÓRDOBA (EPEC) | 4 | $0 |
| Unidad Ejecutora | 3 | $25,341,354,989 |
| EPECO | 3 | $10,739,137,200 |
| Caminos de las Sierras S.A. | 3 | $8,991,502,515 |
| Unidad Ejecutora para el Saneamiento de Títulos | 2 | $0 |
| Unidad Ejecutora para el Saneamiento de CONSORCIO CAMINERO N° 13 | 2 | $0 |
| UNIDAD EJECUTORA LEY 9150 | 2 | $250,000 |
| MINISTERIO DE DESARROLLO SOCIAL Y PROMOCIÓN DEL EMPLEO | 2 | $0 |
| Universidad Nacional de Córdoba - Secretaría de Planeamiento | 1 | $64,984 |
| UNIVERSIDAD NACIONAL DE CÓRDOBA - Secretaría de Planeamiento Físico | 1 | $96,567 |
| Tribunal de Conducta Policial y Penitenciario | 1 | $0 |
| SECRETARÍA DE INFRAESTRUCTURA, MANTENIMIENTO Y SEGURIDAD DE LA FCEFYN-UNC | 1 | $20,992 |
| SECRETARÍA DE DESARROLLO SOSTENIBLE | 1 | $0 |
| Poder Judicial | 1 | $0 |
| OVIEDO, CARLOS ROBERTO - DNI N° 16.947.426 | 1 | $771 |
| LAS PEÑAS SUD – LAS ISLETILLAS | 1 | $25,341,354,989 |
| Juzgado Electoral de la Provincia de Córdoba | 1 | $0 |
| HOSPITAL NACIONAL DE CLÍNICAS, UNIDAD DE FORMACIÓN DE LA FACULTAD DE CIENCIAS MÉDICAS DE LA UNIVERSIDAD NACIONAL DE CÓRDOBA (UNC) | 1 | $4,186 |
| ENTE INTERMUNICIPAL DE GESTIÓN METROPOLITANA | 1 | $464,565,366 |
| Dirección de Inteligencia Fiscal | 1 | $0 |
| CAMS | 1 | $2,521,428,000 |
| BRISUELA, GISELA SO- DNI N° 17.845.811 | 1 | $432 |
