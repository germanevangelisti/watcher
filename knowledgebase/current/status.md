# Estado Actual — Watcher Agent

**Última actualización:** 2026-10-12
**Snapshot del momento.** Se pisa al avanzar. La historia completa está en `docs/changelog.md` y el historial de git.

> **MVP re-priorizado: el producto ahora busca gasto público, no lo contrasta** (2026-10-12).
> Germán reencuadró la salida: *"la nueva prioridad del MVP es leer boletines en búsqueda de gasto
> público nivel provincial y municipal y desde allí el usuario decidirá si analizar en profundidad"*.
> Los Must **M1–M7 + MB** (contraste fiscal vs Ley 11.088) quedan como **línea base alcanzada**, sin
> cambios; los Must **M8–M10** definen la salida vigente (`knowledgebase/vision/mvp.md`, commit
> `1c2453e`). Plan, historias y gate: épica `epic:precio-mercado` en el vault
> (`board/epics/epic-watcher-precio-mercado.md`).
>
> **Estado de las ramas: la pila no llega a `main`.** `feat/precio-mercado` (12 commits, +3103) tiene
> el PR **#5 en draft, con base `feat/chat-insights-pack-2`** (2 commits, +6416) — rama que
> **tampoco está mergeada a `main` y no tiene PR abierto**. Las **7 historias del pack de chat**
> siguen en `testing` esperando el gate manual: ése es el eslabón que traba la cadena entera.
> Retargetear PR #5 a `main` recién después de mergear el chat.
>
> **Lo que ya está implementado y pusheado** en la rama (no está en el kanban: las 4 historias
> originales siguen en `todo` por decisión de Germán, así que **las 13 notas del épico están en
> `todo` con 0 criterios tildados** aunque parte esté hecha): detección heurística de **83
> observables sobre 1.220 actos**, pantalla `/analisis/precio-mercado`, análisis por ítem y **por
> renglón** con agregado, cantidades desde el texto y desde ComprasCba (grilla o pliego), y
> referencias (corpus, precios oficiales de ComprasCba, Mercado Libre con fallback a catálogo —
> `/sites/MLA/search` da 403 con ambos tokens). Cobertura medida: 16 con cantidad, 16 analizables,
> 4 con ≥ 3 refs ML; 5 `dentro_de_rango`, 78 `sin datos suficientes`.
>
> **Brecha medida que define la Fase 1 (P0):** el corpus son **803 boletines, 100% BO provincial**;
> lo municipal entra sólo como **edictos de municipios/comunas del interior** (228 de 1.220 actos,
> 77 organismos) y **Municipalidad de Córdoba (capital): 0 actos** — su Boletín Electrónico
> Municipal no se ingiere.
>
> **Higiene de esta sesión:** los 11 artefactos scratch del worktree (`.pm-shots/*.png`, scripts de
> screenshot, `.tmp-dashboard.png`) quedaron fuera de `git status` con una regla de `.gitignore`
> (no se borraron: son evidencia de gates). `CLAUDE.md` dejó de apuntar a V.7/V.8 como próxima
> sesión. **Sin commit ni push: los corre Germán.**
>
> **`.env` ya dice `LLM_PROVIDER=ollama`** (verificado 2026-10-12): el pendiente "urgente" de los
> bloques de abajo quedó cerrado. El SDK de Google sigue instalado, pero dejó de ser el default.
>
> **M8 hecho: el gasto público se detecta y se lista** (2026-10-12, historia
> `pm-gasto-deteccion-ampliada` en `testing`). El punto de extensión fue el clasificador que **ya
> existía** (`app/services/gasto_classifier.py`, rules-only, ya persistido por P.7), no la heurística
> de precio-mercado: ganó `tipo_gasto` (figura/objeto) y `nivel` (nivel de gobierno) como ejes
> **independientes** de `etapa_gasto` (el momento) y `jurisdiccion_gasto` (de quién es el
> presupuesto). Precedencia: instrumento > objeto > procedimiento.
>
> **Medido sobre `sqlite.db`**: **4.639 actos con monto clasificados (100 %)** — sin `tipo_gasto` ni
> `nivel` en NULL, y `otro`/`no_es_gasto` siempre con motivo. El listado por defecto son **1.265
> actos · $1.781,46 B**, con **$1.033,00 B de republicaciones excluidas de la suma** (se listan
> marcadas: sin ese descuento se contaba dos veces la Licitación 5576 de EPEC, $237,29 B, lo que V.6
> arregló en el ledger). **449 obras + servicios** donde la heurística vieja veía 83 bienes, 272 actos
> municipales/comunales, y **0 `desconocido`** en el listado (los 3.374 `no_es_gasto` quedan fuera por
> defecto, con su nivel y su motivo).
>
> **Un hallazgo cambió el diseño**: con el gate de P.7 solo, `obra`/`servicio`/`compra directa` sin
> keyword de etapa caían en `no_es_gasto`. Se separaron **figura** y **pertenencia al ledger**:
> "Contrátase el servicio de limpieza" **se lista** y **no entra al ledger** (sin evidencia de etapa);
> la fila declara las dos cosas. El ledger no se tocó: sus 1.220 filas conservan sus totales.
>
> **Backfill aplicado con backup `sqlite.db.bak-m8-20261012`** (script con dry-run por defecto; el
> dry-run se verificó antes sobre una copia). Endpoint `GET /gasto/detectado` (filtros y paginado en
> SQL, contra las columnas persistidas) y pantalla `/analisis/precio-mercado` con filtros, total, suma
> y *Analizar en profundidad* por fila — deshabilitado **con el motivo a la vista** para los 45 actos
> que no están en el ledger, porque el análisis de precio todavía lee el ledger.
>
> DoD: backend **5 failed / 1119 passed / 7 skipped** (las 5 rojas son preexistentes, cero nuevas;
> +106 tests del listado + 3 del middleware) · frontend **128/128** · `ruff`, `tsc -b` y `eslint`
> limpios. **Falta**: las etiquetas de la muestra ciega (150 actos en
> `watcher-backend/.tmp-muestra-gasto/`, criterio de precisión pendiente) y la prueba manual de
> Germán. Sin commit ni push: los corre Germán.
>
> **Bug del producto que apareció al abrir la pantalla (mismo día, arreglado).** El listado decía *"No
> se pudo cargar la lista"* **con el endpoint devolviendo 200**. No era la historia: el
> `CUITMaskingMiddleware` (`app/middleware/masking.py`) corría el regex de CUIT sobre el **texto JSON
> serializado**, así que **cualquier número con 11 dígitos enteros** — un monto en pesos normal —
> matcheaba y se reemplazaba por la máscara `**-********-*` **sin comillas**: JSON inválido para
> cualquier cliente, y el `transformResponse` del frontend tirando *"Respuesta JSON inválida del API"*.
> El listado fue la primera víctima porque devuelve montos en pesos (APROSS $21,6B, ACIF $9.571B).
> **Arreglado**: el middleware parsea el cuerpo y enmascara la estructura (`mask_value`, sólo strings),
> así que el CUIT de `beneficiario` se sigue enmascarando y el payload queda parseable. **Tres tests
> nuevos cubren el camino que faltaba** — los existentes sólo probaban las funciones puras, que es
> exactamente por qué llegó hasta producción. Verificado por HTTP real: 0 asteriscos, JSON estricto
> válido. **Límite declarado (decisión de PO)**: sigue enmascarando cualquier secuencia de 11 dígitos
> *dentro de un string* (p. ej. un número de expediente).
>
> **Y el listado mostró su propio defecto al verse**: la columna «Concepto» pintaba el *motivo* de la
> clasificación (`keyword obra`) en vez del acto, porque el endpoint no devolvía la descripción. Ahora
> devuelve `concepto` (`descripcion`, o el fragmento) con el motivo como línea secundaria, y `q` busca
> también en `fragmento`.
>
> **Tercer eje `objeto`, y seis arreglos del clasificador (2026-10-12, después del primer etiquetado a
> mano del PO).** El PO etiquetó 13 actos y `tipo_gasto` dio **4/13**: **4 de las 9 fallas eran una
> convención sin cerrar** — actos que nombran las dos cosas (*"Licitación para la **obra** de
> drenaje"*), etiquetados por el procedimiento donde las reglas daban el objeto. **Decisión del PO:
> separar los ejes.** `tipo_gasto` = la figura/procedimiento (`licitacion`, `concurso_precios`,
> **`subasta_electronica`**, `compra_directa`, `contratacion`, `subsidio_transferencia`, `otro`,
> `no_es_gasto`) y **`objeto`** = qué se compra (`obra`, `bien`, `servicio`, `transferencia`, `otro`,
> `no_aplica`), columna nueva en `Analisis` y en el ledger, con filtro en la API y en la pantalla. Un
> acto se lee *«Licitación · Obra»*.
>
> **El mismo etiquetado pasó de 4/13 a 9/13**, y las 4 fallas que quedan ya no son del clasificador
> sino desacuerdos de taxonomía con nombre (dos actos que dicen literalmente *SUBASTA ELECTRÓNICA*; un
> reintegro de impuesto; un incentivo educativo). **Cada decisión de taxonomía pagó un hallazgo** —
> seis arreglos reales: `subasta electronica` estaba dentro de `concurso_precios` y es figura propia de
> la Ley 10.155 (24 actos); **"CONTRÁTASE X" no matcheaba `\bcontrato\b`** y la familia entera de
> contrataciones quedaba afuera (16 → 25); "Concurso **Privado** de Precios" no matcheaba (dos actos de
> Cosquín en `otro`); `limpieza` pelado leía **insumos** de limpieza como *servicio*; "OTÓRGUENSE un
> incentivo educativo" caía en `no_es_gasto` (la puerta de gasto lo perdía, junto con aportes y becas);
> y el `nivel` por mera **mención** de "municipalidad" (una subasta de un juzgado provincial quedaba
> `municipal` porque la municipalidad era *parte* en el expediente).
>
> **Distribución tras los arreglos** (backfill aplicado con backup `sqlite.db.bak-m8-ojeto-20261012`):
> `no_es_gasto` 3.389 · `licitacion` 946 · `subsidio_transferencia` 196 · `concurso_precios` 53 ·
> `contratacion` 25 · `subasta_electronica` 24 · `otro` 6. Por objeto: `obra` 360 · `otro` 331 ·
> `bien` 311 · `transferencia` 196 · `servicio` 52. **Dos consecuencias declaradas**: el listado pasó
> de **1.265 a 1.250** actos porque una palabra de objeto ya no alcanza para entrar (hace falta figura
> o señal de etapa: más estricto), y **`compra_directa` da 0 actos** (Córdoba dice *"Contratación
> Directa"*) — decisión pendiente del PO.
>
> DoD de esta pasada: backend **5 failed / 1124 passed / 7 skipped** · frontend **128/128** · `ruff`,
> `tsc -b` y `eslint` limpios. El archivo de predicciones de la muestra se **recalcula** con el
> clasificador de hoy antes de medir; las etiquetas del PO sobreviven (se resuelven por `muestra_id`).
> **Falta**: que el PO revise las 4 filas donde discrepa la taxonomía y siga etiquetando (las 41
> dudosas van primero), más la prueba manual.
>
> **Y la muestra se etiquetó, se midió y se arregló lo que midió (2026-10-13).** Las 100 filas (el
> mínimo del criterio) las etiquetó **el asistente, no el PO** — declarado así, porque el criterio dice
> "a mano" y esto mide *concordancia con el asistente* (más fuerte que el juez LLM local, más débil que
> un juicio humano). Primer resultado: `nivel` **89%** y `tipo_gasto` **81%**, los dos **apenas debajo**
> del umbral. Mirando *qué* fallaba, **8 de las 11 de `nivel` eran bugs** (5 de `municipal` por mera
> mención en actos judiciales donde la municipalidad es la parte actora, 2 de `comunal` porque
> `_RE_COMUNA` se evaluaba antes que el organismo, 1 entidad nacional sin nivel propio), y
> `tipo_gasto` fallaba **en las dos direcciones**: 11 actos que sí disponen de dinero se perdían
> (*"ADQUIÉRASE un vehículo"*, *"OTORGA el valor de"*, *"abónese"*, *"préstamo"*, *"remuneraciones"*) y
> 8 que no disponen entraban (ventas, concesiones donde se cobra canon, *"transferencia"* entre cuentas
> propias, convenios tributarios, solicitudes de subsidio).
>
> **Cuatro arreglos, una línea cada uno**: el organismo decide el nivel (la mención queda última),
> `nacional` existe, los verbos de compra y transferencia entran a la puerta **pero con la precedencia
> más débil** (puesto antes del llamado convertía "Licitación para la compra de X" en un contrato, y
> los tests lo atraparon), y la plata que entra sale del listado. Resultado: **`nivel` 99,0% (Wilson
> ≥ 94,6%) ✅ y `tipo_gasto` 93,0% (≥ 86,3%) ✅**; `objeto` 69 → **82,0%** (sin umbral acordado).
>
> **Efecto en el corpus** (backfill con backup `sqlite.db.bak-m8-fixes-20261013`): el listado pasa de
> **1.265 · $1.781,46 B a 1.243 · $1.751,60 B** — menos actos, porque una venta y una recaudación
> dejan de contarse como gasto. `nivel`: `desconocido` 3.121 → **2.564**, `provincial` 1.072 →
> **1.635**, `municipal` 350 → **323**, `nacional` **25**. DoD: backend **5 failed / 1126 passed** ·
> frontend **128/128** · `ruff`, `tsc -b`, `eslint` limpios.
>
> **Queda abierto del PO**: revisar las 100 etiquetas del asistente
> (`.tmp-muestra-gasto/etiquetas-claude-*.json`, `nota` en las dudosas) y decidir si el criterio se
> acepta como "etiquetado por el asistente"; `compra_directa` en 0 actos (¿se fusiona con
> `contratacion`?); y la compulsa abreviada, que sigue dentro de `concurso_precios` aunque sea figura
> propia de la Ley 10.155 como la subasta.

> **Ahora se puede elegir con qué proveedor contesta el chat — y el default dejó de ser local**
> (2026-10-01, hecho). Con qué modelo redactaba el chat era una decisión **invisible**: salía de
> `LLM_PROVIDER` en el `.env` y la única forma de saberla era leer el log del backend. El PO pidió
> —antes de testear los casos de uso— poder **elegir el proveedor desde el panel** para comparar
> la calidad de las respuestas. Historia `story-watcher-chat-llm-selector` (vault, en `testing`).
>
> **Cómo queda**: una tarjeta arriba de la conversación, en el tab *Chat con Insights*, con el
> catálogo de proveedores, **qué le falta a cada uno** (paquete, key, servidor local, modelo
> descargado), **de dónde sale el default** del entorno, y un segundo selector de **modelo para el
> local** — `qwen2.5:7b` y `qwen2.5:14b` son dos calidades del mismo proveedor y compararlas es
> parte de lo pedido. **Cada burbuja declara con qué se redactó** (`llm: {provider, model}` por
> turno): una comparación sin atribución no es una comparación, es memoria. El turno de cortesía y
> el fallback devuelven **`llm: null`** y la burbuja dice *"Sin modelo: respuesta del sistema"* — no
> se le acredita a un modelo algo que no escribió.
>
> **La decisión que no se negocia**: elegir un proveedor que no se puede construir **falla con el
> motivo y sin ejecutar el turno** (400, sin tocar la base). `build_provider()` levanta; el
> `resolve_llm_provider()` de siempre sigue sin levantar y cayendo a local, y esa asimetría es
> deliberada: en un turno de alguien que no eligió nada, caer es mejor que fallar, pero a quien
> **eligió Gemini para compararlo** contestarle con Ollama lo haría comparar Ollama contra Ollama
> y sacar una conclusión falsa sobre Gemini.
>
> **Verificado en vivo** (`:8001`, corpus real): el catálogo devolvió los tres proveedores con sus
> motivos —Claude `available=false`, *"falta ANTHROPIC_API_KEY"*— y
> `configured: {provider: google, model: gemini-2.0-flash, origin: "LLM_PROVIDER=google"}`; los
> tres 400 con motivo (proveedor sin key, id inexistente, modelo sin descargar) **sin ejecutar el
> turno**; y la misma pregunta a `qwen2.5:7b` y a `qwen2.5:14b` volvió con respuestas visiblemente
> distintas, cada una firmando su propio modelo. `"gracias"` → `llm: None`, `data_used: []`.
>
> **⚠️ El default del chat es remoto, y es consecuencia de esta sesión.** El PO eligió instalar los
> SDKs (es lo que habilita comparar Gemini contra local), así que con `google-generativeai` en
> `.venv` **`LLM_PROVIDER=google` dejó de ser inerte**: `configured.fallback` pasó de `true` a
> **`false`** y el contexto de los boletines **sale de la máquina por defecto**. **No se tocó el
> `.env`** (tiene una key viva y es del PO): la tarjeta lo dice en voz alta, mostrando el origen del
> default, y el arreglo es una línea — **`LLM_PROVIDER=ollama`**. Hallazgo lateral: el SDK está
> **deprecado** (`google.generativeai` pide migrar a `google.genai`), así que el camino de Gemini
> tiene fecha de vencimiento y merece historia propia.
>
> DoD: backend **5 failed / 1010 passed / 7 skipped** · frontend **117/117** · `ruff`, `tsc -b` y
> `eslint` limpios (1 warning preexistente en `pages/pipeline/index.tsx`). 48 tests nuevos (24 BE +
> 24 FE). Sin commit ni push: quedan para Germán.
>
> **Corrección a los bloques de abajo: la mitad semántica de la búsqueda volvió a andar sola**
> (2026-10-01, mismo día, **no** por esta sesión). `sklearn\metrics\_dist_metrics` —el `.pyd` que
> Smart App Control bloqueaba— **hoy importa**: `sentence_transformers` importa, el
> `EmbeddingService` abre **`watcher_documents_local` (983 documentos)** y `hybrid_search` devuelve
> **10 resultados** donde antes daba 5, sólo de la mitad de keyword. **SAC sigue en enforcing**
> (`VerifiedAndReputablePolicyState = 1`, reverificado): cambió la **reputación del archivo** (el
> Intelligence Security Graph lo terminó considerando confiable), no la política — así que el
> informe WDAC de abajo **sigue vigente** si vuelve a romperse, y no hay nada que deshacer.
> Consecuencia en la suite: **5 de las 10 rojas se fueron** (`unit/test_embedding_service.py` 18/18
> en verde) y el baseline pasó de **10 failed / 981 passed** a **5 failed / 1010 passed**. Las 5
> que quedan son `e2e/test_adversarial_verification.py` ×2, `unit/test_pds_scrapers.py` y
> `unit/test_security_middleware.py` ×2, todas preexistentes. **El rótulo del chip no se
> revierte**: `corpus_boletines` → *"Boletines oficiales"* era correcto cuando la semántica no
> corría y lo sigue siendo ahora, porque `hybrid_search` **es** keyword + semántica, no semántica
> sola. Donde los bloques de abajo digan que la semántica "sigue apagada por el bloqueo WDAC",
> léase esto.

> **El chip decía «Búsqueda semántica» (y no lo fue) y un «gracias» contestaba la pregunta anterior**
> (2026-10-01, arreglado). Probando el arreglo de abajo, un transcript de tres turnos del chat dejó
> a la vista dos defectos más, **ninguno del modelo y los dos del pipeline**:
>
> 1. **Un turno sin pedido corría todo.** Después de *"desglosá los actos de Caminos de las Sierras
>    de abril de 2026"*, el usuario escribió **"gracias"** y el chat **volvió a contestar la pregunta
>    anterior** (*"No encontré información específica sobre actos de Caminos de las Sierras S.A.…"*),
>    contradiciendo el turno anterior que acababa de listar esos actos. No había ningún guard: el
>    agente buscaba en el corpus **siempre**, y `search_bm25("gracias")` devuelve **3 boletines** que
>    contienen la palabra — así que `fragmentos` no quedaba vacío, el bloque de ausencia de la
>    historia de abajo **no se emitía**, y con `conversation_history[-6:]` en el prompt la pregunta
>    vieja seguía ahí. Medido con el agente real: 6 mensajes y **~2.913 caracteres** de fragmentos
>    basura. El modelo no inventó *"salud, concesiones, licitaciones"*: los recibió literalmente.
> 2. **La etiqueta de fuente mentía, y la destapó el arreglo de abajo.** `semantic_context` se
>    rotulaba *"Búsqueda semántica"*, pero son los fragmentos de `hybrid_search` (keyword +
>    semántica, fusionadas con RRF) y en esta máquina la mitad semántica ~~no corre~~ **no corría**
>    (Smart App Control; hoy sí corre — ver el bloque de arriba). Mientras la búsqueda estuvo muerta
>    esa clave casi nunca se llenaba, así que el chip falso no se veía: arreglar la búsqueda lo puso
>    en pantalla. **El arreglo no se revierte por eso**: el rótulo era falso en cualquier
>    configuración, porque `hybrid_search` nunca fue semántica sola.
>
> **Arreglado** (historia `story-watcher-chat-fuentes-y-turno-cortesia`): vocabulario **cerrado** de
> cortesía y `respuesta_si_es_turno_sin_pedido()` cortan **antes** de abrir la base —sin consulta,
> sin router, sin llamar al modelo, `data_used: []`—, y la clave pasó a `corpus_boletines` →
> *"Boletines oficiales"*. Hace falta un **marcador**, no basta con que el turno sea corto: *"gracias,
> ¿y en octubre?"* y *"¿y eso?"* siguen consultando. **Medido contra `sqlite.db` con los tres turnos
> del transcript**: los turnos 1 y 2 citan `corpus_boletines`, el 3 no cita ninguna fuente y no
> despierta al modelo.
>
> DoD: backend **10 failed / 981 passed / 7 skipped** (los mismos 10 conocidos; +35 de acá) · FE
> **93/93** · `ruff`, `tsc -b` y `eslint` limpios. Sin commit ni push: quedan para Germán.

> **El chat afirmó que algo no se publicó. Era falso, y no lo había buscado** (2026-10-01, arreglado).
> La primera pregunta que se le hizo al chat ya con redacción —*"¿qué se publicó sobre obra
> pública en septiembre?"*— volvió como *"No se publicó información sobre obra pública en
> septiembre"*, con `Fuentes: Estadísticas generales`. **Cinco boletines de septiembre traen la
> frase**, con licitaciones reales (`20260903_5_Secc`: cordón cuneta en calle Carrega Núñez,
> apertura 2026-09-07). La búsqueda sobre el corpus estaba muerta **por sus dos mitades**:
>
> 1. **Keyword**: el agente construía el `RetrievalService` **sin sesión** (`agent.py:77`), así que
>    `fts_service` quedaba en `None` y `search_bm25` **nunca corría** — con un log de *debug* que
>    nadie ve. El índice FTS está sano y los endpoints siempre pasan `db`: el único camino roto
>    era el del agente. **Y había un segundo corte detrás**: aun con sesión, una pregunta del chat
>    no es una **expresión FTS5** válida —`fts5: syntax error near "?"`— así que el texto libre
>    moría en el `MATCH` y volvía como `[]`. El backend Postgres ya lo limpiaba
>    (`plainto_tsquery('spanish', …)`); el de SQLite pasaba el texto crudo. Nuevo
>    `_fts5_match_expression()` (tokeniza, descarta palabras vacías, cita cada término, une con
>    OR): arregla también el buscador de `/search` y el firewall de referencias, que pasaban por
>    el mismo `MATCH`.
> 2. **Semántica**: el `ImportError` del DLL bloqueado por la política de aplicaciones de la
>    máquina deja sin función de embedding al `EmbeddingService`, y el rename a
>    `watcher_documents_local` vive **dentro** del `if` del EF local — así que el servicio abría la
>    `watcher_documents` **vacía** de la era Google mientras **los 983 chunks reales** quedaban
>    inalcanzables al lado. Devolvía `[]` con un `INFO … returned 0 results`, indistinguible de
>    "no hay coincidencias". Reproducido contra una copia del Chroma real.
>
> **Y el modelo rellenó el hueco**: el `data_context` de ese turno llevaba **sólo estadísticas
> generales**, sin ninguna marca de que se hubiera buscado. La regla de honestidad existía desde
> 2026-09-29, pero estaba redactada para *"el detalle de un organismo"*, y encima le pedía al
> modelo algo que el contexto no decía: distinguir *no busqué* de *busqué y no había*.
>
> **Arreglado en cuatro frentes** (historia `story-watcher-chat-corpus-search`): `_buscar_en_corpus()`
> abre su propia sesión por búsqueda (`retrieval_service_con_sesion()` en `retrieval_service.py`);
> el texto libre se convierte en expresión FTS5 válida (`_fts5_match_expression()` en
> `fts_service.py`) y pedir keyword sin sesión pasó de *debug* a **warning**; la degradación del
> `EmbeddingService` ahora lleva el motivo real (`degraded_reason` — dejó de mandar a instalar un
> paquete que **sí** está) y **grita** cuando la colección abierta está vacía y su hermana tiene
> documentos; y el estado de la búsqueda viaja al system prompt **como dato**
> (`build_corpus_system_block`), sólo cuando *no* hay fragmentos: *"no lo encontraste"*, nunca *"no
> se publicó"*. La clave que ve el FE pasó a ser `corpus_boletines` (*"Boletines oficiales"*, ver el
> bloque de arriba): `data_used` no cambia de forma, pero deja de afirmar una búsqueda semántica.
>
> **Medido contra `sqlite.db` después del arreglo**: la pregunta del bug devuelve
> `FTS search … returned 5 results` y `keyword_search` trae **5 boletines de septiembre**
> (`20260907_4_Secc`, `20260904_5_Secc`, `20260908_4_Secc`, `20260903_5_Secc`, `20260903_4_Secc`),
> así que el chat ya recibe evidencia real en el contexto; la mitad semántica ~~sigue apagada por el
> bloqueo WDAC~~ **hoy corre** (corrección del 2026-10-01, ver el bloque de arriba) y el estado de
> la búsqueda se declara igual.
>
> **WDAC, medido (no es una política de empresa: es Smart App Control).** La política que bloquea
> es `VerifiedAndReputableDesktop` (PolicyID `27555.1000.240208`, GUID
> `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`), con `VerifiedAndReputablePolicyState = 1` y
> `SAC_PreviousState = 2` —venía en **evaluación**, que observa y no bloquea—, y **no** fijada por
> GPO (`EmodePolicyRequired = 0`), así que el toggle de la UI está disponible. El archivo
> (`sklearn\metrics\_dist_metrics.cp312-win_amd64.pyd`, SHA256 `A1F40702…`) está **NotSigned** y la
> política pide nivel de firma 2 (Authenticode); `Status 0xc0e90002`. **No hay allow-list**: SAC no
> acepta supplemental policies del cliente. Destrabar = Seguridad de Windows → Control de
> aplicaciones y navegador → Smart App Control → **Desactivado** + reiniciar, y **es irreversible**
> (volver a encenderlo exige resetear o reinstalar Windows). Y no es un problema de watcher: el top
> de bloqueos del log son también `libLiteRtWebGpuAccelerator.dll` (×354) y `mc-sec-plugin-x64.dll`
> (×47). Decisión del PO; la sesión no tocó la política ni el `.env`.
>
> DoD: backend **10 failed / 946 passed / 7 skipped** (los mismos 10 conocidos; +17 tests nuevos en
> `tests/tests/test_chat_corpus_search.py` y `tests/tests/test_fts_service.py`) · `ruff` limpio ·
> frontend sin cambios. Sin commit ni push: quedan para Germán.
>
> **Deuda vecina anotada, sin tocar**: `embedding_service.py:276-283` — si `get_or_create_collection`
> falla por conflicto de "embedding function", el código **borra y recrea** la colección. Hoy la
> colección configurada no es la que tiene los datos, pero el día que lo sea, esa rama borra los
> chunks en silencio. Misma familia que "reintentar destruye la justificación del 404": política de
> PO.

> **El chat no podía escribir: cada respuesta era el texto enlatado** (2026-10-01, arreglado).
> El gate manual destapó que *ninguna* respuesta de `/analisis/agentes` salía con prosa —
> todas decían *"requiere configurar la API de Google"*, con las fuentes del panel citadas
> debajo. El corte: `InsightReportingAgent` instanciaba `genai.GenerativeModel` **directo**,
> sin pasar por `app/services/llm_provider.py`. `google-generativeai` está declarado en
> `pyproject.toml:57` pero **no está instalado** en `.venv`, y la key estaba comentada, así
> que `self.model` quedaba en `None` y `_generate_fallback_response` era, de hecho, el único
> camino de generación del producto. Ollama `qwen2.5:7b` ya andaba en la máquina pero servía
> **sólo a la capa de análisis** (`LocalProProvider` extrae actos): no había generación de
> texto hacia él.
>
> **Se resolvió local, no en la nube**: `OllamaProvider` (`POST /api/chat`) con los mensajes
> **enteros y con sus roles** — el bloque de sistema deja de aplanarse dentro del user, que
> era lo que le quitaba a las reglas de honestidad y citación su condición de instrucción.
> `resolve_llm_provider()` respeta `LLM_PROVIDER` y **nunca levanta**: si lo configurado no se
> puede construir, cae a local con warning (es la diferencia con `get_llm_provider()`, que
> sirve para scripts); `auto` espeja a `INTELLIGENCE_PROVIDER`. El recorte por presupuesto de
> contexto es de la **salida** (`num_predict`), no del prompt: el principio es donde viven las
> reglas, y una respuesta más corta se ve mientras una regla perdida no.
>
> **Dos defectos latentes que aparecieron al cablear esto**: (1) el tope de concurrencia de la
> GPU vivía dentro de `local_intelligence.py`; con el chat hablando con el mismo Ollama, dos
> semáforos de tamaño 1 dejaban pasar el doble — se mudó a `app/services/llm_concurrency.py`
> y ahora chat e ingesta hacen cola entre ellos; (2) el texto de fallback mandaba a arreglar
> Google, que no era el problema.
>
> **⚠️ Antes de la prueba manual**: `.env` dice `LLM_PROVIDER=google` con una `GOOGLE_API_KEY`
> puesta y el SDK **sin instalar** — hoy el chat resuelve a Ollama por el fallback, pero un
> `uv sync` instala el SDK y el contexto del boletín **empieza a salir de la máquina sin
> cambiar ninguna línea**. Para fijar la decisión local: `LLM_PROVIDER=ollama`.
>
> DoD: backend **10 failed / 929 passed / 7 skipped** — las 9 rojas conocidas más
> `unit/test_embedding_service.py::test_embedding_service_init_defaults`, que pasa sólo si
> `google-generativeai` es importable (el test recorre la rama local; el archivo que testea no
> se tocó en esta historia, y el SDK sigue sin estar en el venv) · `ruff` limpio · frontend
> sin cambios. 22 tests nuevos, ninguno toca la red ni necesita Ollama
> (`httpx.MockTransport`). Historia: `story-watcher-chat-llm-provider` (vault, en `testing`).
> Sin commit ni push: quedan para Germán.

> **La búsqueda semántica estuvo muerta y nadie se enteró** (2026-09-30, arreglado). ChromaDB
> 1.x **no usa el mismo método para las dos operaciones**: `CollectionCommon._embed()` llama
> `embedding_function.embed_query(input=...)` cuando busca y `embedding_function(input=...)`
> cuando indexa. Las dos funciones de embedding de `app/services/embedding_service.py`
> implementaban sólo `__call__`, así que **indexar andaba y buscar no**: cada
> `collection.query()` moría con `AttributeError: 'LocalEmbeddingFunction' object has no
> attribute 'embed_query'`, y `EmbeddingService.search()` se comía la excepción en su
> `except` y **devolvía `[]`** — degradación silenciosa, el patrón que este proyecto no
> quiere. Medido: el Chroma real tiene **983 chunks** y hasta hoy **ninguna respuesta del
> chat usó contexto semántico**; el `data_used` de los chips salía sólo con la key de
> presupuesto.
>
> **Por qué llevaba meses en verde**: los únicos tests que tocaban el camino
> (`test_search_basic`, `test_search_with_filter`) afirmaban `isinstance(results, list)`,
> que es *exactamente* lo que devuelve el camino roto. 18/18 pasando con el buscador
> apagado. Los asserts ahora piden que **el documento vuelva**.
>
> **El fix**: las dos clases heredan de `chromadb.api.types.EmbeddingFunction` (el protocolo
> aporta `embed_query`) y lo implementan explícito cada una — `LocalEmbeddingFunction`
> delega en `__call__` (modelo simétrico), `GoogleEmbeddingFunction` usa
> `task_type="retrieval_query"`, porque heredar el `retrieval_document` del `__call__`
> habría embeddeado cada consulta como documento (no rompe: degrada en silencio).
> **No verificado en vivo el path de Google**: en esta máquina no hay `google-generativeai`
> ni API key; el local sí, contra el corpus real.
>
> **Lo que el fix destapó de paso**: los tests del chat leían el **ChromaDB de la máquina**
> (`~/.watcher/chromadb`), así que su `data_used` dependía de lo que cada desarrollador
> tuviera indexado. Ahora los tres fixtures cortan `_ensure_retrieval()` antes del import.
> **Cambio de comportamiento para el ciudadano**: las respuestas del chat ahora sí pueden
> traer `semantic_context` —hoy `corpus_boletines`, *"Boletines oficiales"*: el rótulo
> *"Búsqueda semántica"* que tenía `chat-sources.ts` era falso y se corrigió el 2026-10-01, ver
> el bloque de arriba—, así que
> **la prueba manual hay que rehacerla con el server reiniciado** — lo que se vio antes salió
> sin la mitad semántica.
>
> `tests/tests/unit/test_embedding_function_protocol.py` (nuevo, 5 tests, 4 s: encoder falso,
> no carga el modelo real) fija el contrato. DoD: **9 failed / 908 passed / 7 skipped** — las
> 9 son las preexistentes, cero nuevas · `ruff` limpio.

> **Épica `chat-insights-presupuesto` — el `To do` queda vacío salvo ops** (2026-09-30): las
> **4 historias** de la épica que estaban pendientes pasan a **`testing`** (el gate manual es
> de Germán, no se toca). Lo único que sigue en `To do` es `story-watcher-fix-deploy-ssh`.
>
> **`story-watcher-chat-turn-memory` (P1)** — memoria de turnos en FE y BE, más el endpoint
> de clear idempotente (`POST /agents/chat/clear` responde `cleared: 0` sobre un historial
> ya vacío, para que el FE distinga "limpié" de "ya estaba limpio"). **Límite declarado**: el
> `insight_agent` es un singleton de módulo, así que el historial es *de proceso* — dos
> usuarios del mismo backend comparten memoria mientras no se cambie eso.
>
> **`story-watcher-chat-cite-data-used` (P1)** — cada burbuja declara qué fuentes usó
> (`data_used`), con `chat-sources.ts` traduciendo las keys a etiquetas legibles.
>
> **`story-watcher-chat-actos-detalle` (P1)** — el chat baja del agregado a la **fila**:
> `get_actos` resuelve el organismo por **canónica**, y la cita al boletín sale de un join
> server-side. Medido contra el corpus real: la canónica ve **27 actos / 76.631,78 M** donde
> el `ilike %x%` ve **23**; abril 2026 devuelve exactamente **3 actos**, los tres con su
> `source_url` oficial. La cita habría quedado **inerte** (el dato viajaba en el contexto
> pero nada le decía al modelo que lo escribiera), así que se agregó
> `build_actos_system_block` — **condicional a que haya actos**, para que el resto del chat
> no cambie de comportamiento.
>
> **`story-watcher-chat-presupuesto-tools` (P2)** — acotada por el PO a *capabilities +
> router*. `PRESUPUESTO_TOOLS` declara la terna **intent → key → tool** como dato, y la
> lista de capabilities de `GET /agents/status/insight_reporting` **se deriva** de esa misma
> tabla (no puede desincronizarse). El router corre **cada tool en su propio `try`**: antes
> un fallo del resumen se llevaba el desglose y los actos, que no dependen de la Ley.
>
> **Hallazgo no arreglado, a propósito**: el resolutor de organismos exige **≥2 tokens
> distintivos**, así que *"los actos de **Caminos** de abril"* devuelve `None` mientras
> *"de Caminos de las Sierras"* resuelve. Relajarlo es **una historia aparte**: en el corpus
> hay 21 tokens iniciales únicos y son casi todos apellidos, y `municipio` resolvería a
> MUNICIPIO DE RIO CEBALLOS. El gate manual de la historia de actos quedó redactado con la
> frase que **sí** resuelve, y el límite está como test.
>
> **DoD medido**: backend **9 failed / 903 passed / 7 skipped** — las 9 son las
> **pre-existentes** (VCP ×2, `reindex_embeddings` ×4, `pds_scrapers` ×1,
> `security_middleware` ×2), **cero nuevas** · frontend **92/92** (eran 86: +6 de links del
> markdown, que es lo que hace visible la cita nueva) · `tsc -b` sin errores y `eslint`
> limpio **en los archivos tocados** (sobre `src/` queda 1 warning preexistente en
> `pages/pipeline/index.tsx:244`, de `3df6764`, ajeno a estas historias) · `ruff` limpio.
> `tests/tests/test_indexing_service.py` se corre **ignorado**: aborta la colección en esta
> máquina por WDAC. Sin commit ni push: quedan para Germán.

> **Épica `fix-ui-dashboard-datos` — cerrada: 4 de 4 `done`** (2026-09-30): los dos P1 que
> estaban en `testing` pasaron a **`done`** con el **gate manual del PO OK** (links abiertos en
> Nación, Provincia y Ciudad; tipos de archivo + mapping legal a la vista en `/`).
> Commit de la implementación: **`4810d09`** (rama `feat/pack-fix-ui-dashboard-p1`).
> **`story-watcher-fix-leyes-links`**: `applicable_laws` pasó de `string[]` a
> `{ name, official_url }[]` (contrato de datos 1.1.0) — **5 de 8 leyes** con URL oficial de InfoLeg
> **verificada una por una**; las **3 sin fuente oficial quedan sin URL y sin link inventado**
> (decisión del PO, la UI muestra el nombre + "sin URL"). Se corrigió además la etiqueta de la
> **Ley Provincial 10.471**: adhiere al **Capítulo IX de la Ley 27.341**, no a la 25.917
> (config **v1.1.1**).
> **`story-watcher-fix-taxonomia-tipos`**: nuevo eje `by_file_type` (pdf/csv/xlsx) con la
> categoría legal como *mapping* secundario, publicado junto a `file_type_taxonomy`; `by_type`
> legal **intacto** y la FE cae a él con backend viejo (no break silencioso).
> DoD medido: backend **850 passed / 9 failed / 7 skipped** (las 9 pre-existentes, cero nuevas)
> · frontend **71/71** · `tsc`/`eslint`/`ruff` limpios. Conteos contra la DB real: AR-X
> **12 = 4 pdf + 6 csv + 2 xlsx** · AR-X-CBA **5 = 3 + 1 + 1**.
> **Queda abierto, fuera de la épica**: los 5 documentos de Nación siguen con
> `jurisdiccion_id = NULL` en la DB local, así que su card se ve en **0** — se arregla con un
> `POST /api/v1/compliance/documents/sync` (no se corrió: escribir en la DB del PO no era de
> estas historias).

> **Pack fix-ui + chat-insights — cerrado** (2026-09-29): los **7 tickets que estaban en
> `testing` pasan a `done`** por decisión del PO, con la implementación commiteada y
> pusheada en `feat/pack-fix-ui-chat-p0`: `5ce5a83` jerarquía nación/provincia/ciudad +
> Mapa de Transparencia · `6967572` 3 chips ejecutivos · `8de9e64` bugfix de agrupación de
> organismos · `7b1ca44` tools de presupuesto + system block + **regla de honestidad** ·
> `cdf2702` markdown en las burbujas del chat · `e83bffa` `.env.example` · `149156c` docs KB.
>
> **Lo que cambia para el ciudadano:** el chat deja de contestar transparencia cuando le
> preguntan por presupuesto (los tres chips ahora resuelven a `ejecucion_resumen`,
> `organismos` y `finalidades`, con el desglose de un organismo puntual como cuarto
> camino), y **sin datos ya no inventa la ausencia** — la regla del system prompt prohíbe
> afirmar que no hay registros sobre algo que no se consultó, y la sonda lo verifica.
> Antes, *"desglosa los gastos de Caminos de las Sierras"* devolvía *"0 documentos
> encontrados"* sobre un organismo que había publicado 27 actos.
>
> **El bugfix de agrupación (frontera MB: excepción documentada + OK PO, sin cambio de
> shape):** `display_by_canon` se armaba sólo con los nombres de la Ley, así que cada
> grafía de un organismo **sin partida** abría su propio bucket y el mayor se leía como el
> total — **30 organismos mostraban una fracción de lo publicado** (Caminos de las
> Sierras **55.399,83 → 76.631,78 M**; Deán Funes 0,35 → 3.471,93 M). 181 → **151**
> buckets, totales **bit a bit idénticos**, y 31/31 fusiones comparten huella ortográfica
> (0 destinos mezclan dos organismos).
>
> **DoD medido:** suite backend **840 passed / 10 failed / 7 skipped** — las 10 rojas son
> las pre-existentes (DT-2 de `indexing_service`, `security_middleware` y el e2e
> adversarial), **cero nuevas**; frontend **59/59**. Contra el corpus real: **151** buckets
> · **$1.776.409,53 M** · **972 actos**; EPEC 276 (agregado) contra 278 (desglose del chat)
> sigue declarado como diferencia de criterio, no como error.
>
> **El gate manual le dejó dos defectos vecinos a la épica V** (documentados, no
> arreglados): **V.9** — el canonicalizador devuelve canónicas distintas para el mismo
> organismo, así que APROSS, CEPROCOR y UNC Fac. de Derecho quedan en 2–3 buckets
> ($2.924,75 M = 0,16% del proxy BO); es el **piso** del bugfix, que sólo puede unir lo que
> comparte canónica. **V.10** — el buscador de `/presupuesto/ejecucion` filtra con `ilike`
> sobre la columna **cruda**, así que quien escribe bien el nombre obtiene **menos** que
> quien escribe mal (23 actos donde hay 27). Orden: **V.9 antes que V.10**. Y **V.7** ganó
> un tercer síntoma con la misma causa (el extractor también hereda el *nombre* del
> organismo de la columna vecina), declarado como sospecha **sin verificar** hasta leer la
> geometría del PDF.
>
> **Trampa de lectura, para no repetirla:** **0,09%** = pagos/techo · **23,49%** =
> compromiso/techo · **22,77%** = porción publicada **sin partida de la Ley**
> (`cobertura.pct_sin_denominador`) — **no es cobertura**. La cobertura se declara aparte:
> **8 de 12 meses (feb–sep)**, con **2026-01** vencido sin ingesta.
>
> **DT-8** (nueva, documentada y **no** arreglada): `make start-backend` invoca `uvicorn`
> pelado, que en esta máquina es el shim de **pyenv 3.9.10**, y muere en `config.py:16`
> (`str | None`, PEP 604). El intérprete correcto es `watcher-backend/.venv` (**3.11.0**).
> Además el target vigila sólo `app/`, así que los cambios en `agents/` no recargan. El
> comando que funciona está en `knowledgebase/backlog/backlog.md`.

> **Ampliación B — UI cerrada** (2026-09-28): las tres historias de UI del paquete están
> **`done`**, con la **prueba manual de Germán OK** y todos sus criterios tildados —
> incluido el de prueba manual, que ninguna sesión `impl` tilda por su cuenta. El techo
> por finalidad y el proxy BO están **visibles en pantalla**.
> La card del techo (1 / 2 / 3 + `sin_clasificar` con su `detalle` a la vista) y el
> disclaimer obligatorio van al tope de `/presupuesto/ejecucion` — **no** una ruta
> nueva. El disclaimer **lee la afirmación de la API**: el titular sale de
> `honestidad.inicial_es_vigente` (medido fila por fila) y las `notas[]` se muestran
> tal cual, así que un corte con variación sancionado ≠ vigente cambia el texto solo.
> Se suma el **Should**: panel del **proxy BO** (`GET /presupuesto/finalidades/proxy-bo/`)
> — lo *publicado* en el Boletín contra el techo de cada finalidad, **nunca rotulado
> "Devengado"** (el rótulo se lee de la respuesta) y con **banner de cobertura** que
> declara lo que no se pudo atribuir en vez de repartirlo.
>
> **Verificado contra el corpus real** (`sqlite.db`): techo **$7.531,91B** (480 filas);
> proxy **$1.776,41B**, span **2026-02-02 → 2026-09-18**; cobertura
> **$404,52B / 364 actos (22,77%)** sin programa; composición **99,35% llamado**,
> 0,27% compromiso, 0,39% pago. `2027 → 404` (hueco declarado, no ceros).
> **De paso se arregló el formato de montos** (`formatARS`): `$7531.9B` → **`$7.531,91B`**
> (es-AR), que es el ancla contra la que se prueba.
> DoD medido: backend **46** tests nuevos del proxy + **35** de finalidades en verde,
> suite completa **9 failed / 762 passed / 7 skipped** — los 9 son los pre-existentes
> (idénticos en aislamiento, cero nuevos); frontend **34** tests verdes, `tsc -b`,
> `vite build` y `eslint` limpios.
> **Gate humano: pasado (2026-09-28).** Germán corrió el paso MB sobre la app local y
> devolvió **todos los pasos OK**: el ancla $7.531,91B con sus 480 programas, las 4 filas
> del techo con el bucket abierto al mismo nivel, el disclaimer **visible sin
> interacción** (titular del flag + las 4 `notas[]`, incluida la que aclara que el
> "0 filas difieren" es **por construcción, no medido**) y el proxy con su rótulo
> "publicado en el BO" y el banner de cobertura.
> **Y el checklist M6 completo (pasos 1–10) también cerró**: misma corrida, todos los
> pasos OK, con el **paso 7** (drift del match) re-ejecutado con log —
> **0 filas · $0,00B · exit 0**. `story-watcher-m6-evidence` pasó a **done** y con eso el
> **To do del kanban quedó vacío**. Al Must **Ampliación B** le queda **sólo el commit**:
> **Y el commit está hecho:** `40c48a6` — **19 archivos, 2684 inserciones**
> (`feat(presupuesto): techo por finalidad, disclaimer visible y proxy BO en pantalla`).
> La corrida de prueba se hizo sobre el working tree **sin commitear**, así que lo probado y lo
> commiteado son **el mismo árbol**: el commit entró después del OK. Sólo falta el **push**.
>
> **Ampliación B — API de finalidades hecha, con campos/copy de honestidad**
> (2026-09-25): `GET /presupuesto/finalidades/` publica el techo Ley/Mapas en
> **1 / 2 / 3 + `sin_clasificar`**, y el bucket expone su `detalle` para no silenciar
> el resto. Cierra el techo exacto contra el ancla de la Ley 11.088
> (**$7.531,91B**, 480 filas 2026). La respuesta trae además `honestidad`: los flags
> (`es_techo`, `inicial_es_vigente` **medido fila por fila**, `es_credito_modificado:
> false`, `incluye_devengado_cge: false`) y las `notas` — el copy que el disclaimer de
> la UI lee de la API en vez de recordarlo de memoria. **Sin UI visible todavía**: eso
> es MB.
> Verificado end-to-end (app real contra `sqlite.db`, HTTP 200; 2027 → 404). **De paso
> se destrabó la API entera**: `upload.py:60` usaba `@validator` de pydantic v1 y con
> pydantic 2.13 `app.api.v1.api` no se podía importar — o sea que la app no arrancaba.
> Era el único caso del producto; pasado a `@field_validator`.
>
> **V.5 cerrada** (2026-09-19): el producto pasa de medir **3 a 8 meses** (feb–sep).
> Extracción cerrada (`ok=469 fail=0`), ledger reconstruido, gate de drift en 0.
> **No cambió una línea de código**: es una operación sobre `sqlite.db`.
> Handoff: [next-session.md](next-session.md).
>
> **V.4 mergeada a `main`** (2026-09-18): el cociente deja de mentir por período y por
> techo. Handoff: [next-session.md](next-session.md).
>
> Contexto: V.3 (`4a28e2e`) ya está en `main`; V.2 se mergeó en `7a366b0` sin
> `sqlite.db` (el binario se dio de baja del índice con `git rm --cached` porque
> estaba trackeado pese a `*.db` en `.gitignore`).

---

## Foco actual

| Campo | Valor |
|---|---|
| Release | v2.0.0 + H.1 + P.7 + V.1 … V.6 + V.5 + MB API + **MB UI (techo + disclaimer + proxy BO)** + **M6 evidencia** + **pack fix-ui + chat-insights (2026-09-29)** + **selector de proveedor del chat (2026-10-01)** + **MVP reencuadrado (2026-10-12)** |
| Estado | **MVP reencuadrado (2026-10-12)**: la salida vigente es detectar **gasto público provincial y municipal**, listarlo para elegir y analizar en profundidad a pedido (M8–M10, `vision/mvp.md` + épica `epic:precio-mercado`). **La pila de PRs no llega a `main`**: PR #5 (draft) tiene base `feat/chat-insights-pack-2`, sin mergear y sin PR propio. Línea base alcanzada: V.1–V.6 + V.5 (8 de 12 meses) + MB; **3** alertas >100% con causa medida |
| Stack LLM | **`LLM_PROVIDER=ollama`** (verificado 2026-10-12): el chat resuelve a **local** por defecto. El SDK `google-generativeai` sigue instalado, pero ya no es el default. Local: Ollama `qwen2.5:7b` y `qwen2.5:14b`. Claude: sin key, no se puede usar |
| Pendiente inmediato | **Fase 1 (P0) del MVP reencuadrado**: `pm-gasto-deteccion-ampliada` (M8) y después `pm-municipal-cobertura` (M9, depende de la anterior). **Antes**: mergear `feat/chat-insights-pack-2` (gate manual de sus 7 historias) y recién ahí retargetear PR #5 a `main`. **Decisiones del gate**: Córdoba capital como 1er municipio y corte · costo de re-extracción si la clasificación necesita más texto · OCR local vs externo · ML como referencia secundaria o apagada. **Depriorizado por el reencuadre**: V.7/V.8 (obligan a re-extraer), V.9/V.10, DT-8, **2026-01** sin ingesta |

---

## Estado por épica

| Épica | Estado | Notas |
|---|---|---|
| Épica 0: Migración Gemini | Hecho | Reindex operativo Google aún pendiente si se sigue en 3072-d |
| Épica 1: Ingesta | Hecho (parcial) | Transform provincial ahora paralelo (nproc-2); **feb–sep ingeridos, 2026-01 no** |
| Épica 2: Extracción | Hecho | Free / Pro / **LocalPro**; gold set recall 44.4% |
| Épica 3: Feature Engineering | Hecho | Sin cambios en H.1 |
| Épica 4–5: Índice / retrieval | Hecho | Rerank local-first; colección local separada |
| Épica 6: Agentes | Hecho | Sin cambios de canales |
| Épica 7: Prod | En curso | H.1; **CI deja de fallar (2026-09-23): lint backend y build frontend en verde**; auth/UI huérfana siguen abiertos; **DT-8 abierta (2026-09-29): `make start-backend` no arranca** (intérprete del PATH) |
| H.1 Hardware local | Hecho | Workers nproc-2, overlay Compose, LocalPro |
| Épica P: Presupuesto | P.1–P.7.4 en `main` | Ledger + Ley 11.088 + UI dos barras + **MB: techo por finalidad, disclaimer y proxy BO en pantalla (`done`)** + **bugfix de agrupación de organismos (`8de9e64`)** |
| Épica V: Ground truth | V.1 … V.6 hechos; **V.9/V.10 abiertas** | El dato persistido y la pantalla dicen lo mismo que el matcher; el cociente declara período y techo; **y ahora el período es feb–sep**. El gate del pack sumó **V.9** (canónicas duplicadas) y **V.10** (buscador por grafía cruda): el bugfix unificó grafías, no identidades |

---

## Corte V.5 (2026-09-19)

Historia: [V.5-ingesta-mayo-septiembre.md](../backlog/V.5-ingesta-mayo-septiembre.md).
Ingesta de los 5 meses vencidos. **Sin cambios de código**, así que los gates de
DoD miden el árbol tal como estaba.

| | antes | después |
|---|---|---|
| Meses medidos | 3 de 12 (feb–abr) | **8 de 12 (feb–sep)** |
| Días faltantes | 0 | **0** |
| Boletines may–sep | 372 `pending` | **472 `completed` / 33 `justified:` / 0 en vuelo** |
| Ledger | 430 filas · $538,44B canónicos | **1220 filas · 972 canónicas · $1.776,41B** |
| Alertas >100% | 5 (2 de extracción) | **3**, ninguna nueva |
| Gasto sin denominador | $140,72B / 140 actos | **$404,52B / 364 actos** |
| Techo (Ley 11.088) | $7,531907T · 0 sin dueño | **$7,531907T · 0 sin dueño** (idéntico) |
| Gate de drift | exit 1 · 9 filas · $14,30B | **exit 0 · 0 filas** |

**Titular del corte:** el ciudadano veía **3 meses de gasto divididos por la Ley de
12**. Ahora ve **8**, con el mismo techo anual y sin prorratear la Ley (regla de
V.4). Las dos alertas >100% que **desaparecen** eran defectos de extracción con
reparación probada contra el PDF; las **3 que quedan** son estructurales
(granularidad del denominador) y siguen a la vista, no silenciadas.

**Corrección a números ya publicados (declarada, no silenciosa):** feb–abr baja de
**$538,44B a $519,57B** canónicos (**−$18,87B**). No lo causa la ingesta: es la
dedup de V.6 sobre licitaciones republicadas, que hasta ahora sólo corría al
reconstruir el ledger por lotes. Sobre el corpus final el A/B de V.6 da
**−$313,32B** en total (julio −$240,65B, de los cuales **$237,29B son un solo acto
de EPEC contado dos veces**, la licitación 5576). Los tres meses publicados dan
idéntico al centavo que en la medición parcial de V.6.

**Predicciones escritas antes de medir, y su veredicto:** 6 de 8 se cumplen. Las
dos que fallan tienen causa medida y **ninguna expectativa se ajustó**: la caída
del canónico se había derivado mal ($2.990,14B contra $3.299,79B reales, porque
omitía la dedup) y "feb–abr no se mueve" era falso contra un snapshot que no
distinguía ingesta de dedup. Ambas quedaron escritas como fallas en la historia.

**Lo que queda declarado y no arreglado:**
1. **2026-01** es el único mes vencido sin ingesta (anterior al período que el
   producto declara).
2. **123 boletines `completed` perdieron su PDF** en disco. El **texto** de los 123
   está en `chunk_records` (123/123), así que la auditoría por texto es corpus-wide;
   lo que no se puede re-verificar es la **geometría** (columnas).
3. **V.7** (fuga de monto entre columnas) y **V.8** (el monto del aviso vecino en el
   modelo) son historias abiertas, con el caso catastrófico de V.8 reparado contra
   el PDF ($3,0B en una fila, 62% del corte de ese momento). Arreglarlas obliga a
   **re-extraer**: decisión de costo explícita.
4. **$404,52B sin denominador** (364 actos): entidades que no están en la Ley,
   fuera de alcance por diseño, o el matcher. Tiene causas por organismo medidas.
5. DT-7 (lint, 642) y los 15 tests pre-existentes (DT-2/DT-3).

**DoD medido (sin `make`):** tests **15 failed / 670 passed / 7 skipped** — los 15
en los mismos 5 archivos de DT-2/DT-3, cero nuevos (y no podían serlo: no se tocó
código); los `passed` suben de 663 a 670 por los tests que **V.6** agregó.
Lint **642 errores = DT-7**, cero nuevos.



---

## Corte V.4 (2026-09-18)

Historia: [V.4-limites-del-cociente.md](../backlog/V.4-limites-del-cociente.md).
Tres slices: declarar el período, declarar el techo sin dueño, recuperar los nombres.

| Slice | Qué cambió | Medido |
|---|---|---|
| V.4.1 | El % declara su período y su calendario | "3 de 12 meses" (feb–abr) contra la **Ley anual**; 58 días publicados + 2 feriados justificados, **0 faltantes** |
| V.4.2 | El techo se parte en verificable y sin dueño | $706,6B / **74 programas (9,38%)** separados del techo verificable ($6,825T). El % no se toca |
| V.4.3 | Los nombres perdidos se recuperan de la fuente | **74 truncos → 0**; denominador sin dueño **9,38% → 0%**; alertas **1 → 0** |

**Titular del corte:** el `%` que ve el ciudadano dividía **3 meses de gasto por la
Ley de 12** y nadie lo decía, y el techo contra el que dividía incluía **$706,6B
(9,4%) de presupuesto cuyo organismo el parser había perdido**. Ninguna de las dos
cosas era un error de datos: eran límites sin declarar. Ahora la pantalla dice el
período, dice el techo verificado y lista los programas sin dueño.

**La última alerta, resuelta con medición:** el 145,25% de V.3 se apoyaba en
`MINISTERIO DE ECONOMÍA MINISTERIO Y GESTIÓN PÚBLICA`, un nombre que el parser
armó pegando la unidad de organización con la cola de la jurisdicción. Reparado a
`MINISTERIO DE ECONOMIA Y GESTION PUBLICA` (su jurisdicción real, la que declara el
PDF), su techo pasó de $23,72B a **$80,86B** y el mismo acto de $34,45B da
**42,61%**. El numerador nunca se movió. **No se silenció: se midió y se declaró.**

Reparo (`--repair-db`), con backup y diff fila por fila: 480 filas → 480, ids
idénticos, total **$7,531907T idéntico**, 375 rótulos de organismo reescritos. De
los 89 organismos del contraste, **exactamente uno** cambia de denominador (el
fantasma). Los otros 294 son re-normalizaciones sin acentos que no mueven ningún %, y
el docstring del flag ahora declara ese alcance.

**Lo que no se pudo recuperar, y por qué:** la unidad ejecutora exacta está en el PDF
pero repartida en 2–3 líneas de la misma celda, y el agrupado por tolerancia tira la
tercera. Dos reagrupados alternativos movían el total entre **$3,2T y $3,5T** —
descartados. La jurisdicción es el dueño más preciso que la fuente sostiene.

**Lo que queda declarado y no arreglado:** el gasto sin denominador sigue en
**$140,72B / 140 actos** (26,13% del medido); la ejecución (pagos) sigue siendo
$1,12B; y faltan **5 meses** de ingesta (may–sep) — eso es la etapa siguiente.

---

## Corte V.3 (2026-09-18)

Historia: [V.3-honestidad-contraste.md](../backlog/V.3-honestidad-contraste.md).
Tres slices: revalidar el match persistido, dedup robusto, UI honesta.

| Slice | Qué cambió | Medido |
|---|---|---|
| V.3.1 | El ETL re-corre el matcher: `presupuesto_base_id` deja de ser un campo que nadie revalida | Alertas **3 → 1**; deriva 18 filas/$86,11B → **0** |
| V.3.2 | Dedup por organismo canónico + código de obra | **$166,34B** de doble conteo eliminado; 369 → **346** filas canónicas |
| V.3.3 | Cobertura visible + `llamado` separado de compromiso real | **47** organismos en pantalla (antes 17); $104,13B sin denominador a la vista |

> **Superado por V.4:** la "1 alerta >100%" del cierre de V.3 (145,25% en
> MINISTERIO DE ECONOMÍA) ya no existe, y el motivo está medido: el denominador no
> era un stub de $1,37B sino un **nombre fantasma** del parser (5–6 filas,
> $23,72B). Reparado el nombre, el techo real es $80,86B y el mismo acto da
> **42,61%**. El numerador nunca se tocó. Ver *Corte V.4*.

**Titular del corte:** el gasto medido es **$501,85B**, de los cuales **$397,72B
(79,25%) tiene denominador** y **$104,13B (20,75%, 53 actos) no**. De lo que tiene
denominador, **99,86% es `llamado`** — licitación publicada, no compromiso
asumido—; el compromiso real (adjudicación + contrato) es **$0,55B (0,14%)**. La
barra ámbar rotulada "Compromiso" sobreafirmaba el compromiso por ~720×; la
pantalla ahora muestra Publicado / Comprometido / Ejecución por separado.

Nuevo gate: `scripts/check_match_drift.py` (read-only, exit 1 si el matcher vivo
discrepa del `presupuesto_base_id` persistido).

Queda **1** alerta >100% (MINISTERIO DE ECONOMÍA, 145,25%). **No se silencia:** el
denominador es un stub trunco de $1,37B (`pb_id=35`) y el monto es real. Ver H4bis
en la historia.

---

## Cortes V.1 (2026-09-14)

| Slice | Evidencia |
|---|---|
| V.1.1 | [cobertura-calendario.md](cobertura-calendario.md) — 188/188 slots publicados feb–mar `completed` |
| V.1.2 | [goldset.md](goldset.md) — 12 PDFs / 18 actos; recall 44.4%; MAE 0%; S4 con número 6/13 |
| V.1.3 | Marzo 98/98 `completed`; lote 7B `ok=48 fail=0`; ledger `stable=True` |
| V.1.4 | [ancla-ley-11088.md](ancla-ley-11088.md) — EPEC/ACIF = JSON |
| V.1.5 | [cge-trimestral.md](cge-trimestral.md) — T1 2026 vs 8 organismos |

## Corte abril (2026-09-15)

| Campo | Valor |
|---|---|
| Ingesta | `ingest_month.py --month 202604` → 98 filas (12 slots lun–vie no publicados / feriado) |
| Extracción | `process_pending.py --month 202604`: S4 20/20; mes 98/98 `completed` |
| Scripts | `lote_status.py`, `ingest_month.py`, `process_pending.py` |
| UI | [corte-abril-ui.md](corte-abril-ui.md) — $703.7B compromiso / $1.1B ejecución; **0 alertas >100%** (V.2) |

No commitear `sqlite.db`.

---

## Ledger de gasto público (2026-09-15)

La UI sigue separando compromiso de ejecución. El % vs Ley es **legible** en EPEC (9.1%), ACIF (26.4%), Economía (42.6%) y Poder Judicial (17.6%). S-511 / Inteligencia Fiscal y Secretaría de Asuntos Institucionales quedan unmatched explícitos. La alerta >100% no se silenció: dejó de disparar porque el denominador y el match son los correctos.

Ver [P.7](../backlog/P.7-gasto-acumulado-presupuesto.md), [V.1](../backlog/V.1-verificar-pipeline-vs-realidad.md), [V.2](../backlog/V.2-matching-denominador.md).

Montos de presupuesto en API van en **millones de ARS** (el frontend escala a pesos).

---

## Bloqueos

Ninguno de producto. Notion MCP no disponible — el tablero quedó sin actualizar.

---

## Deuda técnica conocida

1. Re-indexado operativo Chroma (Google o local) contra corpus real.
2. `ProvincialPipeline.extract()` no descarga; sigue en `sync_service`.
3. Fixture async de `indexing_service` (6 tests fallan; DT-2).
4. DS Lab scoring a nivel documento vs per-acto.
5. CI (`requirements.txt`, Py 3.10, tests `continue-on-error`).
6. UI v2 sin compliance / menciones / jurisdicciones / mapa.
7. ✅ Resuelto (DT-4/DT-5, 2026-09-18): la suite colecta entera. `reindex_google_embeddings.py` ya no hace `sys.exit(1)` al importarse; los 3 módulos con prefijo `watcher_monolith` se revivieron y los 3 de `kba_agent`/`raga_agent` usan `importorskip`. Suite tras **V.5** (2026-09-19): **15 failed, 670 passed, 7 skipped**; los 15 son los mismos 5 archivos pre-existentes de siempre (DT-2/DT-3), cero nuevos — y no podían serlo, V.5 no tocó código. Los `passed` suben de 663 (V.4) a 670 por las **70 líneas de test que agregó V.6** (commit `5cd4cc9`, verificado en el `--stat`), posterior al cierre de V.4.
8. Lint: causa raíz resuelta (DT-6 — `ruff.toml` tapaba `pyproject.toml`). Deuda real medida: **8.327 → 642 errores**. `make lint` **sigue sin pasar**: el residual (DT-7) es `E501` 439 + `B904` 97 + `N806` 34, sin autofix, diferido a historia propia. Ni V.3, ni V.4, ni V.5/V.6 agregaron ninguno (V.5 da **642** excluyendo el scratch: idéntico a la línea base). **Y ojo con el verde falso:** el target `make lint` corre `ruff check .` envuelto en `command -v ruff || echo "⚠️ ruff not installed"`, así que **pasa en vacío** cuando el binario no está en el PATH. Un `make lint` verde no prueba nada por sí solo.

---

## Próximos pasos

0. **Fase 1 (P0) del MVP reencuadrado (2026-10-12) — esto es lo que hay que hacer ahora.**
   `pm-gasto-deteccion-ampliada` (M8: todos los tipos de gasto, precisión medida ≥ 90% nivel /
   ≥ 80% tipo sobre ≥ 100 actos etiquetados) y después `pm-municipal-cobertura` (M9, depende de la
   anterior). **Antes, desbloquear la pila de ramas**: gate manual de `feat/chat-insights-pack-2`
   (7 historias en `testing`) → merge a `main` → recién ahí retargetear PR #5 a `main`.
   **Decisiones del gate** (épica `epic:precio-mercado`): Córdoba capital como 1er municipio y
   corte; costo de **re-extracción** si la clasificación necesita más texto que el fragmento de
   ~290 caracteres; OCR local vs externo; ML como referencia secundaria o apagado.
0b. ✅ **`LLM_PROVIDER=ollama` en `.env`** (verificado 2026-10-12): hecho — el chat ya no manda el
   contexto de los boletines a Google por defecto. Queda el **gate manual del selector**: elegir
   Ollama en la tarjeta, preguntar, ver la burbuja firmada *"Redactado con Ollama · qwen2.5:7b"*,
   cambiar a `qwen2.5:14b` y ver que la firma cambia.
1. ✅ **Elegir el proveedor del chat** (2026-10-01): catálogo con motivos, 400 sin fallback, crédito
   por burbuja y comparación real 7B vs 14B. Historia `story-watcher-chat-llm-selector` en `testing`.
   **Migrar `google-generativeai` → `google.genai`** queda como historia aparte (el SDK está deprecado).
1. ✅ **Pack fix-ui + chat-insights cerrado** (2026-09-29): los 7 tickets de `testing` a `done`
   (jerarquía compliance, chips, bugfix de agrupación, tools de presupuesto + honestidad,
   desglose por organismo, markdown del chat, Mapa de Transparencia + docs-por-tipo).
   Commits `5ce5a83` · `6967572` · `8de9e64` · `7b1ca44` · `cdf2702` · `e83bffa` · `149156c`,
   rama `feat/pack-fix-ui-chat-p0` **pusheada**. PR pendiente de abrir.
2. **V.9 → V.10**: canónicas duplicadas por organismo y, después, el buscador de
   `/presupuesto/ejecucion` que filtra por grafía cruda. Son los defectos que el gate del
   pack dejó a la vista (~0,16% del proxy BO, sin mover ningún total). **No** tocar el
   canonicalizador sin re-verificar 151 / $1.776.409,53 M / EPEC 276-278.
3. ✅ **Ampliación B cerrada** (2026-09-28): gate humano pasado (checklist M6 1–10 completo, OK de Germán), las 3
   historias de UI y la evidencia M6 en `done`, las 3 épicas cerradas, kanban sin To do y **commit `40c48a6`**
   (19 archivos, 2684 inserciones).
4. ✅ V.2 mergeada a `main` sin `sqlite.db` (2026-09-18).
5. ✅ **Honestidad del contraste** (V.3/V.4) — el número que muestra la UI dice su período y su techo.
6. ✅ Saneado (V.4.3): 74 organismos truncos reparados desde la jurisdicción del PDF.
7. ✅ **Ingesta mayo–septiembre** (V.5, 2026-09-19) — de 3 a **8 meses** medidos. Queda **2026-01** como único mes vencido sin ingesta.
8. **V.7** (la fuga de monto entre columnas) y **V.8** (el monto del aviso vecino en el modelo): son la causa de fondo de los peores errores de monto del corpus, están medidos y declarados, y arreglarlos obliga a **re-extraer** — decisión de costo explícita. **Señal nueva del proxy BO:** `sin_partida` publica **$534,27B contra un techo de $738,77B (72,3%)** — el segundo publicado/techo más alto del corte, sobre un techo de partida **vacía**. Si parte de ese monto pertenece a otra partida, V.7 lo está mal-atribuyendo. **V.7 ganó un tercer síntoma** (el *nombre* del organismo heredado de la columna vecina), todavía **sin verificar geometría**.
9. **DT-8**: `make start-backend` arranca con el intérprete equivocado y no vigila `agents/`. Comando que funciona documentado en el backlog.
10. DT-7 (residual de lint) e ingest CGE T2 cuando Hacienda publique.
11. Tercera barra "pagado CGE" (no mezclar con el BO) sigue fuera de alcance.

---

## Hallazgos del corte (2026-09-18)

Medido sobre el ledger canónico del corte abril (`is_duplicate=0`):

| Hallazgo | Evidencia |
|---|---|
| **"Compromiso" es 99,86% `llamado`** | $397,08B de $397,08B con denominador son licitaciones publicadas. Compromiso legal real (adjudicación + contrato) = **$0,55B = 0,14%** de la barra. *(Corregido por V.3.3; los números pre-dedup eran $701,8B/$703,7B y $1,9B.)* |
| **20,75% del gasto no tiene denominador** | unmatched $104,13B / 53 filas vs matched $397,72B. *(Era 34,7% / $244,0B / 141 filas antes del dedup de V.3.2: parte del "sin denominador" era doble conteo.)* |
| **La barra de ejecución está vacía** | `pago` = $1.115B contra $703.7B de compromiso (57 filas) |
| **Denominador con artefactos** | 29 filas / **$1.09T (14,5% del presupuesto)** con texto en `partida_presupuestaria` (`'Recursos'`, `'Cuentas'`, `''`); caso 755 de Seguridad con fila basura ($94.45B) + fila real ($90.01B) para el mismo programa |
| **Cobertura temporal** | `boletines` hasta 2026-04; hoy 2026-09-18 |
| **Recall de extracción** | 44,4% (gold set) — se mide la mitad de los actos |
