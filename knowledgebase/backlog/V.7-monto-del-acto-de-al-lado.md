# V.7 El monto del acto de al lado

**Épica:** V — Verificación / ground truth (capa A: pipeline vs boletín)
**Puntos:** 5
**Estado:** pendiente (hallazgo declarado, no arreglado)
**Rama:** `main`
**Depende de:** V.5 (el defecto lo destapó la verificación de la ingesta)
**Origen:** hallazgo medido durante V.5, 2026-09-19

---

## Objetivo

La 4ª sección del boletín se compone en **dos columnas**. El extractor aplana la
página a un solo flujo de texto, así que el `PRESUPUESTO OFICIAL` impreso en una
columna queda **inmediatamente antes** del objeto del acto de la columna vecina, y
el LLM se lo lleva. El acto queda con el monto de otro acto, de **otro organismo**.

**Esto no es un error de dedup ni del matcher: es del extractor.** Y es peor que un
monto mal: mueve plata **entre organismos**, que es justo el eje por el que divide
todo % del producto.

## Los tres casos, verificados contra la geometría del PDF

No se infirió de la heurística: se leyó el PDF con `extract_text(layout=True)` y se
separó por columna. En los tres, el monto que tiene el acto es el que el boletín
imprime **para el acto de la otra columna**.

| `analisis` | fecha | archivo | el acto | monto que tiene | monto que el boletín le imprime |
|---|---|---|---|---|---|
| 6544 | 2026-04-28 | `20260428_4_Secc.pdf` p.2 | plataforma de trabajo en altura (Poder Judicial), compulsa abreviada del T.S.J., objeto de cotización `2026/000188` | `$34.026.000.000` | **ninguno**: la compulsa no publica presupuesto. El monto es el de la licitación de leche de esa página |
| 6550 | 2026-04-29 | `20260429_4_Secc.pdf` p.2 | licitación de leche (exp. `0378-219684/2026`) | `$43.130.000` | **ninguno** en esa columna; el monto es de la `SUBASTA ELECTRÓNICA SC 2026/000005` (exp. `0927-000656/2026`, *ropa de cama*) de la columna derecha |
| 7503 | 2026-05-21 | `20260521_4_Secc.pdf` p.3 | *canales de la Provincia — Zona IV* (Secretaría de Infraestructura Hídrica y Gasífera) | `$3.291.662.574,50` | `$4.599.707.359,00` (columna izquierda). El `$3.291.662.574,50` es el de la **ACIF** para *pavimentación Barrio Rivadavia Anexo* (columna derecha) |
| 8250, 8251, 8256, 8257 | 2026-09-17 y 2026-09-18 | `20260917_4_Secc.pdf` p.11 y `20260918_4_Secc.pdf` p.11 | cuatro **edictos** del Registro de Posesión (U.E. Ley 9150), expedientes `0535-114354/2024`, `0535-115114/2026`, `0535-095446/2009` | `$6.711.331.994,07` | **ninguno**: el bloque de edictos no enuncia monto. El valor es de la obra *MEJORAMIENTO CAMINOS S-242 y T027-26* descrita arriba |

El caso 7503 es el más nítido porque el acto **sí** tiene presupuesto: el vecino le
roba el número y el propio se pierde. El organismo queda con **$4,60B de obra
medidos como $3,29B**.

**El caso de los edictos es el que trae la prueba de la columna.** Con
`extract_words()` se ve que en esa página el `EDICTOS:` de la columna derecha
arranca en `x0 = 304` (el centro de la página es 298), y que la línea que devuelve
el extractor **aplanado** es una sola:

```
topografía de la zona de estudio es de llanura. Monto: $ 6.711.331.994,07, EDICTOS: El presidente de la Unidad Ejecutora…
```

El monto pertenece al texto de la **izquierda** y el `EDICTOS:` al de la
**derecha**: el extractor los pegó en una misma línea y el modelo leyó una
adyacencia que en el papel no existe. Es la demostración más directa del mecanismo,
porque el acto afectado (**un edicto de inscripción en el Registro de Posesión**) no
tiene monto de ninguna clase. Y no se quedó en el dato: **llegó al ledger y fabricó
una alerta >100%** — el detalle y la reparación están en **V.8**.

