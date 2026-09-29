# V.9 Canónicas distintas para el mismo organismo

**Épica:** V — Verificación / ground truth (capa de **identidad** de organismos)
**Puntos:** 3
**Estado:** pendiente (hallazgo declarado, no arreglado)
**Rama:** `feat/pack-fix-ui-chat-p0`
**Depende de:** el bugfix de agrupación de organismos (misma superficie, defecto **vecino**)
**Origen:** hallazgo medido en el gate manual del pack fix-ui + chat, 2026-09-29

---

## Objetivo

El bugfix de agrupación unificó los buckets que **compartían canónica**. Pero la
canónica no siempre es una sola: `canonical_organismo_name` devuelve **cadenas
distintas para el mismo organismo** cuando la grafía difiere en puntuación, en una
palabra funcional interna o en el **orden** de los tokens. Como "canónicas distintas"
es la definición misma de "buckets distintos", el agregado sigue mostrando el mismo
organismo **dos o tres veces**, y ninguna de esas filas es el total.

Es un defecto **de la capa de identidad**, no del display: el mapa de display del
bugfix no podía tocarlo por construcción.

## Por qué el bugfix de agrupación no lo cubre

`display_por_canonico()` mapea `canónica → mejor grafía observada`. Si dos grafías
producen **canónicas diferentes**, hay dos entradas en el mapa y dos buckets — da
igual cuántas grafías intermedias se hayan absorbido. El fix cerró el caso "una
canónica, muchas grafías"; este es "una entidad, varias canónicas".

## Los tres casos, medidos

Contra el corpus real (`sqlite.db`, 972 canónicos, proxy BO $1.776.409,53 M), sobre
los **151** buckets del endpoint. La huella usada para detectarlos normaliza acentos,
signos, sufijos societarios y **ordena los tokens**, así que encuentra también el caso
de orden que una huella secuencial no vería.

| Entidad | Buckets | Grafías (canónica entre paréntesis) | Monto real |
|---|---|---|---|
| **APROSS** | 2 | `ADMINISTRACIÓN PROVINCIAL DEL SEGURO DE SALUD -APROSS` (n=2, $2.878,55 M) · `Administración Provincial del Seguro de Salud - APROSS` (n=2, $648,76 M) | **$3.527,31 M / 4 actos** |
| **CEPROCOR** | 2 | `Centro de Excelencia en Productos y Procesos Córdoba (CEPROCOR)` (n=3, $461,35 M) · `CENTRO DE EXCELENCIA EN PRODUCTOS Y PROCESOS DE CÓRDOBA (CEPROCOR)` (n=1, $46,15 M) | **$507,50 M / 4 actos** |
| **UNC — Fac. de Derecho** | 3 | `Universidad Nacional de Córdoba - Facultad de Derecho` (n=4, $3.115,17 M) · `Facultad de Derecho de la Universidad Nacional de Córdoba` (n=1, $0,03 M) · `Facultad de Derecho - Universidad Nacional de Córdoba` (n=1, $0,02 M) | **$3.115,22 M / 6 actos** |

**3 entidades fragmentadas · 4 buckets de más** sobre 151 (`249` grafías crudas en el
ledger → 151 buckets: la dispersión de *grafías* está absorbida; la de *canónicas* no).

## Causa raíz — tres reglas del canonicalizador

Medido llamando `canonical_organismo_name` sobre los pares:

1. **El guion pegado al token.** `…SALUD -APROSS` conserva el guion dentro del token
   (`-APROSS`) y `…SALUD - APROSS` lo separa → dos canónicas. Un espacio decide la
   identidad del organismo.
2. **Palabra funcional interna inconsistente.** `PROCESOS CORDOBA` vs
   `PROCESOS DE CORDOBA`: el `DE` sobrevive en una y no en la otra. (El canonicalizador
   sí descarta funcionales en otras posiciones — `FACULTAD DE DERECHO **DE** UNIVERSIDAD`
   conserva el `DE` interno —, así que la regla no es "se descartan los DE", es
   "se descartan algunos DE".)
