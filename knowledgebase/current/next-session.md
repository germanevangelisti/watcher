# Próxima sesión — Watcher Agent

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
uv run pytest -q                                     # 15 failed / 670 passed (DT-2/DT-3)
uv run ruff check .                                  # 0 = DT-7 cerrada (2026-09-23)
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
