# V.5 Ingesta mayo–septiembre

**Épica:** V — Verificación / ground truth (capa A: pipeline vs boletín)
**Puntos:** 5 (operativo: no agrega features, cierra el período)
**Estado:** hecho (2026-09-19) — extracción cerrada, ledger reconstruido, gate en 0
**Rama:** `main` (la ingesta es una operación sobre `sqlite.db`, no un cambio de código)
**Depende de:** V.4 hecho (el producto declara su período; V.5 lo extiende)
**Handoff:** [next-session.md](../current/next-session.md)

**Resultado del corte, medido:** may–sep ingeridos (472 `completed` / 33
`justified:` / 0 en vuelo, **0 fallos sin justificar**), la pantalla pasa de **3 a
8 meses** con `dias_faltantes = 0`, el ledger queda en **1220 filas / 972 canónicas
/ $1.776,41B** con **3 alertas >100%** (eran 5, ninguna nueva) y el techo intacto
en **$7,531907T**. El gasto sin denominador es **364 actos / $404,52B**, declarado
con causas. Sin una línea de código cambiada.

---

## Objetivo

El producto mide **feb–abr 2026** y hoy es **2026-09-19**. Cinco meses vencidos sin
ingerir: mientras falten, el gasto medido es un **piso**, no el avance del año, y
el % contra la Ley anual subestima por partida doble (período corto × meses
faltantes).

V.4 dejó el cociente honesto: declara su período (3 de 12), su calendario (60 días,
0 faltantes) y su techo ($7,53T, 100% con dueño). **V.5 no toca el cociente: le da
los meses que le faltan.**

## Criterio de aceptación

- [x] **Los 5 meses entran a `boletines`.** 202605 … 202609 con el calendario
      cerrado: cada día hábil (lun–vie) es `completed` (el boletín salió) o está
      justificado (`justified:`, el boletín no salió), y **0 días sin explicación**.
      El invariante del corte: días hábiles = días con PDF + weekdays sin PDF.
      **Medido al cierre:** 472 `completed` / 33 `failed` (todos `justified:`) /
      0 en vuelo · `dias_faltantes = 0` · `dias_justificados = 8` · 153 días con
      publicación. `vencidos_sin_ingesta = ('2026-01',)` — el hueco anterior al
      período declarado, que esta historia no toca.
- [x] **Los actos se extraen.** `process_pending.py` sobre los 5 meses: 0 slots
      `pending` al cerrar, y los `failed` declarados con su motivo (no borrados).
      **Medido:** `ok=469 fail=0`, y **0 fallos sin justificar en todo el corpus**.
- [x] **El ledger se re-corre y el matcher no driftea.** `etl_analisis_to_ejecucion.py`
      + `scripts/check_match_drift.py` → **exit 0**. Si el matcher vivo discrepa del
      `presupuesto_base_id` persistido, la ingesta no está cerrada.
      **Medido:** ETL real 1220 → 248 duplicados → 972 canónicos; gate **exit 0,
      0 filas**. La línea base roja (exit 1, 9 filas, $14,30B) era el estado *de
      entrada* del paso 4, no un pendiente: el re-corrido reasigna el
      `presupuesto_base_id` entero.
- [x] **La pantalla declara el período nuevo.** `cobertura_temporal` pasa de 3 a 8
      meses (feb–sep), `meses_vencidos_sin_ingesta` deja de listar may–sep, y las
      alertas >100% nuevas (si aparecen) tienen motivo medido — no se silencian.
      **Medido:** 8 de 12 meses, 0 días faltantes, may–sep fuera de vencidos; las
      alertas pasan de **5 a 3** (las dos que se van son las de extracción, con
      predicción escrita antes) y **ninguna es nueva**; las 3 tienen causa medida
      (granularidad del denominador) y siguen visibles.
- [x] **No se prorratea la Ley.** El % sigue dividiendo por la Ley anual completa.
      Es la regla que V.4 dejó escrita y V.5 no la toca. **Medido:** el techo sigue
      en 480 filas / **$7,531907T** / 0 sin dueño, idéntico al de V.4.
- [x] `knowledgebase/current/` actualizado (corte V.5 + estado + próximos pasos).
      `sqlite.db` y los PDFs **no** se commitean (gitignored).

**DoD, medido (no `make`: no está disponible en este entorno):**

