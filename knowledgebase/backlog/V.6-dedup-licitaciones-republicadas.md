# V.6 El mismo acto republicado con dos grafías

**Épica:** V — Verificación / ground truth (capa A: pipeline vs boletín)
**Puntos:** 3
**Estado:** hecho (2026-09-19) — A/B re-medido sobre el corpus final; gate en exit 0
**Rama:** `main`
**Depende de:** V.5 (el defecto lo destapó la ingesta de mayo–septiembre)
**Origen:** hallazgo medido durante V.5, 2026-09-19

---

## Objetivo

El boletín **republica una licitación al día siguiente**, y el LLM escribe el
número de acto distinto cada vez: `5576` un día, `LICITACION PUBLICA No 5576` al
otro. `_normalize_acto` sólo pasa a mayúsculas y saca espacios, así que las dos
grafías dan **claves de dedup distintas** y el mismo acto entra **dos veces** al
canónico.

La dedup de republicaciones ya existe y funciona cuando la clave coincide
(`_dedup_organismo` se agregó justamente porque "el boletín republica una
licitación al día siguiente bajo una grafía variante y el organismo era el único
componente de la clave que cambiaba"). V.6 cierra el caso hermano: el que varía es
el número de acto.

## Caso testigo (verificado contra el texto, no inferido)

EPEC S.A.U — **Licitación Pública N° 5576**, objeto *"AUMENTO DE DISPONIBILIDAD
DE POTENCIA Y MEJORA TECNOLOGICA DEL COMPLEJO HIDROELÉCTRICO RÍO GRANDE"*,
presupuesto oficial **$237.291.285.000,01**, doble apertura 21-09-26:

| analisis | fecha | archivo | `numero_acto` | ledger |
|---|---|---|---|---|
| 7862 | 2026-07-22 | `20260722_4_Secc.pdf` | `5576` | `is_duplicate=0` |
| 7877 | 2026-07-23 | `20260723_4_Secc.pdf` | `LICITACION PUBLICA No 5576` | `is_duplicate=0` |

Es **un acto de $237,29B contado dos veces**: $474,58B en el ledger.

## Impacto medido (no estimado)

**A/B autoritativo:** ETL real sobre una copia de la DB, con el `_normalize_acto`
viejo y con el nuevo. El canónico total pasa de **$1.600,12B a $1.312,60B**
(**−$287,52B**), los duplicados de 151 a 183 filas, y el **% de match a
`presupuesto_base` no se mueve** (72,3%): el arreglo toca la dedup, no el matcher.

> **Corpus de esta medición:** 2026-09-19 05:00, extracción de may–sep **en
> curso** (72 de 502 boletines completados). Los meses 05–08 están parciales y
> 09 todavía vacío, así que el total crece. El **delta por mes es lo que vale**
> (es la corrección de V.6); el total absoluto se re-mide sobre el corpus final
> al cerrar V.5 y ese número es el que queda en `status.md`.

| mes | canónico antes | canónico después | delta |
|---|---|---|---|
| 2026-02 | $101,73B | $97,83B | −$3,90B |
| 2026-03 | $208,79B | $206,45B | −$2,34B |
| 2026-04 | $227,92B | $215,29B | −$12,63B |
| 2026-05 | $155,55B | $136,30B | −$19,25B |
| 2026-06 | $159,27B | $150,53B | −$8,74B |
| 2026-07 | $719,22B | $478,56B | −$240,66B |
| 2026-08 | $27,64B | $27,64B | $0,00B |

### Corpus final (re-medición prometida arriba, 2026-09-19)

Con la extracción **cerrada** (`ok=469 fail=0`), el mismo A/B sobre el mismo
código da:

| | canónico | duplicados | match |
|---|---|---|---|
| ANTES (clave vieja) | $2.089,73B | 202 | 64,8% |
| DESPUÉS (clave nueva) | $1.776,41B | 248 | 64,8% |
| **delta** | **−$313,32B** | +46 | 0 |

| mes | canónico antes | canónico después | delta |
|---|---|---|---|
| 2026-02 | $101,73B | $97,83B | −$3,90B |
| 2026-03 | $208,79B | $206,45B | −$2,34B |
| 2026-04 | $227,92B | $215,29B | −$12,63B |
| 2026-05 | $159,39B | $140,13B | −$19,26B |
| 2026-06 | $196,90B | $188,15B | −$8,75B |
| 2026-07 | $720,70B | $480,05B | −$240,65B |
| 2026-08 | $253,14B | $227,64B | −$25,50B |
| 2026-09 | $221,16B | $220,87B | −$0,29B |

**Los tres meses publicados dan idéntico al centavo** que en la medición parcial
(−$3,90B / −$2,34B / −$12,63B = **−$18,87B**): la corrección de feb–abr queda
confirmada en el corpus final. **Agosto es la fila que cambia de sentido**: en la
medición parcial daba $0,00B porque agosto estaba **sin extraer** ($27,64B);
ahora se mueve **−$25,50B**. El −$287,52B anterior queda como lo que fue: una
medición sobre corpus parcial, no un número equivocado.

El aporte sigue concentrado: la 5576 de EPEC ($237,29B) es el **76%** de julio.
Y una corrección de atribución: **esta historia nunca declaró "ACIF −$323B"** —su
única entrada ACIF es un par duplicado de **$1,06B**—; medido sobre el ledger
final, ACIF se mueve **−$9,78B**. Los $313B son EPEC y el resto repartido. Si
alguien cita un "−$323B de ACIF", no sale de acá.


**Los 33 pares que el arreglo reconoce son todos republicaciones verificadas**,
no sólo un número: cada fila que pasa a duplicada aparece en el corpus junto a su
par —número pelado un día, forma decorada al otro, mismo organismo, mismo monto al
centavo. Ejemplos:

| par | monto |
|---|---|
| `5576` (07-22) == `LICITACION PUBLICA No 5576` (07-23) | $237,29B |
| `1324` (04-29, como "1324 - GD 2026") == `…Electrónica N.o 1324` (05-04) | $12,36B |
| `0916-000465/2026` (04-23) == `Licitación Pública N° 0916-000465/2026` (04-27), ACIF | $1,06B |
| `0683-078920/2026` (04-14) == `…EXPTE. N°0683-078920/2026` (04-15), Min. de Seguridad | $0,08B |
| `1/2026` (03-10) == `Licitación Pública No 1/2026` (03-11), Mun. San Francisco | $0,44B |

El caso `1344` muestra el alcance real: tres filas del mismo pliego
(`Electrónica N.o 1344` el 06-02, `Electrónica N° 1344` y la **`Nota Aclaratoria
N° 1` del mismo pliego** el 06-08) colapsan a una sola canónica.

**Efecto sobre los meses ya publicados (declarado, no silenciado).** feb–abr se
mueven **−$18,87B**: son republicaciones que venían contadas dos veces desde
antes de V.5. No es un efecto de la ingesta y se declara como corrección de V.6.

- **EPEC, etapa `llamado`:** $564,54B canónicos → **$327,25B** sin la duplicación.
  Contra su techo de $2.627,77B pasa de 21,5% a 12,5%. No dispara alerta >100%,
  pero deforma el número publicado al doble en esa etapa. *(Medido sobre el corpus
  parcial; la etapa no se re-midió sobre el final.)*
- **Sobre el canónico de mayo–septiembre:** $237,29B es el **76%** del delta de
  julio sobre el corpus final (el "23% de $1,034T" de la medición parcial queda
  viejo: ese total era con la extracción en curso).

> **Tres números, uno solo vale.** Un primer barrido por heurística de substrings
> sugirió 58 grupos / $304,66B; un prototipo de clave por texto dio $259,58B; el
> A/B del ETL real da **−$313,32B** sobre el corpus final (**−$287,52B** sobre el
> parcial), que es el autoritativo porque corre el camino de producción. Los otros
> dos eran aproximaciones con falsos positivos y falsos negativos. Queda escrito
> para que nadie cite el equivocado.

## Criterio de aceptación

- [x] **Test que falla primero.** `_normalize_acto('LICITACION PUBLICA No 5576')`
      y `_normalize_acto('5576')` devuelven **la misma** clave. (Falló primero con
      las dos claves reales impresas en el assert.)
- [x] **Contra-ejemplos que no se pueden fusionar** (todos con test):
      `5561` vs `5562` (licitaciones distintas, mismo organismo) siguen distintas;
      `DECRETO N° 456/2026` vs `RESOLUCION N° 456/2026` **no** se fusionan;
      `N/A`, `S/N` y vacío siguen devolviendo `None` (sin clave → no deduplica).
      Los 33 pares que el arreglo reconoce se revisaron uno por uno: todos son
      republicaciones del mismo pliego, ninguno una fusión falsa.
- [x] **El campo que ve el usuario no cambia.** `numero_acto` se muestra en
      `boletin-detail.tsx`: el arreglo va en la **clave**, no en el dato guardado.
      La pantalla sigue mostrando `LICITACION PUBLICA No 5576`.
- [x] **A/B del canónico medido y declarado**: el delta por mes se reporta, no se
      silencia. **Re-medido sobre el corpus final al cerrar V.5** (−$313,32B; ver
      *Corpus final*, arriba).
- [x] **El gate sigue verde**: `check_match_drift.py` exit 0 después del cambio
      (la dedup no toca `presupuesto_base_id`, pero se verifica).
      **Medido al cerrar V.5, sobre la DB real con el corpus completo: exit 0,
      0 filas con deriva, 0 sin match.**
- [x] **`make test` y `make lint`**: `test_etl_presupuesto.py` 151/151 (7 tests
      nuevos); el resto del suite igual que antes (15 fallos pre-existentes de
      DT-2/DT-3, ninguno de dedup/ETL). Lint: **0 errores nuevos** — el archivo de
      producto queda limpio y los 8 E501 del archivo de tests son pre-existentes.
      El residual del repo (642, DT-7) no se toca.

## Diseño del arreglo

En `app/services/presupuesto_matching.py`, `_normalize_acto` reduce a su **código**
sólo cuando el texto es una **licitación de la familia de `_NUMERO_PATTERNS[0]`**
(licitación pública/privada, compulsa abreviada, subasta electrónica, concurso de
precios, contratación directa, expediente): ahí el número **es** la identidad del
acto y el boletín lo republica textual. Se reusa el patrón que ya existe y ya está
probado — no se agrega una familia nueva de regex.

**Por qué sólo esa familia.** Reducir también `DECRETO N° 456/2026` a `456/2026`
fusionaría dos instrumentos distintos que comparten número (mismo organismo y
mismo monto redondeado a 1M), que es un falso positivo silencioso peor que la
duplicación que se quiere arreglar. Se prefiere el hueco declarado al falso
positivo.

**Descartado:** arreglarlo en `resolve_numero_acto`. Ese campo se persiste en
`analisis` y se muestra en pantalla; la reducción es una necesidad de la **clave**,
no del dato.

## Fuera de alcance (huecos declarados, con número)

- **Instrumentos numerados con tipo distinto.** `N°02/2026` vs `02/2026` (Poder
  Judicial, $4,12B) no se toca: para fusionarlos habría que tirar el tipo de
  instrumento de la clave, y ahí `DECRETO 456` ≡ `RESOLUCION 456`.
- **Grafías del organismo que `_dedup_organismo` no une.** Casos medidos:
  `SECRETARIA DE INFRAESTRUCTURA HIDRICA Y GASIFERA` vs la variante con
  `DEL MINISTERIO DE SERVICIOS PUBLICOS` ($3,29B); `EPECO` vs
  `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA` ($0,57B). Es la misma familia de
  defecto en otro componente de la clave → si se abre, es su propia historia.
- **Precisión del extractor.** Un prototipo de clave por texto produjo códigos
  basura (`DE1.500` leyendo "Licitación Pública No 1/2026" seguido de
  "presupuesto $1.500.000"): razón adicional para reusar `_NUMERO_PATTERNS` en vez
  de escribir un patrón nuevo.