**Segundo síntoma, misma causa.** El encabezado de la columna (`EXPEDIENTE N° …`,
`OBJETO DE COTIZACIÓN N° …`) también se hereda: 6544, 6550 y 6551 cargan **el
mismo** expediente `0378-219684/2026` con tres objetos distintos (plataforma, leche,
pistolas) porque los tres están en la misma página; 7503 y 7504 comparten
`2026/000016`. No es una segunda historia: es el mismo texto aplanado.

## Mecanismo nombrado

`app/services/extractors/pdfplumber_extractor.py:126` usa `page.extract_text()` sin
`layout=True` — el default de pdfplumber lee **de arriba hacia abajo atravesando las
dos columnas**, así que el párrafo del presupuesto de una columna cae en el flujo
justo antes del objeto de la otra. `PdfPlumberExtractor` es el extractor default
(`registry.py:30`), así que el defecto aplica a **todo el corpus**.

## Alcance: no medido, y por qué

La firma barata (mismo boletín, **mismo monto exacto**, objetos distintos) da
**52 grupos / $125,18B** (5,1% del monto extraído). **Eso no es el tamaño del
defecto y no se debe citar como si lo fuera.** Está dominado por falsos positivos:

- dos obras parecidas del mismo organismo con el **mismo presupuesto oficial**
  (es legítimo: ACIF llama bacheo zona 4 y zona 5 por el mismo monto);
- el patrón de republicación de **V.6** (el mismo par contado en dos días seguidos).

Es un **techo**, no una medición: la mayoría de esos 52 grupos no son fugas.
Quedan **3 casos verificados** y el resto es sospecha sin verificar. Medir el
alcance real exige re-extraer con columnas y comparar, o verificar geometría página
por página.

## Criterio de aceptación (cuando se aborde)

- [ ] **Test que falla primero**, con un PDF mínimo de dos columnas donde el
      presupuesto de la derecha precede al objeto de la izquierda: el acto de la
      izquierda **no** puede quedarse con ese monto.
- [ ] **Extracción por columnas**, verificada sobre los tres casos testigo y sobre
      una muestra de las secciones 1, 2, 3 y 5 (que son de una columna o de otro
      formato): el arreglo no puede romper lo que hoy funciona.
- [ ] **Medido con el camino real.** Prototipo sobre copia de la DB y A/B contra el
      canónico, con el % por organismo afectado antes y después
      (Infraestructura Hídrica, Asuntos Institucionales, Salud y Desarrollo Humano,
      Niñez) — el número que importa es el del organismo, no el total.
- [ ] **Declarar la re-ingesta.** Cambiar el extractor cambia las filas de
      `analisis` de **todo** el corpus: o se re-extrae, o los actos viejos siguen
      con el monto del vecino. Es una decisión de costo explícita, no un efecto
      colateral silencioso.
- [ ] **Ningún arreglo silencioso.** Los tres casos quedan en la KB con su monto
      correcto y el equivocado, para poder re-medir.

## Fuera de alcance

- **V.6** (republicación con dos grafías): es de la clave de dedup, ya arreglado.
  Ojo: comparte síntoma con esto —"el mismo monto en dos filas"—, así que cualquier
  medición futura de esta historia tiene que descontar V.6 primero.
- **El `numero_acto` basura** (`3 días - No 657969`, `1304`, `01/2026` repetido en 4
  actos de la sección 5): misma familia (precisión del extractor) pero otro campo.
- **Recall de extracción** (44,4% del gold set): es del numerador y tiene su historia.
- **La alerta >100% de Infraestructura Hídrica**: el denominador de programa que
  declara V.5 es un defecto **distinto** de éste. Los dos tocan al mismo organismo y
  por eso conviene no arreglarlos juntos en la misma medición.
