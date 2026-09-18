# Próxima sesión — Watcher Agent

**Fecha del handoff:** 2026-09-18
**Trabajo cerrado esta sesión:** **V.4 límites del cociente** (V.4.1–V.4.3). El %
declara su período (3 de 12 meses, contra la Ley anual) y su techo ($706,6B / 74
programas sin organismo, reparados desde el PDF). Alertas 1 → 0, con el motivo medido.
**Trabajo siguiente:** **ingesta mayo–septiembre.** El producto mide feb–abr y hoy es
septiembre: 5 meses sin ingerir, y eso convierte el gasto medido en un piso.

> **Antes de seguir: leer [status.md](status.md) y
> [V.4-limites-del-cociente.md](../backlog/V.4-limites-del-cociente.md).**
> `main` ya tiene V.1–V.4. El cuerpo de abajo es el handoff de V.2 y **ya no describe
> la DB de hoy**: los números de $703,7B y "0 alertas >100%" son del corte pre-V.3.

---

## La etapa siguiente: ingesta mayo–septiembre

Es lo que más mueve la aguja y lo que está bloqueando la lectura del año. Estado de
partida medido (corte V.4):

| | valor |
|---|---|
| Boletines ingeridos | 2026-02-02 → 2026-04-30 (60 días: 58 publicados + 2 feriados justificados) |
| Meses vencidos sin ingerir | **2026-01, 2026-05 … 2026-09** (6) |
| Gasto medido | $538,44B canónicos; $397,72B con denominador |
| Denominador | Ley 11.088 completa: $7,531907T — y **el 100% tiene dueño** (V.4.3) |

Órden de trabajo sugerido:

1. `ingest_month.py --month 202605` … `--month 202609`, verificando por mes el
   calendario (`justified:` vs `failed` sin justificar: la pantalla ahora lo muestra
   en rojo si falta un día sin explicación).
2. `process_pending.py --month <mes>` para extraer los actos.
3. Re-correr `etl_analisis_to_ejecucion.py` y después
   `scripts/check_match_drift.py` — el gate de V.3: si el matcher vivo discrepa del
   `presupuesto_base_id` persistido, exit 1.
4. Recién ahí el `%` empieza a parecerse al avance del año. **No prorratear la Ley**
   para acelerar la comparación: es la regla que V.4 dejó escrita.

## Lo que V.4 dejó declarado y sin arreglar

- **Gasto sin denominador: $140,72B / 140 actos (26,13%)** — publicado sin partida
  comparable. V.3 lo hizo visible; V.4 verificó que no gana techo con el reparo.
- **Ejecución (pagos): $1,12B** contra $537,32B publicados. La barra azul sigue casi
  vacía: el boletín publica licitaciones, no pagos.
- **Unidad ejecutora exacta**: el PDF la tiene partida en 2–3 líneas por celda y el
  agrupado por tolerancia descarta la tercera. Los dos reagrupados que probé movían
  el total entre $3,2T y $3,5T. Si alguien quiere recuperarla, el trabajo es rehacer
  el agrupado **y** demostrar que el total no se mueve — no antes.
- **Recall de extracción 44,4%** (gold set): se mide la mitad de los actos.

---

## Dónde quedó

Rama: `feature/V.2-matching-denominador`. Mergear **sin** `sqlite.db`.

Operar el denominador en una DB local:

```powershell
cd C:\Users\germa\watcher\watcher-backend
uv run python scripts/parse_pdf_presupuesto_2026.py --repair-db
uv run python scripts/etl_analisis_to_ejecucion.py
```

| Mes | DB | Notas |
|---|---|---|
| 202602 | cerrado V.1 | Carnaval justificado |
| 202603 | 98 completed | Cerrado V.1.3 |
| 202604 | 98 completed | Cerrado |

UI `/presupuesto/ejecucion`: 369 canónicos, **$703.7B compromiso / $1.1B ejecución**, **0 alertas >100%**. Detalle: [corte-abril-ui.md](corte-abril-ui.md).

## Qué quedó hecho (V.2)

Historia: [V.2-matching-denominador.md](../backlog/V.2-matching-denominador.md).

1. Bitácora V.2.1: [bitacora-alertas-v2.md](bitacora-alertas-v2.md).
2. Matching: Jaccard por tokens distintivos; stubs (`MINISTERIO DE`, `DIRECCIÓN DE MINISTERIO`) no matchean.
3. Denominador: `PODER JUDICIAL` + `PODER JUDICIAL -` → $103.3B (17.6%). Economía → $80.9B (42.6%).
4. Parser: `--repair-db` promociona truncos desde la jurisdicción. Tests S-511 / PJ / trunco. La UI **no** silencia >100%.

## Qué no hacer

- Meter pagado CGE en la misma barra que compromiso/ejecución del BO.
- Tratar $703.7B como ejecución SIGAF.
- Commitear `sqlite.db`, `*.db-wal`, `uv.lock`, PDFs, Mapas-por-Programas, xlsx CGE.

## Contexto mínimo

| Corte | Archivo |
|---|---|
| Handoff UI post V.2 | [corte-abril-ui.md](corte-abril-ui.md) |
| Ancla Ley | [ancla-ley-11088.md](ancla-ley-11088.md) |
| V.2 | [V.2-matching-denominador.md](../backlog/V.2-matching-denominador.md) |

Runtime LocalPro: `qwen2.5:7b`. Notion MCP no disponible.
