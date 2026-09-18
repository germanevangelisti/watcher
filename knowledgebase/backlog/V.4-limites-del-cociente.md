# V.4 Límites del cociente

**Épica:** V — Verificación / ground truth (capa B: ledger vs Ley)
**Puntos:** 8 (tomar por slices)
**Estado:** en curso — V.4.1 ✅ · V.4.2 ✅ · V.4.3 ⬜
**Rama:** `feature/V.4-limites-del-cociente` desde `main` (`4a28e2e`)
**Depende de:** V.3 hecho (V.3 hizo honesto cada lado del cociente; V.4 hace honesto el cociente)
**Handoff:** [next-session.md](../current/next-session.md)

---

## Objetivo

V.3 arregló **cada lado** de la división: el numerador dejó de contar dos veces y el
denominador dejó de ser un match viejo. V.4 arregla **la división**: hoy el % que
ve el ciudadano no es comparable consigo mismo.

El gasto medido cubre **3 meses**; el presupuesto vigente contra el que se divide
es **la Ley anual entera**. Por construcción el % subestima ~4×. No es un error de
datos — es un error de comparación, y es más grande que el doble conteo que V.3
eliminó.

Tres límites del cociente que hoy no se declaran en ninguna parte:

1. **Período.** `feb–abr` (3 de 12 meses) dividido por la Ley anual.
2. **Días del período.** 60 en total: 58 con publicación y 2 feriados en que el
   boletín no salió (justificados). **Ninguno sin explicación** — se declara como
   afirmación verificable, no como un hueco.
3. **Denominador sin dueño.** **74 filas / $706,6B** cuyo organismo el parser
   perdió, y que el matcher por eso rechaza.

## Por qué es producto

El objetivo es *medir gasto público provincial vs presupuesto*. Un cociente entre
dos períodos distintos no mide: subestima. Y un techo que incluye $706,6B de
presupuesto sin dueño no es un techo verificado.

Es la misma regla que V.3 aplicó al numerador: **declarar el límite, no taparlo ni
inventar el número que falta.** En particular, V.4 **no** prorratea la Ley a 3/12
para "arreglar" el %: la ejecución presupuestaria no es uniforme en el año, así que
prorratear sería inventar un denominador — exactamente lo que V.3 se negó a hacer
con el gasto sin match.

## Hallazgos del corte 2026-09-18 (medidos, no inferidos)

Base: `watcher-backend/sqlite.db`, `presupuesto_base` ejercicio 2026.

| Hecho | Número |
|---|---|
| Cobertura de boletines | **2026-02-02 → 2026-04-30** · 296 filas · 60 días |
| Meses del año sin boletines | **202605 … 202609** (5 meses) |
| Días del período | **60** · 58 con publicación + 2 feriados justificados (Carnaval) · **0 faltantes** |
| Denominador | 480 filas · **$7,532T** (anual, Ley 11.088) |
| Gasto con denominador | $397,72B → **5,28%** del anual |
| El mismo gasto contra 3/12 | $1.883B → **21,1%** |
| Filas con organismo trunco | **74 · $706,6B · 9,4%** del denominador |
| … de esas, con contraparte completa | **0** |
| Filas con texto en `partida_presupuestaria` | 15 · $0,352T |

### H1 — El % divide 3 meses por 12

`get_ejecucion_resumen` filtra el numerador por fecha y el denominador **sólo por
`ejercicio`**:

```python
# denominador — ignora el período del numerador
.where(PresupuestoBase.ejercicio == ejercicio)
```

Así, `pct_compromiso` compara lo publicado en feb–abr contra el crédito vigente de
todo 2026. El número no es falso: es **incomparable**, y nada en la pantalla lo
dice. La diferencia es de ~4×, o sea del mismo orden que el total que el panel
muestra.

### H2 — CORREGIDO: dentro del período no falta ningún día

