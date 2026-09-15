# Gold set de extracción — V.1.2

| Métrica | Valor |
|---|---:|
| Actos gold | 18 |
| Matcheados contra `analisis` | 8 |
| Recall (gold recuperados) | 44.4% |
| Precisión (PDFs `complete_gasto`) | n/a |
| Error relativo medio de monto (matcheados) | 0.0% |
| S4 gold con `numero_acto` extraído | 6/13 (46.2%) |
| Gold `is_gasto_publico=false` clasificados como gasto | 0 |

## Matches

| gold_id | filename | método | numero gold | numero extraído | monto error |
|---|---|---|---|---|---:|
| g-ley-11063 | 20260202_1_Secc.pdf | numero_acto | 11063 | Ley: 11063 |  |
| g-concurso-soria | 20260202_2_Secc.pdf | unmatched | 14167382 |  |  |
| g-asamblea-mutual | 20260202_3_Secc.pdf | unmatched |  |  |  |
| g-epec-1231 | 20260202_4_Secc.pdf | unmatched | 1231 |  |  |
| g-epec-5547 | 20260202_4_Secc.pdf | numero_acto | 5547 | 5547 | 0.0% |
| g-alta-gracia-lp01 | 20260202_5_Secc.pdf | numero_acto | 01/25 | Licitación Pública 01/25 | 0.0% |
| g-pj-02-2026 | 20260220_4_Secc.pdf | numero_acto | 02/2026 | N° 02/2026 | 0.0% |
| g-epec-1252 | 20260220_4_Secc.pdf | numero_acto | 1252 | N.o 1252 | 0.0% |
| g-pj-02-2026-rep | 20260224_4_Secc.pdf | numero_acto | 02/2026 | 02/2026 | 0.0% |
| g-epec-1243 | 20260224_4_Secc.pdf | numero_acto | 1243 | 1243 | 0.0% |
| g-mds-transporte | 20260227_4_Secc.pdf | unmatched | 2026/PRSGA-00000011 |  |  |
| g-mds-transporte-rep | 20260303_4_Secc.pdf | unmatched | 2026/PRSGA-00000011 |  |  |
| g-epec-1257 | 20260303_4_Secc.pdf | unmatched | 1257 |  |  |
| g-decreto-10 | 20260304_1_Secc.pdf | unmatched | 10 |  |  |
| g-seg-neumaticos | 20260309_4_Secc.pdf | unmatched | 0909-078704/2026 |  |  |
| g-epec-1268 | 20260309_4_Secc.pdf | numero_acto | 1268 | 1268 | 0.0% |
| g-epec-1271 | 20260312_4_Secc.pdf | unmatched | 1271 |  |  |
| g-epec-1277 | 20260312_4_Secc.pdf | unmatched | 1277 |  |  |

## Gold sin match

- `g-concurso-soria` 20260202_2_Secc.pdf 14167382 Juzgado Civil Córdoba
- `g-asamblea-mutual` 20260202_3_Secc.pdf  ASOCIACION MUTUAL DE EMPLEADOS Y FUNCIONARIOS DEL MINISTERIO DE JUSTICIA DE CORDOBA
- `g-epec-1231` 20260202_4_Secc.pdf 1231 EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA
- `g-mds-transporte` 20260227_4_Secc.pdf 2026/PRSGA-00000011 Ministerio de Desarrollo Social y Promoción del Empleo
- `g-mds-transporte-rep` 20260303_4_Secc.pdf 2026/PRSGA-00000011 Ministerio de Desarrollo Social y Promoción del Empleo
- `g-epec-1257` 20260303_4_Secc.pdf 1257 EPEC
- `g-decreto-10` 20260304_1_Secc.pdf 10 Poder Ejecutivo Provincial
- `g-seg-neumaticos` 20260309_4_Secc.pdf 0909-078704/2026 Ministerio de Seguridad
- `g-epec-1271` 20260312_4_Secc.pdf 1271 EPEC
- `g-epec-1277` 20260312_4_Secc.pdf 1277 EPEC

## Corpus

- PDFs etiquetados: 12
- Actos extraídos en esos PDFs: 352
- Gold versionado en `C:/Users/germa/watcher/watcher-doc/data/2026/goldset/goldset.csv`
- PDFs en `boletines/` (gitignored). Dumps de páginas 1–4 en `watcher-doc/data/2026/goldset/*.txt`.

Precisión omitida: el gold no es exhaustivo por PDF (S4 tiene decenas de pliegos EPEC). Recall mide si Watcher recuperó los actos etiquetados a mano desde el PDF.

El scorer exige `numero_acto` con monto a ≤10% (si ambos tienen monto) y no acepta organismo+monto cuando el número extraído contradice el gold. Así se evita un falso match de `numero_acto` con otro pliego. El MAE es sobre matches honestos.