- Tests: **15 failed, 670 passed, 7 skipped**. Los 15 son los **mismos 5 archivos**
  de siempre (DT-2/DT-3: `indexing_service`, `reindex_embeddings`,
  `adversarial_verification`, `pds_scrapers`, `security_middleware`), todos por
  dependencia de entorno (chromadb ausente, separador de path de Windows, event
  loop). **Cero nuevos** — y no podían serlo: esta historia **no tocó una línea de
  código**. Los `passed` suben de 663 (V.4) a 670 porque **V.6 agregó 70 líneas de
  test** después del cierre de V.4 (commit `5cd4cc9`), verificado en el `--stat`.
- Lint: **642 errores** excluyendo el scratch, exactamente el residual **DT-7** ya
  declarado y medido en V.4 ("642 en la rama y 642 en `main`"). **Cero nuevos.**
  `make lint` **no pasa** y no pasaba antes de V.5: el target corre
  `ruff check .` pero está envuelto en `command -v ruff || echo "⚠️ ruff not
  installed"`, así que **pasa en vacío** si el binario no está en el PATH. La
  deuda es DT-7, diferida a historia propia.


## Estado de partida (medido 2026-09-19, antes de tocar nada)

| | valor |
|---|---|
| Boletines en DB | 2026-02-02 → 2026-04-30 · 296 filas · 60 días |
| Meses vencidos sin ingerir | 2026-01, 2026-05 … 2026-09 |
| Fallos sin justificar en todo el corpus | **0** |
| Gasto medido (corte V.4) | $538,44B canónicos · $397,72B con denominador |
| Denominador | Ley 11.088 completa · $7,531907T · 100% con dueño |

## Procedimiento

| Paso | Comando | Qué deja |
|---|---|---|
| 1 | `scripts/ingest_month.py --month 202605` … `202609` | probe + descarga + filas `pending` |
| 2 | filas `justified:` de los feriados **y de las 3 secciones que ese día no salieron** | un weekday sin PDF no es un hueco (hallazgo 6) |
| 3 | `scripts/process_pending.py --from 202605 --to 202609` | actos extraídos (LocalPro `qwen2.5:7b`, gasto primero) |
| 4 | `scripts/etl_analisis_to_ejecucion.py` | ledger: `ejecucion_presupuestaria` |
| 5 | `scripts/check_match_drift.py` | gate: `presupuesto_base_id` persistido vs matcher vivo |

**El paso 2 es el que no existía.** Hasta ahora los feriados se justificaban con
scripts a medida por mes (`cerrar_marzo_2026.py`), y marzo 23–24 quedó sin fila. Un
día hábil sin PDF dejaba de aparecer en la tabla, y la pantalla no podía distinguir
"no se publicó" de "no lo buscamos". V.5 los registra `failed` + `justified:`, que
es lo que el agregado temporal de V.4.1 ya sabe leer.

## Hallazgos declarados (medidos, no silenciados)

### 1. V.6: la misma licitación republicada con dos grafías

La ingesta destapó que el boletín republica una licitación al día siguiente con el
número escrito distinto, y la dedup no lo reconocía: la Licitación Pública N° 5576
de EPEC ($237,29B) entró dos veces al canónico. **Tiene su propia historia (V.6)**,
ya arreglada y medida — el A/B del ETL da −$287,52B. V.6 corrige además
**−$18,87B de feb–abr**, que no es efecto de la ingesta y se declara como
corrección suya.

### 2. Las alertas >100%: cinco, cada una con su causa medida (dos no eran del cociente)

Con los meses nuevos el producto pasa de 0 a **5 alertas >100%**. Ninguna se
silencia, y ninguna queda sin causa: **dos son defectos de extracción ya reparados**
(las dos del hallazgo 5) y **tres son un choque de granularidad** entre numerador y
denominador. Medido con `causa_alertas.py`, acto por acto y fila de
`presupuesto_base` por fila:

| organismo | comp. | numerador | denominador | causa |
|---|---|---|---|---|
| MINISTERIO PUBLICO DE DEFENSA | 10.850% | $3.009,83B (6) | $27,74B (pb 459) | **extracción**: los 5 actos son el bloque EPEC mal atribuido (V.8). Al repararlo el numerador queda en ~$0 → la alerta **desaparece** |
| UNIDAD EJECUTORA PARA SANEAMIENTO | 1.030% | $20,17B (19) | $1,958B (pb 140) | **extracción**: 3 filas de $6,711B son edictos con el monto de la obra vecina (V.8). Reparado: quedan $0,04B → ~2% |
| SECRETARIA DE INFRAESTRUCTURA HIDRICA | 1.570% | $42,25B (9) | $2,690B (pb 277) | granularidad: el denominador es **una línea de programa** |
| SECRETARIA DE SEGURIDAD | 142% | $5,25B (8) | $1,844B (pb 384) | granularidad, con la prueba en la mano: **3 filas** del mismo organismo y programa (pb 384 $1,844B + pb 385 $0,615B + pb 386 $1,230B = $3,689B) y el cociente usa una sola. Con la suma daría **71%** |
| SECRETARIA DE DESARROLLO SOSTENIBLE | 185% | $0,46B (4) | $0,249B (pb 4) | granularidad: un acto de $0,390B contra un denominador de $0,249B |