3. **Sensibilidad al orden.** `UNIVERSIDAD NACIONAL DE CORDOBA - FACULTAD DE DERECHO`
   ≠ `FACULTAD DE DERECHO DE UNIVERSIDAD NACIONAL DE CORDOBA`. El extractor escribe el
   mismo par de entidades en los dos órdenes y el canonicalizador no los ordena.

## Impacto

- **$2.924,75 M** (la suma de los hermanos menores) viven bajo una etiqueta duplicada:
  **0,16% del proxy BO**. No mueve ningún total —el dinero está, mal atribuido.
- **El error por fila es grande aunque el agregado no lo note**: la fila principal de
  APROSS muestra $2.878,55 M cuando la entidad publicó **$3.527,31 M**. Ninguna de las
  dos filas de APROSS es el total, así que **el lector no puede reconstruirlo** sumando
  a ojo lo que ve.
- Afecta a **todo % por organismo** de los fragmentados (denominador contra numerador
  partido).

## Lo que NO se debe hacer

- **No partir por ` - `.** Hay nombres **legítimos** con guion, y un `split` ingenuo los
  rompe: `Dirección de Inteligencia Fiscal - Área Determinaciones` ($8.657,49 M),
  `Universidad Nacional de Córdoba - Facultad de Derecho` ($3.115,17 M),
  `Universidad Nacional de Córdoba - Secretaría de Planeamiento` ($349,07 M),
  `Subsecretaría de Infraestructura Urbana, dependiente del Ministerio de
  Infraestructura y Servicios Públicos` ($558,41 M).
- **No ordenar los tokens a ciegas.** Ordenar unifica el caso UNC, pero también puede
  hacer colisionar nombres que hoy son distintos; hay que medirlo antes.
- **No tocar el canonicalizador sin re-verificar.** Cambiar la canónica **re-identifica
  buckets en todo el corpus**: se mueven el conteo de 151, el `%` de cada organismo y la
  comparación EPEC del agregado (276) contra el desglose del chat (278). Es una
  **re-verificación**, no un parche.

## Criterio de aceptación (cuando se aborde)

- [ ] **Medir antes de elegir la regla.** Cuantificar, sobre el corpus completo, cuántos
      buckets se fusionarían con cada variante (guion/espacios, funcionales internas,
      orden de tokens) y **listar cada fusión propuesta** para inspección una por una.
- [ ] **La regla elige conservador, no agresivo**: se aceptan las tres causas de arriba
      y ninguna otra. La huella de V.6/P.3 (alias) es el precedente de un arreglo
      quirúrgico cuando la regla general asusta.
- [ ] **Totales bit a bit idénticos** antes/después ($1.776.409,53 M / 972 actos), igual
      que el bugfix de agrupación.
- [ ] **Test de no-sobre-fusión** con el mismo método del bugfix: huella ortográfica
      compartida por cada par fusionado y **0** destinos que mezclen dos huellas.
- [ ] **Los nombres legítimos con guion de arriba quedan intactos**, con test que lo fije.
- [ ] **Los 3 pares de este ticket colapsan a 1 bucket cada uno**: APROSS $3.527,31 M,
      CEPROCOR $507,50 M, UNC Fac. de Derecho $3.115,22 M.
- [ ] **Declarar el efecto en las otras superficies**: el agregado del chat, el
      desglose por organismo y el buscador de ejecución (ver **V.10**) cambian de
      número; hay que re-correr la verificación de cada uno, no sólo la del endpoint.

## Fuera de alcance

- **Nombres encadenados** (`ACIF … - Secretaría de Infraestructura Hídrica …`): es del
  **extractor**, no del canonicalizador. Documentado como síntoma de **V.7**.
- **Garbling del extractor** (`Empresaria` por `Empresa`, `Ea Provincia`, `EPECO`):
  canónicas distintas **de verdad**; es V.7/V.8.
- **V.6** (dedup de republicaciones): comparte el síntoma "misma plata en dos filas".
  Cualquier medición acá tiene que descontar V.6 primero, igual que V.7.
- **El fallback `raw` de `remap_organismo_key`**: el bugfix lo dejó inocuo; con el mapa
  completo ya casi no se alcanza, pero sigue ahí.