> **Corrección (2026-09-18, al leer el `error_message` en vez de contar los
> `failed`).** Escribí que 2026-02-16 y 2026-02-17 eran dos días perdidos. **Es
> falso.** Los 10 boletines de esas fechas dicen
> `'justified: Carnaval 2026, HTTP 404 (no salió...)'`: **el boletín no se
> publicó** y el pipeline lo registró como justificado. No hay hueco.

Medido: 20 días por mes × 3 meses = **60 días**; **58 con publicación** y **2
feriados justificados** (Carnaval). **0 días fallidos sin justificar** en todo el
corpus (`failed sin 'justified:'` → 0).

O sea que el único límite del numerador es el **período**, no su interior. Eso es
una afirmación verificable y positiva, y V.4.1 la declara como tal. La regla de
`'justified:'` también deja un gate: si algún día falla sin justificar, la pantalla
lo tiene que mostrar en rojo en vez de contarlo como gasto cero.

Segundo error de método de esta épica, y del mismo tipo que el H4 de V.3: conté
estados (`failed`) y concluí un hecho sobre el mundo (días perdidos) sin leer el
dato que lo explicaba. El `error_message` estaba ahí.

### H3 — El 9,4% del techo no tiene dueño

74 filas de `presupuesto_base` tienen el organismo truncado por el parser
(`MINISTERIO DE` $98,8B; otro `MINISTERIO DE` $80,4B; `DIRECCIÓN GENERAL DE`
$52,9B; `SECRETARÍA DE` $52,9B…).

**No son filas basura a borrar: 0 de 74 tienen una contraparte completa en la
tabla.** Son $706,6B de presupuesto real cuyo organismo se perdió en el parseo.
`match_organismo` las rechaza (`is_truncated_organismo`), lo cual es correcto —
pero el efecto neto es que el denominador **incluye presupuesto que nunca podrá
usarse como techo**, y que parte del "gasto sin denominador" de V.3 ($104,13B)
podría tener techo entre estas filas y no lo sabemos.

Mi primera lectura fue "basura del parser, limpiar". La medición la refutó: hay que
**recuperar los nombres**, no borrar las filas.

**Resuelto en V.4.2** (read-only). Dos decisiones, y las dos importan:

1. **No se restan del denominador.** Restarlos movería *todos* los % a la vez y en
   silencio, que es exactamente lo que esta épica existe para impedir. El % sigue
   dividiendo por la Ley completa; lo que se declara al lado es que el techo
   verificado es $6,825T y no $7,532T.
2. **Se cuentan filas, no grupos.** La query del denominador agrupaba por organismo
   (`group_by`), así que la misma pregunta "¿cuántas filas no tienen dueño?" daba
   14 en vez de 74 — contaba *nombres truncados distintos*. El endpoint ahora trae
   las filas crudas (480) y las agrupa después, lo que da el mismo total en pesos y
   el recuento verdadero en filas. Un número que la pantalla afirma tiene que poder
   contarse; agrupar antes de contar lo convierte en otra cosa.

Resultado en pantalla: "Techo de la Ley" — $7,53T, barra partida al 9,38%, los 12
stubs con su monto (MINISTERIO DE 27 · $291,2B; SECRETARÍA DE 22 · $207,3B;
DIRECCIÓN GENERAL DE 5 · $56,6B…) y la frase que dice qué falta: recuperar esos
nombres es trabajo sobre el parseo de los Mapas, no sobre el contraste.

### H4 — El stub que sostiene la última alerta

La alerta de 145,25% que V.3 dejó viva se apoya en `MINISTERIO DE ECONOMÍA
MINISTERIO Y GESTIÓN PÚBLICA` — nombre del que también está truncado el programa
(`'16 - APORTES AGENCIA PARA LA'`, cortado a mitad de frase). Son **5 filas**
(ids 367/43/44/36/35, $10,5+7,2+2,7+2,0+1,4 = **$23,72B**).

