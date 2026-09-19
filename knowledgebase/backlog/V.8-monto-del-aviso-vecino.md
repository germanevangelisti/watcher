# V.8 El monto del aviso vecino y la coma que se cae

**Épica:** V — Verificación / ground truth (capa A: pipeline vs boletín)
**Puntos:** 5
**Estado:** pendiente (hallazgo declarado; el caso catastrófico está reparado a mano)
**Rama:** `main`
**Depende de:** V.5 (lo destapó la verificación de la ingesta)
**Origen:** hallazgo medido durante V.5, 2026-09-19
**Relacionada:** V.7 (misma página, misma causa de fondo: el texto aplanado)

---

## Objetivo

En una página con varios avisos seguidos, el modelo local (LocalPro `qwen2.5:7b`)
le pone al acto **el monto del aviso vecino**, o **el precio de publicación** del
boletín, o el número correcto con la **coma decimal caída (×100)**. `crud.py:208`
copia el número del modelo tal cual cuando viene numérico > 0, así que el error se
persiste sin ningún control.

No es teoría: el caso mayor metió **$3,0 billones** en el ledger — el número más
grande del producto — y fabricó una alerta de **10.850%**.

## Caso testigo, verificado por columna

`20260903_4_Secc.pdf` (boletín 712), **página 4**. La **columna izquierda** trae
cinco licitaciones de EPEC, cada una encabezada por `EMPRESA PROVINCIAL DE ENERGIA
DE CORDOBA S.A.U.` y con su presupuesto contiguo (leído con
`extract_text(layout=True)` y separando por columna; la columna derecha es de la
Defensoría, y su texto `MINISTERIO PÚBLICO DE LA DEFENSA` cae en la misma línea
que el encabezado de la 5591).

| acto | impreso en el boletín (col. izq.) | guardado | veredicto |
|---|---|---|---|
| 5591 | `$ 3.679.368.000,00` | `1.493.640,00` | mal: es la tasa BOE (`$ 14936,40`) con la coma caída |
| 5592 | `$ 30.000.077.244,29` | `3.000.007.724.429` | mal: la misma cifra con la **coma caída (×100)** |
| 5593 | `$ 6.023.864.000,00` | `6.023.864.000` | **ok** |
| 5594 | `$ 3.784.396.000,00` | `3.784.396.000` | **ok** |
| 5595 | *(no imprime presupuesto: el aviso se corta en el salto de página)* | `12.796.640,00` | mal: la tasa BOE (`$ 127966,40`) ×100 |

Las cinco quedaron además atribuidas a **`Ministerio Público de la Defensa`**, que
es el texto de la **otra columna**.

**La firma del ×100 es el estado de los centavos.** Los dos montos que salieron
bien son justamente los de centavos `,00`: ahí tirar la coma no cambia el número.
Los tres que salieron mal tienen centavos no nulos (`,29`, `,40`).

## Qué es reproducible y qué no (medido)

- **El formato no es el problema.** Sondeando al modelo real (`qwen2.5:7b`, el que
  usa `process_pending.py`) con cuatro textos controlados —centavos de 2 dígitos,
  `,00`, un monto grande con `,01`, un monto chico— devuelve **siempre el número
  correcto** (`30000077244.29`, `3784396000`, `237291285000.01`, `43130000`). Tres
  intentos, ninguno reprodujo el ×100.
- **El monto del vecino sí es reproducible.** Alimentando al mismo modelo con el
  fragmento crudo y aplanado de esa página, la licitación 5592 salió con
  `monto_total_numerico = 3784396000` — el presupuesto del aviso de alumbrado
  contiguo — y con el organismo correcto (EPEC). O sea: **el error de asignación
  entre avisos se repite; el ×100 no se repite, pero ocurrió tres veces en una
  sola página.**
- **La tasa es desconocida.** No se puede medir sobre el fragmento guardado, y esto
  tiene causa medida: `analisis.fragmento` no es el texto que leyó el modelo, es la
  **cita que el modelo devolvió** (`texto_original`, `intelligence_provider.py:184`
  y `local_intelligence.py:191`), que casi nunca incluye la línea del presupuesto
  —**3114 de 3174 filas (98,1%)** no traen ningún monto `$` en su fragmento—. Un
  oráculo por regex sobre el fragmento mide el fragmento, no el defecto; el primero
  que escribí además truncaba los números de 5 dígitos (`71845` → `718`). **Los dos
  instrumentos están tirados. El oráculo válido es el PDF completo**, y sólo sirve
  donde el PDF existe (ver el hallazgo 7 de V.5: 123 filas `completed` sin archivo).

**Dónde tiene que correr el guard, entonces.** En línea, dentro de la extracción,
donde el texto de entrada **sí** está disponible (`pipeline.py:1606` /
`batch_processor.py:315`): ahí el contraste "numérico del modelo vs parseo nuestro
del mismo texto" es decidible. Fuera de línea, contra el PDF.

Sub-población medible hoy: cuando la cita del propio modelo trae un monto (60 filas
del corpus), **44 coinciden con el guardado y 16 no** — entre ellos `8152`, que
guardó `$1.091.398.522,50` donde el texto dice `$2.485.340.000,00`. Es chico pero es
un caso donde el modelo se contradice **a sí mismo** y el pipeline no lo nota.

