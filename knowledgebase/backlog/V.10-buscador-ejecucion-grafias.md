# V.10 El buscador de ejecución no encuentra lo que sí está

**Épica:** V — Verificación / ground truth (capa de **matching por grafía**)
**Puntos:** 3
**Estado:** pendiente (hallazgo declarado, no arreglado)
**Rama:** `feat/pack-fix-ui-chat-p0`
**Depende de:** V.9 (misma causa raíz: la identidad del organismo depende de cómo se escribió)
**Origen:** hallazgo medido en el gate manual del pack fix-ui + chat, 2026-09-29

---

## Objetivo

El buscador **Organismo** de `/presupuesto/ejecucion` filtra por coincidencia de
**texto crudo** (`ilike %…%`), no por identidad. Quien escribe el nombre de un
organismo **ve un subconjunto** de sus actos, y la UI no lo advierte: el resultado
parece completo. Es el mismo defecto que el bugfix de agrupación arregló en el
agregado, **un piso más abajo y sin arreglar** — y acá el que se equivoca es un
usuario real tipeando, no un mapa.

## Mecanismo nombrado

`app/api/v1/endpoints/presupuesto.py` — `GET /presupuesto/ejecucion/`:

```python
if organismo:
    filters.append(EjecucionPresupuestaria.organismo.ilike(f"%{organismo}%"))
```

Pega sobre la columna **cruda** `ejecucion_presupuestaria.organismo`, que guarda la
grafía que publicó el boletín. No hay columna canónica en la tabla (verificado: las
columnas son `organismo`, `beneficiario`, `concepto`, … y ninguna es canónica).

Del lado FE, `ejecucion.tsx` manda ese texto tal cual como query param
(`filters.organismo` → `useEjecucion`), y la página **no lee la URL**, así que tampoco
se puede llegar con un filtro pre-armado desde otro lado.

## El caso, medido en vivo

`Caminos de las Sierras S.A.` tiene **3 grafías** en el ledger:

| Grafía cruda | Actos | Monto |
|---|---|---|
| `Caminos de las Sierras S.A.` | 17 | $55.399,83 M |
| `CAMINOS DE LAS SIERRAS S.A.` | 6 | $20.556,17 M |
| `CÁMINOS DE LAS SIERRAS S.A.` | 4 | $675,79 M |
| **Total real** | **27** | **$76.631,78 M** |

Buscando en la UI:

| Lo que el usuario escribe | Lo que obtiene | Lo que hay |
|---|---|---|
| `CAMINOS DE LAS SIERRAS` | 23 actos · $75.955,99 M | 27 · $76.631,78 M |
| `CÁMINOS` | 4 actos · $675,79 M | (subconjunto por typo) |
| `SIERRA` (raíz sin sufijo) | **27 · $76.631,78 M** | ✅ completo, por casualidad |

La tercera fila es el diagnóstico: **el buscador acierta si el usuario escribe
"menos"** (una raíz que matchea las 3 grafías) y **falla si escribe el nombre
completo**, porque la grafía del boletín tiene un typo (`CÁMINOS`). El usuario que
escribe bien obtiene menos que el que escribe mal.

## Alcance

- **`249` grafías crudas** distintas en el ledger para `151` organismos canónicos (ver
  V.9 para las canónicas, que es la otra mitad del problema): cualquier organismo con
  más de una grafía es un buscador que devuelve de menos.
- Afecta la **tabla de actos** (lo que el usuario ve fila por fila) y su
  `total` / `total_monto` — los dos números que la página muestra como si fueran el
  universo.
- **No** afecta al agregado `/ejecucion/resumen/`, que ya se arregló (bugfix de
  agrupación) ni al chat.

## Solución propuesta (a decidir en el abordaje)

No hace falta migración. Tres caminos, de menor a mayor riesgo:

1. **Resolver la entrada a las grafías reales (preferido).** El endpoint usa la misma
   pieza que ya existe en `presupuesto_matching` / `resolver_familia_organismo`: del
   texto libre saca la **canónica**, de la canónica saca el **conjunto de grafías
   crudas** observadas, y filtra con `IN (...)`. Cero columnas nuevas, cero cambios de
   shape, y arregla exactamente el caso de arriba. Riesgo: es un `IN` con hasta N
   grafías (chico: máximo unas pocas por organismo).
2. **Autocompletar contra las canónicas (FE).** El input pasa a ser un combobox que
   ofrece los 151 organismos; el usuario no puede escribir una grafía inexistente. Es
   un cambio de UI en una página de Ampliación B (**frontera MB**: requiere OK del PO).
   Complementa a 1, no lo reemplaza: la URL y los links profundos siguen aceptando
   texto.
3. **Columna canónica persistida (descartado por ahora).** Migración + backfill del
   ledger y del ETL: es la solución "de verdad" a V.9 y V.10 juntas, pero obliga a
   re-verificar todo y no se justifica por 3 puntos.

**El síntoma es silencioso, y eso es lo que lo hace caro**: no hay error ni mensaje, el
usuario ve 23 actos y cree que hay 23.

## Criterio de aceptación (cuando se aborde)

- [ ] **Test que falla primero**, con el caso de arriba: buscando
      `CAMINOS DE LAS SIERRAS` el endpoint devuelve **27** actos y $76.631,78 M, no 23
      ni $75.955,99 M.
- [ ] **Test del typo**: `CÁMINOS` deja de ser una búsqueda distinta de `CAMINOS`
      (las dos grafías son el mismo organismo).
- [ ] **Test de no-sobre-fusión**: buscar `Secretaría de Salud` **no** devuelve actos de
      un organismo distinto que comparta tokens (mismo estándar que el bugfix de
      agrupación: huella compartida o nada).
- [ ] **Sin cambios de shape**: mismos params, mismas claves, mismos tipos.
- [ ] **Si entra la opción 2 (autocompletar)**: OK explícito del PO por la frontera MB
      y prueba manual en `/presupuesto/ejecucion`.
- [ ] **Coherencia entre superficies**, verificada y anotada: el número del buscador, el
      del agregado y el del chat para el mismo organismo tienen que ser **el mismo**
      (hoy Caminos da 23 en el buscador y 27 en el resto).

## Fuera de alcance

- **V.9** (canónicas distintas para el mismo organismo): es la otra mitad. Si se hacen
  por separado, **V.9 primero** — arreglar el buscador sin arreglar las canónicas deja
  el mismo organismo en dos filas de la tabla.
- **El agregado** ya arreglado (bugfix de agrupación).
- **Nombres encadenados** y **garbling del extractor** (V.7/V.8): cambian lo que hay en
  la columna, no cómo se busca.