El numerador que la dispara es el acto de $34,026B cuya **extracción** V.3 marcó
como sospechosa (H4 de V.3: leche en polvo y logística a $34B, plausible; la misma
cifra para una plataforma de trabajo en altura, absurda). O sea: **la alerta puede
estar bien y el monto mal**. V.4 no la silencia; decide si el organismo es real.

## Criterio de aceptación (epígrafe)

- [x] **La pantalla declara el período del numerador.** Se ve "3 de 12 meses" y
      "feb–abr 2026" junto al %, y queda explícito que el % es **contra la Ley
      anual** y que por eso subestima. No se prorratea la Ley.
- [x] **Se declara el calendario del período.** 58 días con publicación + 2
      feriados justificados (Carnaval, el boletín no salió) = 60, **0 faltantes**.
      Si algún día fallara sin justificar, la pantalla lo muestra en rojo.
- [x] **Se declara el denominador sin dueño.** $706,6B / 74 programas reportados
      como "presupuesto sin organismo identificado", separados del techo
      verificable ($6,825T). El % no cambia por declararlos; cambia lo que el
      ciudadano sabe. Verificado contra el endpoint: 74 · $706.582,9M · 9,38%.
- [ ] **Los nombres perdidos se intentan recuperar desde la fuente** (Mapas /
      `parse_pdf_presupuesto_2026.py`). Si el parseo no los puede recuperar, queda
      documentado por qué y el criterio anterior sigue en pie.
- [ ] **La última alerta se resuelve o se explica.** Si
      `MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA` es un organismo real,
      se corrige el nombre; si es artefacto, se documenta. **No se silencia.**
- [ ] `make test` / lint sin errores nuevos (A/B con `git stash`, como V.3).
- [ ] `knowledgebase/current/` actualizado. No se commitea `sqlite.db`.

## Slices (orden)

| Slice | Pts | Entrega | Estado |
|---|---|---|---|
| **V.4.1** Declarar el período y el calendario | 3 | Cobertura temporal en el endpoint + la pantalla: meses cubiertos, meses vencidos sin ingerir, días del período y el % rotulado como "contra la Ley anual". Read-only. | ✅ |
| **V.4.2** Declarar el denominador sin dueño | 3 | $706,6B / 74 programas separados del techo verificable ($6,825T), en el endpoint y la pantalla. Read-only. | ✅ |
| **V.4.3** Recuperar los nombres perdidos | 2 | Reparar el parseo de Mapas; si no se puede, documentar la causa y el techo queda declarado | ⬜ |

Empezar por **V.4.1**: es read-only, no toca la DB, y es el que cambia lo que
significa el número que ya está en pantalla. V.4.3 es el único que escribe.

## Fuera de alcance

- **Prorratear la Ley a 3/12.** Inventaría un denominador (la ejecución no es
  uniforme en el año).
- **Ingesta mayo–septiembre.** Es la etapa siguiente y ya está identificada; V.4
  hace que el producto *declare* que le faltan 5 meses, no que los tenga.
- Recall de extracción (44,4%) y montos mal atribuidos (H4 de V.3): son del
  numerador y tienen su propia historia.
- DT-7 (residual de lint, 642) y los 15 tests pre-existentes (DT-2/DT-3).
- Tercera barra "pagado CGE".

## DoR de esta sesión

- [x] Historia en `knowledgebase/backlog/` con criterio de aceptación
- [x] Diagnóstico medido, no supuesto (queries sobre `sqlite.db`)
- [x] Criterio testeable
- [x] Working tree limpio
- [x] `main` actualizada (V.3 mergeada en `4a28e2e`)

## Riesgo principal

V.4.3 es el único slice que escribe, y `presupuesto_base` es el **techo de todos los
%**. Un reparo que agregue o cambie filas mueve todos los denominadores. Backup de
`sqlite.db` antes, y el diff de `presupuesto_base` revisado fila por fila antes de
commitear. Si el reparo no es confiable, se queda en V.4.2 (declarar) — que es
valioso por sí solo.