## Impacto

| | valor |
|---|---|
| ledger canónico **en ese corte** | $4.872,37B (crece con la extracción: es un corte, no un techo) |
| el acto 5592 | $3.000,01B = **62%** de ese corte |
| alerta fabricada | `MINISTERIO PUBLICO DE DEFENSA` comp = **10.850%** |
| monto correcto | $30,00B |

Con el valor impreso, **los cinco actos salen de la Defensoría y vuelven a EPEC**: el
numerador de `MINISTERIO PUBLICO DE DEFENSA` queda en ~$0,000B (un solo acto real
del 27-ago), o sea que **la alerta de 10.850% desaparece** —no se "vuelve legible",
como estimé al principio: no queda nada que alertar—. Lo que sí queda por medir es
el % de EPEC, que recibe **$43,49B** en su lugar (3,679368 + 30,000077 + 6,023864 +
3,784396 + 0). Predicción escrita **antes** del ETL en V.5, para poder fallar.

## Segundo testigo: los edictos que se quedaron con la obra de al lado

Más limpio que el primero, porque el acto no tiene monto **de ninguna clase**.
Cuatro edictos del Registro de Posesión de la Unidad Ejecutora Ley 9150 (`analisis`
8250, 8251, 8256, 8257) quedaron con el monto y la descripción de una **obra**.
Está probado contra el PDF: en `20260917_4_Secc.pdf` pág. 11 y
`20260918_4_Secc.pdf` pág. 11, la misma línea dice

```
topografía de la zona de estudio es de llanura. Monto: $ 6.711.331.994,07, EDICTOS: El presidente de la Unidad Ejecutora...
```

El monto es de la obra "MEJORAMIENTO CAMINOS S-242 y T027-26"; el bloque de edictos
que sigue no enuncia ninguno. **El valor guardado es el impreso exacto**: el modelo
leyó bien el número y se lo dio al acto equivocado, que es la misma conclusión del
repro de la 5592.

| | valor |
|---|---|
| `analisis` afectado | $26,85B (4 filas) |
| canónico en el ledger | $20,18B |
| alerta fabricada | `UNIDAD EJECUTORA PARA SANEAMIENTO` comp = **1030,08%** |
| clase entera (fragmento con "EDICTOS" y monto > 0) | 55 filas, $26,95B → **4 grandes y 51 de ≤$0,015B** |

Reparado con evidencia en `datos_extra` (monto a 0, `is_gasto_publico=0`); la clase
queda en $0,10B. **Cuidado con la conclusión fácil**: la cita del modelo en esas
filas no trae monto, pero el **texto de la página sí** (el de la obra vecina), así
que un guard que sólo compare el numérico contra el texto de entrada **no** las
habría cazado — ver el criterio de aceptación, donde está el porqué.

## Reparación hecha (declarada, no silenciosa)

`.tmp_ingesta/repara_epec_20260903.py` corrige las **5 filas de `analisis`** con el
valor impreso en la columna, y deja la evidencia **dentro de la fila**
(`datos_extra.correccion_2026_09_19` con el valor antes/después y la fuente). El
ledger no se toca a mano: `etl_analisis_to_ejecucion.py` lo reconstruye desde
`analisis`.

**Límite de la reparación:** es una reparación **de datos**, no de código. Si el
boletín se re-extrae, el error vuelve. Y sólo cubre lo que se verificó página por
página; el resto del corpus no está auditado.

## Criterio de aceptación (cuando se aborde)

- [ ] **Guard en `crud.py:208`** (donde hoy se copia el número del modelo sin
      control). **Corrección importante, medida antes de escribir el guard: la cita
      del modelo NO sirve como insumo** — sólo **60 de 3174** filas (1,9%) traen
      algún monto `$` en su `fragmento`, así que una regla del tipo "si su cita no
      tiene monto, rechazar el numérico" marcaría el **98% del corpus**. El insumo
      tiene que ser **el texto que entró al modelo** (disponible en línea, en
      `pipeline.py:1606` / `batch_processor.py:315`), no `analisis.fragmento`.
      Con ese insumo, sí:
      1. Si el texto de entrada **no enuncia ningún monto** y el modelo devuelve uno
         → contradicción: `requiere_revision`, no entra al canónico.
      2. Si enuncia montos y el numérico no coincide con ninguno (ni con el parseo
         de la coma) → lo mismo. Habría cazado `8152` ($1.091.398.522,50 guardado
         contra $2.485.340.000,00 en su propio texto).
      Tests que fallan primero, con `8152` como fixture.
- [ ] **Y decir lo que el guard NO arregla.** Para la clase de los edictos el guard
      numérico **no alcanza**: el texto de la página **sí imprime** el monto de la
      obra vecina (`$ 6.711.331.994,07`), así que la regla 2 lo ve y lo acepta. Lo
      que hace falta ahí es que el extractor no mezcle las columnas: **el guard real
      de esa clase es V.7**. V.8 y V.7 no son la misma historia con dos nombres, pero
      V.7 es la que previene y V.8 la que detecta el subconjunto detectable.
