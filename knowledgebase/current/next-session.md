# Próxima sesión — Watcher Agent

> **Actualización 2026-10-12 — el MVP se reencuadró: la próxima sesión NO es V.7/V.8.**
> Germán re-priorizó la salida: *"la nueva prioridad del MVP es leer boletines en búsqueda de gasto
> público nivel provincial y municipal y desde allí el usuario decidirá si analizar en profundidad"*.
> Los Must **M1–M7 + MB** quedan como **línea base alcanzada**; la salida vigente son **M8–M10**
> (`knowledgebase/vision/mvp.md`, commit `1c2453e`) y la épica `epic:precio-mercado` del vault.
> **Todas las notas de abajo que dicen que el trabajo siguiente es V.7/V.8 quedan superadas por
> esto**: V.7/V.8 sigue siendo la causa de fondo de los peores errores de monto y obliga a
> **re-extraer**, pero está **depriorizado**, no borrado.
>
> **Trabajo de la próxima sesión — Fase 1 (P0):**
> 1. **Desbloquear la pila de ramas.** `feat/precio-mercado` (PR #5, draft) tiene **base
>    `feat/chat-insights-pack-2`**, rama que **no está mergeada a `main` ni tiene PR abierto**. Las
>    7 historias del pack de chat esperan gate manual: correrlo → mergear → **recién ahí** retargetear
>    PR #5 a `main`. Hoy **nada** de las dos ramas llega a `main`.
> 2. **`pm-gasto-deteccion-ampliada` (M8)** — clasificar **todo** acto con monto por `tipo_gasto`
>    (licitación, compra directa, contratación, concurso, adjudicación, obra, servicio,
>    subsidio/transferencia, `otro` con motivo), con organismo y nivel; precisión medida ≥ 90% nivel
>    / ≥ 80% tipo sobre ≥ 100 actos etiquetados. Hoy hay **83 observables de 1.220**: ése es el techo
>    que la historia levanta.
> 3. **`pm-municipal-cobertura` (M9, depende de la anterior)** — `nivel` provincial/municipal/comunal
>    + conector del **Boletín Municipal de Córdoba capital** (hoy **0 actos** de la capital; los 228
>    actos municipales entran sólo como edictos de municipios del interior) + banner de cobertura.
> 4. **Decisiones del gate** antes de codear lo que las necesita: Córdoba capital como 1er municipio
>    y corte temporal; **costo de re-extracción** si la clasificación no alcanza con el fragmento de
>    ~290 caracteres; OCR local vs externo; ML como referencia secundaria o apagado.
>
> **Ya hecho en la rama, no rehacer:** detección heurística de observables, pantalla
> `/analisis/precio-mercado`, análisis por ítem y **por renglón** con agregado, cantidades desde el
> texto y desde ComprasCba (grilla o pliego), referencias (corpus + precios oficiales de ComprasCba +
> Mercado Libre con fallback a catálogo). Cobertura medida: 16 con cantidad, 16 analizables, 4 con
> ≥ 3 refs ML; 5 `dentro_de_rango`, 78 `sin datos suficientes`. **Las 4 historias originales siguen
> en `todo` por decisión de Germán**, así que el kanban no refleja lo hecho.
> **`.env` ya dice `LLM_PROVIDER=ollama`** (verificado 2026-10-12): el pendiente urgente de abajo
> quedó cerrado.
>
> **Actualización 2026-10-12 (segunda) — M8 hecho, y lo que queda es tuyo.**
> `pm-gasto-deteccion-ampliada` pasó a `testing`: el gasto público se detecta y se lista (ver
> [status.md](status.md) y la nota de la historia). Medido: **4.639 actos con monto clasificados
> (100 %)**, listado de **1.265 actos · $1.781,46 B**, 449 obras+servicios, y la suma descuenta
> republicaciones. Backfill aplicado con backup `sqlite.db.bak-m8-20261012`.
>
> **La próxima sesión arranca por acá:**
> 1. **Etiquetar la muestra ciega** — `watcher-backend/.tmp-muestra-gasto/gasto_muestra_etiquetado.md`
>    (150 actos, `nivel_real` y `tipo_gasto_real`; **la predicción no está en ese archivo**, va en un
>    JSON aparte que no hay que abrir). Después: `.\.venv\Scripts\python.exe
>    scripts/medir_clasificacion_gasto.py` → precisión por eje con cota de Wilson al 95 %. El criterio
>    es ≥ 90 % nivel / ≥ 80 % tipo; si no llega, **la muestra dice dónde falla** (desagregado por
>    fragmento corto y por municipal).
> 2. **Prueba manual del listado** (`/analisis/precio-mercado`): filtros, total y suma, y *Analizar en
>    profundidad* en un acto del ledger. El botón está deshabilitado con motivo para los 45 actos que
>    no están en el ledger.
> 3. **Después: `pm-municipal-cobertura` (M9)** — el `nivel` ya está etiquetado en el corpus
>    (municipal 350 / comunal 96 en el universo; 272 en el listado) y `municipio` sale del organismo
>    (364 actos). Falta el conector del Boletín Municipal de Córdoba capital (**0 actos** hoy) y el
>    banner de cobertura. Requiere tu decisión de corte temporal.
> 4. **Decisión pendiente**: el ledger existente no tiene `tipo_gasto`/`nivel` en sus 1.220 filas —
>    los llena un rebuild del ETL, que toca los contadores y los números del contraste vs la Ley. El
>    listado no lo necesita; se dejó sin correr a propósito.

> **Actualización 2026-10-01 (cuarta):** **el chat ahora deja elegir el proveedor y declara con
> cuál se redactó** (tarjeta en el tab *Chat con Insights*), para poder comparar la calidad de las
> respuestas. Ver [status.md](status.md) y la historia `story-watcher-chat-llm-selector` (en
> `testing`). **Tres cosas para el arranque, y la primera es urgente:**
>
> 1. **`LLM_PROVIDER=ollama` en `.env` — una línea, y es del PO.** Instalar los SDKs (que el PO
>    eligió para poder comparar Gemini contra local) dejó `LLM_PROVIDER=google` **vivo**:
>    `google-generativeai` ya está en `.venv`, así que `configured.fallback` pasó de `true` a
>    **`false`** y **el contexto de los boletines sale de la máquina por defecto**. No se tocó el
>    `.env` (tiene una key viva). La tarjeta del panel muestra el origen del default y avisa; el
>    arreglo es esa línea. **El SDK además está deprecado** (`google.generativeai` → `google.genai`):
>    historia aparte.
> 2. **El gate manual del chat suma la comparación.** En la tarjeta: elegir **Ollama** → preguntar
>    *"¿qué organismos concentran mayor gasto?"* → la burbuja tiene que decir **"Redactado con
>    Ollama · qwen2.5:7b"** debajo de las fuentes; cambiar el modelo a **`qwen2.5:14b`** y volver a
>    preguntar → la firma cambia y la respuesta es más detallada. Escribir **"gracias"** → la
>    burbuja dice *"Sin modelo: respuesta del sistema"*, sin fuentes. Claude tiene que aparecer
>    **deshabilitado** con su motivo (`falta ANTHROPIC_API_KEY`), y la elección tiene que
>    sobrevivir a un refresh.
> 3. **La mitad semántica de la búsqueda volvió a andar sola, y el baseline bajó.** El `.pyd` de
>    scikit-learn que Smart App Control bloqueaba **hoy importa** (cambió la reputación del
>    archivo, no la política: `VerifiedAndReputablePolicyState` sigue en `1`), `hybrid_search`
>    devuelve **10 resultados** donde daba 5 y `unit/test_embedding_service.py` está 18/18 en
>    verde. **Baseline nuevo: 5 failed / 1010 passed / 7 skipped** (ver el bloque de comandos,
>    abajo está corregido). El informe WDAC de abajo **no se contradice**: describe por qué estaba
>    bloqueado y qué hacer si vuelve a romperse, y sigue vigente. El rótulo del chip
>    (*"Boletines oficiales"*) **no se revierte**: es lo correcto con o sin la mitad semántica.
>
> Nada de esto toca el corpus: **el trabajo siguiente sigue siendo V.7 y V.8**, que sí obligan a
> re-extraer.

> **Actualización 2026-10-01 (tercera):** **un turno sin pedido corría todo el pipeline** y **el chip
> de fuentes mentía**. Un *"gracias"* después de un desglose **volvió a contestar la pregunta
> anterior** (`search_bm25("gracias")` devuelve 3 boletines, así que el bloque de ausencia no se
> emitía y el historial le devolvía la pregunta vieja al modelo), y la fuente del corpus se rotulaba
> *"Búsqueda semántica"* cuando en esta máquina la mitad semántica está apagada. Arreglado — ver
> [status.md](status.md) y la historia `story-watcher-chat-fuentes-y-turno-cortesia` (en `testing`).
> **Dos cosas para el arranque:**
>
> 1. **El gate manual del chat suma dos pasos.** Además de
>    *"¿qué se publicó sobre obra pública en septiembre?"*: (a) después de una respuesta con datos,
>    escribir **"gracias"** → tiene que contestar corto, **sin fuentes** y **sin** repetir la
>    pregunta anterior; (b) mirar el chip del corpus → dice **"Boletines oficiales"**, no "Búsqueda
>    semántica". Y *"gracias, ¿y en octubre?"* tiene que **consultar** (el corte no se come pedidos).
> 2. **El vocabulario de cortesía es una lista cerrada**, en una constante de `agent.py`. *"muchas
>    gracias por la info"* no entra y sigue el camino normal. Si el PO escribe una fórmula nueva, se
>    agrega la palabra; no hay detector semántico a propósito.
>
> **Corrección:** este bloque dice que la mitad semántica "está apagada", y el de abajo
> (segunda) la da por inalcanzable — **hoy corre** (ver la actualización cuarta, punto 3). El
> **arreglo** del chip no se revierte: el rótulo *"Búsqueda semántica"* era falso en cualquier
> configuración, porque `hybrid_search` siempre fue keyword + semántica, no semántica sola. El
> resto de estos bloques sigue valiendo.

> **Actualización 2026-10-01 (segunda):** el chat **afirmaba ausencias que no había verificado**
> (*"No se publicó información sobre obra pública en septiembre"*, siendo falso). Arreglado —
> ver [status.md](status.md) y la historia `story-watcher-chat-corpus-search` (en `testing`).
> Tres cosas para el arranque:
>
> 1. **El gate manual del chat cambia de pregunta.** La que hay que hacer es
>    *"¿qué se publicó sobre obra pública en septiembre?"*: tiene que traer los boletines de
>    septiembre (`20260903_5_Secc` y compañía) **o**, si la búsqueda no corre, decir *"no lo
>    encontré / no lo busqué"* — nunca *"no se publicó"*.
> 2. **El corpus sigue sin alcanzarse en esta máquina, y ahora se ve por qué.** Es **Smart App
>    Control** (`VerifiedAndReputablePolicyState = 1`) bloqueando el `.pyd` sin firmar de
>    scikit-learn: sin función de embedding local, los **983 chunks** de
>    `watcher_documents_local` quedan inalcanzables y la mitad semántica no busca. **Destrabarlo
>    es acción de admin del PO** (Seguridad de Windows → Control de aplicaciones y navegador →
>    Smart App Control → Desactivado + reiniciar) y **es irreversible**. Con el bloqueo puesto,
>    el log ahora lo **grita** en vez de devolver `0 results` en silencio. Detalle en la historia.
> 3. **`.env` dice `LLM_PROVIDER=google` con una `GOOGLE_API_KEY` puesta y el SDK sin
>    instalar.** Hoy no pasa nada (el chat cae a Ollama por el fallback), pero **un `uv sync`
>    instala `google-generativeai` y el contexto del boletín empieza a salir de la máquina sin
>    cambiar ninguna línea**. Para fijar local: `LLM_PROVIDER=ollama`.
>
> Sigue sin tocarse el corpus: **el trabajo siguiente sigue siendo V.7 y V.8**, que sí obligan a
> re-extraer.

> **Actualización 2026-10-01:** el chat de `/analisis/agentes` **ya redacta** con el modelo
> local (`OllamaProvider` + `resolve_llm_provider()`; ver [status.md](status.md)). Nada de
> esto toca el corpus: **el trabajo siguiente sigue siendo V.7 y V.8**, que sí obligan a
> re-extraer. Dos cosas para el arranque:
>
> 1. **`.env` dice `LLM_PROVIDER=google` con una `GOOGLE_API_KEY` puesta y el SDK sin
>    instalar.** Hoy no pasa nada (el chat cae a Ollama por el fallback), pero **un `uv sync`
>    instala `google-generativeai` y el contexto del boletín empieza a salir de la máquina sin
>    cambiar ninguna línea**. Para fijar local: `LLM_PROVIDER=ollama`.
> 2. **La prueba manual del chat hay que rehacerla con el server reiniciado**, y ahora incluye
>    la mitad semántica (los chips pueden traer `corpus_boletines` — *"Boletines oficiales"*) más
>    la prosa real.

> **Actualización 2026-09-30:** la épica **`chat-insights-presupuesto` quedó sin `To do`**
> (sus 4 historias pasaron a `testing`; ver [status.md](status.md)). Nada de eso toca el
> corpus: **el trabajo siguiente sigue siendo V.7 y V.8**, que sí obligan a re-extraer.
> Lo único pendiente en el tablero es ops (`fix deploy SSH`), que es tarea de Germán.

> **Actualización 2026-09-28 (post Ampliación B / M6):** este handoff es del **2026-09-19 (V.5)**.
> Después pasó **MB completo** (API 2026-09-25 + UI y proxy BO 2026-09-28) y el **checklist M6 (1–10)** se
> ejecutó el **2026-09-28 con OK de Germán**. **El Must quedó cerrado:** commit `40c48a6` (19 archivos, 2684 inserciones), sobre **el mismo árbol** que se
> probó en pantalla. Sólo falta el `git push origin main`.
> El estado vivo está en [status.md](status.md) — leer **eso** antes que este archivo.
> La línea de base de tests de más abajo también cambió (ver el bloque de comandos).

**Fecha del handoff:** 2026-09-19
**Trabajo cerrado esta sesión:** **V.5 ingesta mayo–septiembre.** El producto pasó de
medir **3 a 8 meses** (feb–sep). Extracción cerrada (`ok=469 fail=0`, 0 fallos sin
justificar), ledger reconstruido (1220 filas → 972 canónicas → **$1.776,41B**), gate de
drift en **exit 0**, 3 alertas >100% (eran 5, ninguna nueva). **Sin una línea de código
cambiada**: es una operación sobre `sqlite.db`.
**Trabajo siguiente:** **V.7** (la fuga de monto entre columnas del extractor) y **V.8**
(el monto del aviso vecino). Son la causa de fondo de los peores errores de monto del
corpus. Ojo: arreglarlas obliga a **re-extraer** — es una decisión de costo, no un parche.

> **Antes de seguir: leer [status.md](status.md) y
> [V.5-ingesta-mayo-septiembre.md](../backlog/V.5-ingesta-mayo-septiembre.md).**
> `main` ya tiene V.1–V.6 y V.5. Las secciones de más abajo sobre V.2 y el corte abril
> quedan como contexto histórico: **no describen la DB de hoy**.

---

## La etapa siguiente: V.7 y V.8 (requieren re-extracción)

Los dos defectos están **medidos y declarados**, con caso testigo probado a mano
contra el PDF. Los dos viven en la capa de extracción, así que arreglarlos cambia
las filas de `analisis` de **todo el corpus**.

| | V.7 | V.8 |
|---|---|---|
| Qué es | el monto del acto de la columna de al lado | el modelo le pone al acto el monto del aviso vecino, o la tasa BOE, o el número con la coma caída (×100) |
| Caso testigo | dos columnas interleaveadas en la 4ª sección | `20260903_4_Secc.pdf` pág. 4: `$30.000.077.244,29` impreso, `3.000.007.724.429` guardado |
| Daño medido | ver la historia | **$3,0B en una fila**, y una alerta fabricada de 10.850% (ya reparada a mano) |
| Instrumento que sirve | el PDF (geometría) | el **texto que entra al modelo**, en línea (`pipeline.py:1606`) — **no** `analisis.fragmento` |

**Lo que ya está hecho y no hay que rehacer:** el caso catastrófico de V.8 está
reparado **contra el PDF** (5 filas de EPEC + 4 edictos de la 9150), con la evidencia
dentro de la fila (`datos_extra.correccion_2026_09_19*`), y la reparación **se pierde
si el boletín se re-extrae** — eso es esperado y está declarado.

**Lo que NO sirve como instrumento** (tres, los tres falsificados a mano; no
reintentarlos): regex sobre `analisis.fragmento` (3114/3174 fragmentos no traen
ningún `$`, y truncaba números de 5 dígitos), oráculo de pertenencia sobre el PDF
entero (4/4 falsos positivos verificados), y el mismo oráculo sobre
`chunk_records.text` (cae en CUIT, DNI y capitales sociales). El detalle y las
causas están en V.8, criterio de aceptación.

## Lo que V.5 dejó declarado y sin arreglar

- **2026-01 es el único mes vencido sin ingesta.** Es anterior al período que el
  producto declara (feb–sep), y se declara como hueco, no se esconde.
- **123 boletines `completed` sin PDF en disco.** El **texto** de los 123 está en
  `chunk_records` (123/123, 1606 filas, $283,18B), así que la auditoría **por texto**
  sigue siendo corpus-wide; lo que no se puede re-verificar es la **geometría**.
- **Gasto sin denominador: $404,52B / 364 actos.** Creció de $140,72B porque ahora
  se miden 5 meses más. Causas por organismo medidas (entidades que no están en la
  Ley, fuera de alcance por diseño, y el matcher).
- **3 alertas >100%**, todas por granularidad del denominador, todas visibles:
  Infraestructura Hídrica 1561,58% · Desarrollo Sostenible 184,80% · Seguridad 136,01%.
- **Ejecución (pagos) casi vacía** y **recall de extracción 44,4%**: historias propias.

## Corrección a números ya publicados (declarada)

**feb–abr baja de $538,44B a $519,57B canónicos (−$18,87B).** No lo causa la ingesta:
es la dedup de V.6 sobre licitaciones republicadas, que hasta ahora sólo corría al
reconstruir el ledger por lotes. Sobre el corpus final el A/B de V.6 da **−$313,32B**,
de los cuales **$237,29B son un solo acto de EPEC contado dos veces** (licitación 5576).

> **Antes de citar un número, mirar de dónde sale.** En esta sesión tres instrumentos
> distintos dieron el mismo total con el reparto mal, y una cifra que se creía medida
> ($2.966,33B) había salido de una réplica ya descartada. Si un número no tiene su
> medición escrita al lado, no vale.

## Cómo operar (los comandos que funcionan)

```powershell
cd C:\Users\germa\watcher\watcher-backend
uv run python .tmp_ingesta/...            # (el scratch se borra al cerrar V.5)
uv run python scripts/etl_analisis_to_ejecucion.py   # reconstruye el ledger ENTERO
uv run python scripts/check_match_drift.py           # gate: exit 0 = sano
uv run pytest -q                                     # ver nota de línea base abajo
uv run ruff check .                                  # 0 = DT-7 cerrada (2026-09-23)
```

**Línea base de tests (2026-10-01, cuarta — corregida):** `5 failed / 1010 passed / 7 skipped`
corriendo con `--ignore tests/tests/test_indexing_service.py`. Ese archivo **aborta la colección**
en esta máquina (`OSError: [WinError 4551] An Application Control policy has blocked this file` —
la misma política WDAC del bloqueo de sklearn), y sus fallos estaban contados dentro del viejo
"15 failed".

**Bajó de 10 a 5 el mismo día, y no por un arreglo: el `.pyd` de scikit-learn dejó de estar
bloqueado.** `sklearn.metrics._dist_metrics` hoy importa, así que el EF local carga y los 5 tests
de `unit/test_embedding_service.py` que fallaban ahora pasan (18/18). **SAC sigue en enforcing**
(`VerifiedAndReputablePolicyState = 1`): cambió la reputación del archivo (ISG), no la política.

Las **5 que quedan** son todas preexistentes y ninguna toca el chat:
`e2e/test_adversarial_verification.py` ×2 (VCP), `unit/test_pds_scrapers.py::test_provincial_scraper_download_single`
(separador de path) y `unit/test_security_middleware.py` ×2 (sin event loop).

**Los tres comandos no obvios de esta máquina:**
```powershell
.\.venv\Scripts\python.exe -m pytest ...   # `make` y `ruff` no están en el PATH
.\.venv\Scripts\python.exe -m ruff check .  # 0 = limpio
python -c "import sklearn"                  # si esto falla, la mitad semántica del chat no busca
```

`make` **no está disponible** en este entorno: correr los targets a mano.
`make lint` además **pasa en vacío** si `ruff` no está en el PATH.

| Mes | DB | Notas |
|---|---|---|
| 202602–202604 | cerrados | feb–abr, corregidos −$18,87B por V.6 |
| 202605–202609 | **cerrados V.5** | 472 `completed` / 33 `justified:` / 0 en vuelo |
| 202601 | **sin ingesta** | único mes vencido que queda |

## Qué no hacer

- Meter pagado CGE en la misma barra que compromiso/ejecución del BO.
- Tratar el compromiso como ejecución: el 99,86% de la barra "compromiso" es `llamado`
  (licitación publicada), no compromiso asumido.
- **Prorratear la Ley** para acelerar la comparación: es la regla que V.4 dejó escrita.
- Silenciar una alerta >100% sin medir su causa.
- Commitear `sqlite.db`, `*.db-wal`, `uv.lock`, PDFs, Mapas-por-Programas, xlsx CGE.

## Contexto mínimo

| Corte | Archivo |
|---|---|
| V.5 (esta sesión) | [V.5-ingesta-mayo-septiembre.md](../backlog/V.5-ingesta-mayo-septiembre.md) |
| V.7 / V.8 (próximas) | [V.7](../backlog/V.7-monto-del-acto-de-al-lado.md) · [V.8](../backlog/V.8-monto-del-aviso-vecino.md) |
| Ancla Ley | [ancla-ley-11088.md](ancla-ley-11088.md) |
| Handoff UI post V.2 | [corte-abril-ui.md](corte-abril-ui.md) |

Runtime LocalPro: `qwen2.5:7b`, `LLM_MAX_CONCURRENT=1`, `OLLAMA_TIMEOUT_S=480`.
Notion MCP no disponible.
