# Inventario calendario vs DB — V.1.1

**Rango:** 2026-02-02 → 2026-03-31
**Modo de publicación:** `cached`

Capa A: pipeline vs boletín. No es ejecución SIGAF/CGE.

## Métricas

| Métrica | Valor |
|---|---:|
| Días hábiles (lun–vie, regla de sync) | 42 |
| Slots candidatos (día × S1–S5) | 210 |
| Días con PDF publicado | 38 |
| Slots publicados | 188 |
| Filas `boletines` en rango | 198 |
| `completed` | 188 |
| `failed`/`error` | 10 |
| `pending`/`processing` | 0 |
| otro status | 0 |
| Slots publicados y `completed` en DB | 188 |
| % días publicados cubiertos (todas las secciones) | 100.0% |
| % secciones publicadas presentes (`completed`) | 100.0% |
| Huecos (publicado, ausente en DB) | 0 |
| Weekdays sin PDF (feriado / no salió) | 4 |

## Secciones por día

| Fecha | Publicadas | En DB | Completed | Failed | Pending | Cubiertas |
|---|---:|---:|---:|---:|---:|---:|
| 2026-02-02 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-03 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-04 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-05 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-06 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-09 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-10 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-11 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-12 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-13 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-16 | 0 | 5 | 0 | 5 | 0 | 0 |
| 2026-02-17 | 0 | 5 | 0 | 5 | 0 | 0 |
| 2026-02-18 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-19 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-20 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-23 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-24 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-25 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-26 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-02-27 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-02 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-03 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-04 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-05 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-06 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-09 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-10 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-11 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-12 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-13 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-16 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-17 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-18 | 4 | 4 | 4 | 0 | 0 | 4 |
| 2026-03-19 | 4 | 4 | 4 | 0 | 0 | 4 |
| 2026-03-20 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-23 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-03-24 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-03-25 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-26 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-27 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-30 | 5 | 5 | 5 | 0 | 0 | 5 |
| 2026-03-31 | 5 | 5 | 5 | 0 | 0 | 5 |

## Huecos — publicados y no están en `boletines`

_Ninguno._

## Failed / error

| id | Fecha | Sección | Status | Filename | Error |
|---|---:|---:|---|---|---|
| 101 | 2026-02-16 | S1 | failed | 20260216_1_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 102 | 2026-02-16 | S3 | failed | 20260216_3_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 103 | 2026-02-16 | S4 | failed | 20260216_4_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 104 | 2026-02-16 | S5 | failed | 20260216_5_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 105 | 2026-02-16 | S2 | failed | 20260216_2_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 106 | 2026-02-17 | S1 | failed | 20260217_1_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 107 | 2026-02-17 | S3 | failed | 20260217_3_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 108 | 2026-02-17 | S4 | failed | 20260217_4_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 109 | 2026-02-17 | S5 | failed | 20260217_5_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 110 | 2026-02-17 | S2 | failed | 20260217_2_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |

## Pending / processing

_Ninguno._

## En DB pero no publicados (o no en el probe)

| id | Fecha | Sección | Status | Filename | Error |
|---|---:|---:|---|---|---|
| 101 | 2026-02-16 | S1 | failed | 20260216_1_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 105 | 2026-02-16 | S2 | failed | 20260216_2_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 102 | 2026-02-16 | S3 | failed | 20260216_3_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 103 | 2026-02-16 | S4 | failed | 20260216_4_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 104 | 2026-02-16 | S5 | failed | 20260216_5_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 106 | 2026-02-17 | S1 | failed | 20260217_1_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 110 | 2026-02-17 | S2 | failed | 20260217_2_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 107 | 2026-02-17 | S3 | failed | 20260217_3_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 108 | 2026-02-17 | S4 | failed | 20260217_4_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |
| 109 | 2026-02-17 | S5 | failed | 20260217_5_Secc.pdf | justified: Carnaval 2026, HTTP 404 (no salió boletín) |

## Weekdays sin PDF

2026-02-16, 2026-02-17, 2026-03-23, 2026-03-24

## Notas

- Inventario sobre lo que `sync` persistió en `boletines`, no sobre disco.
- No mezclar con ejecución CGE/SIGAF.
- Probes leídos de ..\watcher-doc\data\2026\cobertura_probes.json

## Lectura

- Feriado / no salió: weekday sin PDF (p.ej. Carnaval) no es hueco de pipeline. Carnaval 16–17 feb queda `failed` justificado; 23–24 mar no tienen fila porque el BO no publicó.
- Hueco: publicado en el BO y ausente en `boletines`.
- `pending`: PDF registrado; la extracción LLM no cerró el slot.
- Capa A solamente: no mezclar este inventario con CGE/SIGAF.