El caso de Seguridad es el que **convierte la hipótesis en medición**: 64 de los 141
organismos de `presupuesto_base` tienen más de una fila, `match_organismo` elige una,
y ahí están las tres filas separadas por subprograma con su suma exacta. La causa
está probada y la dirección del arreglo también (sumar el organismo en vez de elegir
una fila), pero **mueve todos los % del producto**: es su propia historia, no un
parche de V.5.

**Cuarta alerta que casi aparece, declarada para no descubrirla después: ACIF.**
`AGENCIA CORDOBA DE INVERSION Y FINANCIAMIENTO` queda en **92,21%** en la copia del
paso 4 ($528,71B de actos canónicos contra una línea de la Ley de $573,29B), o sea
**debajo del umbral pero cerca**, y con los meses que faltan extraer puede
cruzararlo. Su composición está medida: es **casi toda `llamado`** ($528,44B de
$528,71B) y el apareo es **`substring`** en $525,69B — filas cuyo `organismo` trae
la cadena de dependencia pegada ("Agencia Córdoba de Inversión y Financiamiento
Sociedad de Economía Mixta (ACIF S.E.M.) - Secretaría de …"). Es la misma semántica
de Infraestructura Hídrica (`ETAPAS_COMPROMISO` incluye `llamado`), así que si
cruza el umbral la causa ya está nombrada y **no se va a silenciar**. Un dato más
del mismo apareo, por si alguien lo mide: las filas que dicen "Ministerio de
Infraestructura y Servicios Públicos - Agencia Córdoba de Inversión…" ($4,83B)
matchean **al Ministerio, no a ACIF** — es el matcher por substring eligiendo el
primer componente que reconoce, no el organismo que ejecuta.

Y el de Infraestructura Hídrica es la misma semántica declarada de siempre
(`ETAPAS_COMPROMISO` incluye `llamado`: el presupuesto oficial de un llamado cuenta
como compromiso) aplicada sobre un denominador de programa. **$16,57B de los $42,25B
son de mayo–junio**: la alerta la destapa la ingesta, y es una consecuencia honesta
del criterio, no un error de dato.

### 3. El gasto sin denominador se multiplicó por 2,3 (y no es un `pb_id` viejo)

Pasó de **$140,72B** (feb–abr, idéntico al corte V.4: $41,60 + $29,74 + $69,38) a
**$318,80B / 225 actos**. Todo el crecimiento es de los meses nuevos.

Lo primero que hay que descartar es que sea el `presupuesto_base_id` viejo que
vigila el gate de drift — o sea, filas que el matcher vivo ya matchea y el ETL va a
recuperar. **Medido fila por fila con el matcher vivo: recupera $4,91B, el 1,5%.**
No es eso.

Causas, verificadas una por una contra la cadena cruda y contra `presupuesto_base`:

| causa | monto | caso |
|---|---|---|
| la Ley **sí** tiene la fila y el matcher la pierde | $45,55B | ACIF: el campo `organismo` trae la cadena de dependencia pegada ("…Sociedad de Economía Mixta (ACIF S.E.M.) - Secretaría de Infraestructura Hídrica y Gasífera - Ministerio…"). La fila de ACIF en la Ley es de $573,29B |
| el ente **no tiene ninguna fila** en los datos de la Ley | $126,80B | Asuntos Institucionales $68,21B, Caminos de las Sierras $72,64B (3 grafías), Hábitat $16,06B, EPECO, APROSS, Univ. Provincial de Córdoba |
| fuera del presupuesto provincial por diseño | $41,43B | municipios, comunas, universidades nacionales |
| la obra en el campo `organismo` | $25,34B | `LAS PEÑAS SUD – LAS ISLETILLAS` (es la obra del S-511): defecto de extracción, el LLM puso la obra donde va el ente |

**Limitación de esta medición**: un clasificador automático por regex que probé
rotula mal —`Caminos de las Sierras S.A.` cae en "la obra en el campo organismo"
porque el patrón busca `SOCIEDAD`/`EMPRESA` y no ve `S.A.`—, así que **los números
de la tabla son ítem por ítem, no de un clasificador**. Se dejan escritos con esa
salvedad para que nadie los cite como un reparto exhaustivo.

### 4. El monto del acto de al lado (tiene su propia historia: V.7)

Verificando el extracto que parecía raro —dos actos de **exactamente $34.026.000.000**
con objetos distintos— apareció un defecto del **extractor**, no del numerador ni del
matcher: la 4ª sección se compone en **dos columnas**, el extractor aplana la página
a un solo flujo, y el `PRESUPUESTO OFICIAL` de una columna queda inmediatamente
antes del objeto del acto de la **columna vecina**. Tres casos leídos contra la
geometría del PDF (`extract_text(layout=True)`, no inferidos):

| `analisis` | el acto | monto que tiene | monto que el boletín le imprime |
|---|---|---|---|
| 6544 (28-abr) | plataforma en altura, compulsa del T.S.J. | $34,03B | **ninguno** (es el de la licitación de leche de esa página) |
| 6550 (29-abr) | licitación de leche | $0,04B | **ninguno** (es el de la subasta de ropa de cama) |
| 7503 (21-may) | canales Zona IV, Infraestructura Hídrica | $3,29B | **$4,60B** (el $3,29B es de la ACIF) |

La causa está nombrada: `pdfplumber_extractor.py:126` llama `page.extract_text()`
sin `layout=True`. **Mueve plata entre organismos**, así que toca el eje por el que
divide todo %. El techo barato (mismo boletín + mismo monto + objetos distintos) da
52 grupos / $125,18B, pero **no es el tamaño del defecto**: está dominado por
presupuestos oficiales idénticos de obras parecidas y por el patrón de V.6. Queda
como historia propia (**V.7**), con los tres casos y la advertencia de no citar los
$125,18B como medición.

### 5. El monto del aviso vecino, en el modelo (tiene su propia historia: V.8)

La verificación del hallazgo 4 destapó el mismo síntoma **un nivel más arriba**, en
la extracción del modelo. En `20260903_4_Secc.pdf` (boletín 712, pág. 4) hay cinco
licitaciones de EPEC en la **columna izquierda**, cada una con su presupuesto
contiguo. La extracción las guardó a las cinco bajo
`Ministerio Público de la Defensa` —el texto de la **columna derecha**— y con los
montos corridos. El peor:

| `analisis` | el acto | monto guardado | monto impreso |
|---|---|---|---|
| 8181 | L.P. 5592, ET Cruz del Eje | **$3.000,01B** | $30,00B |

**$3,0 billones: el 62% del ledger canónico**, y el origen de la alerta
`MINISTERIO PUBLICO DE DEFENSA` con **10.850%** de compromiso. La firma del error
es la **coma decimal caída (×100)**, y muerde sólo cuando los centavos no son
`,00` — por eso dos de las cinco filas salieron bien. `crud.py:208` copia el
numérico del modelo sin contraste; nuestro parser (que sí trata la coma) sólo corre
como fallback.

**Reparado y declarado**: las 5 filas de `analisis` se corrigieron contra el valor
impreso leído por columna, con la evidencia dentro de la fila
(`datos_extra.correccion_2026_09_19`). El ledger no se toca a mano: el paso 4 lo
reconstruye. **La tasa del defecto en el resto del corpus queda declarada como
desconocida, y ahora se sabe por qué**: se construyeron y se tiraron **tres
instrumentos**, y los tres quedaron falsificados por verificación a mano —el
detalle completo, con los cuatro falsos positivos probados, está en **V.8**—. Lo
que la auditoría sí dejó establecido: el texto del boletín está guardado para
**414 de 414** boletines `completed` (`chunk_records.text`), o sea que auditar es
posible; y los candidatos a ×100 se concentran en la 3ª/4ª sección, que son las
de dos columnas — dirección consistente con **V.7**, no medición. Todo el detalle
—el repro del monto del vecino, el sondeo con textos controlados, el guard
propuesto— está en **V.8**. Como V.7, es de la capa de extracción y no se arregla
acá.

**Y el defecto no se queda en un número raro: fabrica alertas.** El caso más limpio
son **4 edictos** del Registro de Posesión de la Unidad Ejecutora Ley 9150
(`analisis` 8250, 8251, 8256, 8257) a los que la extracción les puso el monto y la
descripción de la **obra de al lado**. Probado contra el PDF, no inferido: en
`20260917_4_Secc.pdf` **pág. 11** y `20260918_4_Secc.pdf` **pág. 11** —las dos, la
misma línea—

```
topografía de la zona de estudio es de llanura. Monto: $ 6.711.331.994,07, EDICTOS: El presidente de la Unidad Ejecutora...
```

El monto es de la obra "MEJORAMIENTO CAMINOS S-242 y T027-26"; lo que sigue es el
bloque de edictos, que **no enuncia ningún monto**. Detalle que importa: el valor
guardado es el impreso **exacto** (`6.711.331.994,07`), o sea que el modelo **leyó
bien el número y se lo dio al acto equivocado** — no es un problema de formato.

Efecto medido: **$26,85B en `analisis` y $20,18B canónicos** en el ledger, que son
**toda** la alerta `UNIDAD EJECUTORA PARA SANEAMIENTO comp=1030,08%`. La clase
entera, medida: de 55 filas del corpus con "EDICTOS" en el fragmento y monto > 0,
estas cuatro eran las únicas grandes; las otras 51 suman **$0,10B** (tasas BOE y
subsidios chicos: se declaran, no se tocan). Después de la reparación (monto a 0 y
`is_gasto_publico=0`, evidencia en `datos_extra`), la clase queda en **$0,10B**.
El efecto sobre el % se verifica recién en el paso 4, cuando el ETL reconstruya.

### 6. Tres huecos reales en el calendario (el "0 huecos" heredado era falso)

La afirmación que venía de la sesión anterior —"502 = 472 + 30, 0 huecos"— era
**circular**: contaba slots registrados, no secciones publicadas. Comparando el
**conjunto de secciones por día hábil** aparecen tres días en que una sección que
sale habitualmente no tiene fila:

| día hábil | sección | sondeo | vecinos |
|---|---|---|---|
| 2026-07-20 | S1 | **HTTP 404**, sin PDF en disco | S1 sale normal el 17 y el 21 |
| 2026-07-29 | S1 | **HTTP 404**, sin PDF en disco | — |
| 2026-08-26 | S5 | **HTTP 404**, sin PDF en disco | S5 sale normal el 25 y el 27 |

No son fallos de ingesta: **el boletín no publicó la sección ese día**. Se
registraron como `failed` + `justified: la sección N no salió ese día, HTTP 404
(verificado 2026-09-19)`, mismo formato que los feriados, para que el calendario
quede completo **a nivel de slot**: sin esa fila, "no lo buscamos" y "no salió" son
indistinguibles. May–sep queda en **505 filas, 33 justificadas**.

Precisión importante, medida y no supuesta: estas 3 filas **no** mueven
`dias_faltantes`. Ese contador es **por día** y un día entra como "con publicación"
si **alguna** de sus secciones salió — y esos tres días sí publicaron las otras
secciones, así que el hueco era invisible ahí. Lo que mueve `dias_faltantes` es la
**extracción** (`boletines.status='completed'` significa *documento extraído*): con
el corpus ya descargado pero sin extraer dio **93**, y bajó a 23 → 9 → **0** a
medida que el extractor completó la primera sección de cada día. Al cierre, los
días de may–sep sin ninguna sección completada son exactamente los de feriado, y
todos dicen `justified:`.

El sondeo del proyecto (`probe_slots`, con headers de navegador) es el único
instrumento usable: `curl -I` da **403 en CloudFront para todas las URLs**, incluso
las que sí existen.

### 7. 123 filas `completed` no tienen su PDF en disco (la evidencia de feb–mar)

Verificando contra los PDFs apareció que **123 filas `completed` no tienen archivo
en disco**, y el reparto no es por mes sino por **origen** de la fila:

| `origin` | PDF en disco | sin PDF |
|---|---|---|
| `downloaded` | 12 | **123** |
| `synced` | 254 | **0** |

Todas las filas que dejó la ingesta nueva (`synced`) tienen su PDF; los 123 que
faltan son de la tubería vieja (`origin='downloaded'`, feb–mar), de los cuales sólo
12 sobrevivieron. Por mes: feb 82 de 90, mar 41 de 98, abr–sep **0**.

No afecta a los números ya extraídos (el texto vive en `analisis`), pero **sí
afecta a la auditabilidad geométrica**: las historias de verificación contra el
boletín (V.7, V.8) no van a poder re-chequear actos de febrero **página por
página** —la prueba por columna necesita el PDF—. Se declara acá, no se esconde:
es la evidencia de tres meses, no un detalle de disco. Causa del borrado: **no
determinada** desde acá (el `origin` sí explica *cuáles* faltan).

**Corrección medida el mismo día, para no exagerar el alcance.** El texto de esos
123 boletines **sí está guardado**: `chunk_records.text` los cubre **123 de 123**
(1606 filas de `analisis`, $283,18B), y cubre el **100%** de las filas con monto
> 0 del corpus (414 de 414 boletines `completed`). O sea que lo que se perdió es
la **geometría**, no el texto: una auditoría por texto sigue siendo posible sobre
todo el corpus; lo que no se puede es volver al papel a medir columnas.

### 8. El gate de drift estaba rojo **antes** del paso 4 (y el paso 4 lo cierra)

`check_match_drift.py` → **exit 1**, 9 filas con deriva, $14,30B: exactamente la
línea base pre-V.5 (`drift_baseline.txt`). La ingesta no agrega deriva; la
corrección de nombres de V.4.3 dejó el `presupuesto_base_id` persistido viejo y el
re-corrido del ETL es el que lo limpia (paso 4 del procedimiento).

**Y el gate se cierra, medido sobre la copia con el ETL ya aplicado**: 0 filas con
deriva, 0 sin match, **exit 0**. Sobre ese corpus el `presupuesto_base_id` que el
ledger persiste es el que el matcher vivo asigna, así que la línea base roja no es
un pendiente de V.5 sino el estado *de entrada* del paso 4. El re-corrido no
introduce deriva nueva: **la reasigna entera**. La confirmación sobre la DB real
queda para el cierre.

## Qué tiene que pasar en el paso 4 (predicción escrita antes de medir)

Las dos reparaciones del hallazgo 5 se aplicaron sobre `analisis`, y el ledger las
va a leer recién cuando corra el ETL. Para no racionalizar después, esto es lo que
tiene que pasar, y es falsable:

| predicción | valor esperado |
|---|---|
| `MINISTERIO PUBLICO DE DEFENSA` numerador | ~$0,000B (los 5 actos EPEC salen del organismo) |
| alerta de Defensa | **desaparece** (no queda monto que alertar) |
| `UNIDAD EJECUTORA PARA SANEAMIENTO` numerador | < $0,05B (los 4 edictos salen) |
| alerta de Saneamiento | **desaparece** (~2%) |
| `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA` numerador | ≥ $43,49B (recibe los 5 actos: 3,679368 + 30,000077 + 6,023864 + 3,784396 + 0) |
| canónico del ledger | baja **$2.990,14B** respecto del estado con el defecto ($3.000,01B del 5592 + $20,18B de los edictos, menos los $30,00B correctos del 5592) |
| `presupuesto_base` (el techo) | **no se mueve**: 480 filas, $7,531907T, 0 sin dueño |
| feb–abr | **no se mueve** contra el snapshot (V.6 ya está adentro) |

Si alguna de estas no se cumple, la reparación o el ETL están mal y eso se reporta
como hallazgo, no se ajusta la expectativa.

### Verificación previa: el paso 4 corrido **sobre una copia** (2026-09-19)

La tabla de arriba se escribió antes de tocar el ledger, y en vez de esperar a que
termine la extracción para verla, el **camino real** se corrió sobre una copia
consistente de la DB: `VACUUM INTO` (no un `cp`, que puede leer una DB a medio
escribir) y después `etl_analisis_to_ejecucion.py` con `DB_PATH` apuntado a la
copia. Es el mismo código que va a correr al cierre, con el corpus en **3231 filas
de `analisis` con monto > 0** (corte: extracción todavía corriendo).

Resultado: 1105 actos de gasto público → 241 duplicados → **864 canónicos**; 779
con match (70,5%); canónico **$1.729,32B** (crudo $2.715,57B); **3 alertas >100%**;
sin denominador 267 actos $367,92B; techo **480 / $7,531907T / 0 sin dueño**.

| predicción | esperado | medido en la copia | veredicto |
|---|---|---|---|
| numerador de Defensa | ~$0,000B | **$0,0001B** (n=1) | **acierta** |
| alerta de Defensa | desaparece | **desaparece** (no está entre las 3) | **acierta** |
| numerador de Saneamiento | < $0,05B | **$0,0447B**, comp **1,89%** | **acierta** |
| alerta de Saneamiento | desaparece | **desaparece** | **acierta** |
| numerador de EPEC | ≥ $43,49B | **$594,96B** bajo la grafía `EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA`, $391,51B sumando las 6 | **acierta** |
| caída del canónico | $2.990,14B | **$3.299,37B** | **falla** |
| techo | no se mueve | 480 filas / $7,531907T / 0 sin dueño | **acierta** |
| feb–abr | no se mueve | **se mueve −$18,87B** | **falla** |

**El gate de drift no estaba en la tabla** —se escribió antes de que se me ocurriera
mirarlo—, así que no lleva veredicto: se midió después, sobre la misma copia, y dio
**exit 0 con 0 filas** (hallazgo 8). Se dice acá para que nadie lea la tabla como si
lo hubiera predicho.

Las dos que fallan **tienen motivo medido, y ninguna se ajusta**:

- **Los $2.990,14B estaban mal derivados.** Salieron de "los $3.000,01B del 5592
  + $20,18B de los edictos − $30,00B correctos del 5592", o sea de **2 de las 5
  filas EPEC**: no contaban la **suba** de 8180 (de $1,49M a $3,679B, porque lo
  guardado era la tasa BOE y lo correcto es el presupuesto) ni la de 8184. El
  resto hasta la caída total es la **dedup entre días que sólo puede hacer el ETL
  por lotes** —la tubería viva escribe boletín por boletín y no ve la
  republicación—, que es la corrección que **V.6** ya había declarado.

  > **Corrección (cierre, 2026-09-19).** Acá decía que la caída por las 9
  > reparaciones, "medida fila por fila sobre la copia", era **$2.966,33B**. Ese
  > número **no salió del ledger**: salió de `prediccion_paso4.py`, la réplica que
  > ya se había tirado, y estaba mal por **4 edictos ($26,85B)**: la réplica los
  > marcaba duplicados y el ledger real los tiene canónicos. Medido diffeando los
  > **dos ledgers reales**, es **$2.986,48B**. La cifra vieja se deja escrita
  > porque es la tercera vez que la misma réplica se equivoca en el reparto.
- **feb–abr se mueve −$18,87B**, y ese número es **el que V.6 declaró para
  feb–abr**. El `snapshot_antes.json` contra el que se comparó es anterior al pase
  por lotes, así que "V.6 ya está adentro" era falso para ese snapshot: la
  corrección entra justamente acá. No es efecto de la ingesta.

**Y no aparece ninguna alerta nueva.** Las 5 se convierten en **3**, las tres con
la causa ya declarada en el hallazgo 2 (granularidad del denominador, más el
criterio `llamado` cuenta como compromiso): Infraestructura Hídrica **1561,58%**,
Seguridad **136,01%**, Desarrollo Sostenible **184,80%**. Las dos que se van son
las dos de extracción, que es lo que la reparación buscaba.

### El paso 4 corrido sobre la DB real (cierre, 2026-09-19)

La extracción cerró con **`ok=469 fail=0`**, 0 boletines en vuelo y **0 fallos sin
justificar en todo el corpus**; `dias_faltantes = 0`, `vencidos_sin_ingesta =
('2026-01',)`. Antes de correr el ETL se tomó un `VACUUM INTO` (`pre_paso4.db`,
integridad `ok`) como punto de retorno, porque el ETL arranca con
`DELETE FROM ejecucion_presupuestaria`.

Entrada: **4619 filas de `analisis` con monto > 0** (la copia tenía 3231), ledger
vivo **1225 filas / $5.076,20B canónicos**, con feb–abr en **$538,44B** — el total
previo que este documento nombra como referencia. Salida del ETL: **1220
procesados → 248 duplicados → 972 canónicos**, 790 con match (64,8%).

| predicción | esperado | medido en la DB real | veredicto |
|---|---|---|---|
| numerador de Defensa | ~$0,000B | **$0,0001B** (n=1) | **acierta** |
| alerta de Defensa | desaparece | **desaparece** (no está entre las 3) | **acierta** |
| numerador de Saneamiento | < $0,05B | **$0,0447B**, comp **1,89%** | **acierta** |
| alerta de Saneamiento | desaparece | **desaparece** | **acierta** |
| numerador de EPEC | ≥ $43,49B | **$594,96B** (6 grafías: $391,51B) | **acierta** |
| caída del canónico | $2.990,14B | **$3.299,79B** | **falla** |
| techo | no se mueve | 480 filas / $7,531907T / 0 sin dueño | **acierta** |
| feb–abr | no se mueve | **−$18,87B** (crudo idéntico) | **falla** |

Los tres numeradores dan **al centavo lo mismo que en la copia**, con 1388 filas
de `analisis` más: la extracción que faltaba no movió a ninguno de los tres.

**La caída del canónico, desarmada con dos mediciones que no se pisan** (una
diffea los dos ledgers reales, la otra es el A/B de V.6 sobre el cambio de clave):

| componente | monto |
|---|---|
| total (pre $5.076,20B → post $1.776,41B) | **−$3.299,79B** |
| de eso: las 9 reparaciones de V.8 | **−$2.986,48B** |
| de eso: la dedup entre días de V.6 (A/B) | **−$313,32B** |
| de eso: feb–abr (dentro de V.6) | −$18,87B |

El A/B de V.6 sobre el corpus final da **−$313,32B** (canónico $2.089,73B →
$1.776,41B, duplicados 202 → 248), y los dos instrumentos cierran: la diff de
ledgers deja un resto de **$313,31B** y el A/B mide **$313,32B** por un camino
independiente. **El resto era la dedup, y ahora está medido, no inferido.**

**Lo que este cierre corrige de V.6**: su A/B declarado (−$287,52B, duplicados
151→183, agosto en $0,00B) se corrió con agosto **sin extraer**. Sobre el corpus
final es **−$313,32B** y agosto se mueve **−$25,50B**. El aporte mayor sigue
siendo la 5576 de EPEC ($237,29B, **76%** del total del mes de julio). De paso se
corrige una atribución que se me había pegado: **V.6 nunca declaró "ACIF
−$323B"** —su única entrada ACIF es un par duplicado de **$1,06B**— y medido, ACIF
se mueve **−$9,78B**. Los $313B son EPEC ($237,29B en un solo acto) y el resto
repartido.

**Y feb–abr queda explicado del todo.** Contra el snapshot tomado justo antes del
paso 4 (el que aísla la ingesta) los tres meses tienen el **crudo idéntico al
centavo** ($210,71B / $405,52B / $332,17B) y sólo suben los duplicados (19→24,
16→23, 34→40): eso es dedup, no ingesta —una ingesta de may–sep no puede agregar
filas a febrero—. La caída canónica es **−$18,87B**, exactamente la que el A/B de
V.6 le asigna a feb–abr. Las dos mediciones coinciden.

Contra el snapshot **viejo** (`snapshot_antes.json`, 03:42) feb–abr también da
−$18,87B, pero ese snapshot no distingue las dos causas. Por eso el número es el
mismo y la conclusión es distinta: la primera comparación no probaba nada.


### Un instrumento que se tiró (y por qué se anota)

Antes de correr el ETL sobre la copia escribí una **réplica** del paso 4 en Python
(`prediccion_paso4.py`), para tener la predicción sin tocar nada. Daba el total
exacto ($1.729,32B) **pero repartía distinto por organismo**: le daba a ACIF
$852,05B donde el ETL le da $528,71B, y eso la mostraba con **148,61%** —una
alerta >100% que el camino real no produce—. La causa era un bug propio: le
pasaba a `dedup_keys` el `numero_acto` **crudo**, cuando la función espera el
valor ya pasado por `_normalize_acto`. Corregido, la réplica converge al centavo
con el ETL. Se deja escrito por la moraleja, que en esta sesión se repitió tres
veces: **una réplica que coincide en el total puede estar equivocada en el
reparto, y el reparto es lo que se mira**. El instrumento válido es el camino de
producción sobre la copia.

## Riesgos
- **La extracción no es gratis en tiempo.** 472 PDFs con `qwen2.5:7b` local,
  `LLM_MAX_CONCURRENT=1` (impuesto por `process_pending.py`). El tiempo por acto es
  el recurso escaso de la sesión, no la descarga. Si no cierra entero, el estado se
  declara por mes: "may–jul extraídos, ago–sep pendientes" — nunca "hecho".
- **El ledger es acumulativo.** `etl_analisis_to_ejecucion.py` reprocesa todo: si
  duplica filas en vez de hacer upsert, el gasto medido se infla y todos los %
  suben. Se verifica contra el total previo ($538,44B canónicos) antes de mirar el
  % nuevo.
- **Un mes que entra mal es peor que un mes que falta**: un boletín a medias deja
  el período declarado como completo sin estarlo. Por eso el paso 1 verifica el
  calendario del mes **antes** de pasar al siguiente.

## Fuera de alcance

- **2026-01.** Es un hueco anterior al período que el producto declara (feb–sep) y
  esta historia no lo toca: queda listado como mes vencido sin ingesta, que es la
  verdad.
- Recall de extracción (44,4%, gold set): es del numerador y tiene su historia.
- **La fuga de monto entre columnas (V.7)** y **el monto del aviso vecino en el
  modelo (V.8)**: verificados y declarados, **no** arreglados acá. Los dos viven en
  la capa de extracción y arreglarlos cambia las filas de `analisis` de todo el
  corpus, o sea que obliga a re-extraer: es una decisión de costo explícita, no un
  parche de ingesta. Lo que sí se hizo es reparar y declarar el caso catastrófico
  de V.8 ($3,0B en una fila) contra el PDF.
- Unidad ejecutora exacta del techo y gasto sin denominador ($140,72B): son de V.4.
- DT-7 (residual de lint) y los 15 tests pre-existentes (DT-2/DT-3).
- Tercera barra "pagado CGE". No mezclar pagado CGE con compromiso/ejecución del BO.