- [ ] **Contra-ejemplo**: un monto legítimamente grande no se puede rechazar por
      tamaño. EPEC 5576 ($237,29B) y el acueducto ($110,73B) son reales: el guard
      compara **contra el texto**, no contra un umbral.
- [ ] **Medir el ×100: tres instrumentos, los tres falsificados a mano (2026-09-19).**
      Queda escrito con el detalle para que nadie lo reintente igual. La conclusión
      es que **la tasa sigue sin medirse**, pero ahora se sabe *por qué*, y eso es
      un resultado, no un pendiente.
      1. **Regex sobre `analisis.fragmento`** (`monto_contra_texto.py`): truncaba
         los números de 5 dígitos y además midió que **3114 de 3174 (98,1%)** de
         los fragmentos no traen ningún `$`. No sirve: mide el fragmento.
      2. **Oráculo sobre el PDF entero** (`audita_montos_vs_pdf.py`, tokens
         anclados en separador de miles): 3216 filas → OK **983** (30,6%),
         X100 **11**, NO_ESTA 616, sin PDF 1606. **Verificadas a mano las 4 que se
         pueden mirar: 4/4 falsos positivos.** Las tres causas, medidas:
         (a) exigir separador de miles deja invisible al importe escrito sin él —
         el acta de constitución de ATLÁNTIDA DECORACIONES (2745) dice *"Un
         Millón (1000000)"* y el oráculo no puede ver ese `1000000`; (b)
         `valores()` normalizaba **cada token en las dos convenciones**, así que
         el "10.000" de la tasa de otro acto entraba también como `10,0`; (c) en
         la 4ª sección las dos columnas se interleavean y el importe del vecino
         entra al conjunto (7916: el `USD10.000,00` que dispara el ×100 es de una
         **venta de inmueble de EPEC**, no de la asesoría).
      3. **Oráculo sobre `chunk_records.text`** (`audita_v2_chunks.py`, lectura
         AR/US según la forma del token + enteros pelados): OK **2172** (67,1%),
         X100 **13** (0,40%), NO_ESTA 1050 — y con contexto de monto obligatorio
         (`$`/`pesos`/`Monto:`/`presupuesto`), X100 **12** (0,37%), casi todo en la
         3ª sección y con candidatos **repetidos** (682.000,00 cinco veces) que
         son capitales sociales. Verificado a mano 5678: el `700` que matcheaba
         estaba dentro de un **CUIT** (`20-17000176-4`).
      **Por qué la familia no puede funcionar acá**: el corpus mezcla importes con
      CUIT, DNI, expedientes y tasas; escribe importes con separador, sin
      separador y **en palabras** ("pesos trescientos cuarenta y nueve millones",
      fila 7067); y las secciones 3 y 4 interleavean columnas. Un oráculo de
      pertenencia a un conjunto de valores cambia un error por el otro, y la rama
      ×100 (pertenencia de `guardado/100`) es exactamente donde los falsos
      positivos aterrizan.
- [ ] **Y la firma "muerde sólo con centavos ≠ `,00`" no se corrobora.** Es una
      observación **de esa página** (5 licitaciones de EPEC, 3 con centavos no
      nulos mal y 2 con `,00` bien), y sirve para explicar ese bloque. Los
      candidatos de los dos oráculos son abrumadoramente montos con centavos
      `,00`, así que **no se sostiene como detector**. No usarla como regla.
- [ ] **Cobertura: la auditoría por texto NO está limitada por los PDFs perdidos**
      (corrige lo que V.5 le atribuía al hallazgo 7). `chunk_records.text`
      conserva el texto de **414 de 414** boletines `completed` y cubre
      **3237 de 3237** filas con monto > 0 (100%), **incluidas las 123 filas sin
      PDF** (123/123 con texto: 1606 filas de `analisis`, $283,18B). Lo que no se
      puede re-verificar sin el PDF es la **geometría** (la prueba por columna de
      V.7); el texto sí está.
- [ ] **Lo que sí queda probado a mano**: el defecto existe —`30.000.077.244,29`
      impreso en `20260903_4_Secc.pdf` pág. 4 y `3.000.007.724.429` guardado— y
      los candidatos de los dos oráculos se concentran en las secciones de dos
      columnas / sociedades, dirección consistente con **V.7**. Eso es dirección,
      no medición.
- [ ] **Cuantificar el daño por organismo** después del guard, no sólo el total.
- [ ] **La re-extracción** (si se decide) es una decisión de costo explícita,
      igual que en V.7: cambia las filas de `analisis` de todo el corpus.

## Fuera de alcance

- **V.7** (columnas del extractor): es la causa de fondo del "aviso vecino". Si V.7
  se arregla antes, parte de esta historia se vuelve preventiva en vez de curativa.
- **Aliases y grafías de organismo**: EPEC aparece con 6 grafías en `analisis`
  (89 + 9 + 3 + 3 + 3). Es el matcher, no el extractor.
- **Recall de extracción** (44,4% del gold set) y la unidad ejecutora del techo:
  historias propias.
