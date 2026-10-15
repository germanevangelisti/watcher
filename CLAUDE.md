# Watcher Agent — Project context for AI assistants

## Qué es este proyecto
Sistema de monitoreo ciudadano de boletines oficiales de la Provincia de Córdoba, Argentina. Ingiere boletines, extrae actos administrativos vía LLM, y persiste en PostgreSQL + Neo4j + ChromaDB. Stack: FastAPI + React + Google Gemini.

## Comandos esenciales
```bash
make install                    # Instalar dependencias
make start                      # Iniciar servidores de desarrollo
make test                       # Correr tests
make lint                       # Correr linters
make build                      # Build para producción
```

## Estructura clave
```
watcher-backend/    # FastAPI backend + agents + tests + scripts
watcher-frontend/   # React 18 + TypeScript + Vite (v2: shadcn/ui + TanStack)
watcher-lab/        # Data science notebooks y herramientas
watcher-doc/        # Datasets, modelos ML, análisis de datos
docs/               # Documentación técnica (legacy)
```

## Convenciones de commits
Formato: `<tipo>(<scope>): <descripción>`
Tipos: `feat` `fix` `refactor` `test` `docs` `chore`

## DoR (Definition of Ready) — antes de arrancar una feature
- [ ] Historia existe en `knowledgebase/backlog/` con criterio de aceptación
- [ ] Working tree limpio (`git status`)
- [ ] Rama `main` actualizada

## DoD (Definition of Done) — antes de mergear
- [ ] Tests pasan (`make test`)
- [ ] Linting limpio (`make lint`)
- [ ] Historia en backlog actualizada a `hecho`
- [ ] `knowledgebase/current/status.md` actualizado
- [ ] KB actualizada si hubo cambios de arquitectura (ADR)

## Estado actual del proyecto

**MVP re-priorizado (Germán, 2026-10-12).** La salida vigente dejó de ser el contraste
fiscal vs Ley 11.088 (M1–M7 + MB, ya alcanzado y en `main`): ahora es **leer los
boletines provinciales y municipales en busca de gasto público, listarlo para que el
usuario elija y analizar en profundidad a pedido**. Ver `knowledgebase/vision/mvp.md`
(M8–M10) y la épica `epic:precio-mercado` en el vault
(`board/epics/epic-watcher-precio-mercado.md`).

- **Fase 1 (P0):** `pm-gasto-deteccion-ampliada` (M8) **Done** (prueba manual de Germán OK 2026-10-13; muestra etiquetada parcial 13/150, cerrada así por decisión de Germán) — el gasto público se
  detecta y se lista (4.639 actos con monto clasificados por `tipo_gasto` y `nivel`; listado de 1.265
  actos · $1.781,46 B). Falta etiquetar la muestra ciega (150 actos,
  `watcher-backend/.tmp-muestra-gasto/`) y la prueba manual. Después: `pm-municipal-cobertura` (M9,
  depende de la anterior).
- **Rama de trabajo:** `feat/precio-mercado` (PR #5, draft) — **apilada sobre
  `feat/chat-insights-pack-2`**, que todavía no está mergeada a `main`. Nada de las dos
  llega a `main` hasta mergear primero la del chat (sus 7 historias esperan gate manual).
- **Línea base alcanzada:** V.1–V.6 y **V.5 (ingesta mayo–septiembre)** en `main`; H.1
  también. El producto mide **8 de 12 meses (feb–sep)** con el % declarando su período y
  su techo, sin prorratear la Ley; **3 alertas >100%** visibles por granularidad del
  denominador; **2026-01** es el único mes vencido sin ingesta. Ver
  `knowledgebase/current/status.md`.
- **Depriorizado por el reencuadre (no borrado):** V.7/V.8 (arreglarlas obliga a
  **re-extraer** el corpus), V.9/V.10, DT-8. Leer
  `knowledgebase/current/next-session.md`.

<!-- agent-session-rules:start -->
## Reglas de sesión de agente (Germán / Cooperledge)

- **Proyecto**: `watcher` · **Kanban**: `vault/wiki/board-watcher.kanban.md` · **Flujo**: PR a main (rama tipo/<proyecto-o-epica>-<id>)
- **Canónico** (leer si podés seguir links): `C:\Users\germa\cooperledge\vault\wiki\standards\agent-session-rules.md`

Reglas clave (valen aunque no abras el link):
1. **Leé el vault primero**: la historia (`vault/wiki/board/stories/<id>.md`), su épica, el kanban y `vault/wiki/status/watcher-status.md`. No re-especifiques lo documentado; si la doc no coincide con el código, manda el código y corregís la doc.
2. **Docs vivas**: actualizá la historia (checklist, Last updated, tests corridos) y el status (rama y SHA reales de `git log`) durante la sesión.
3. **Kanban**: solo movés `todo → wip → testing`. **Nunca `done`**: Done lo marca solo Germán tras su prueba manual. Máximo 1 historia en WIP. No tildes "Prueba manual de Germán OK". `kanban:` del frontmatter = columna del board.
4. **Ramas**: `tipo/<proyecto-o-epica>-<id>` (ej. `feat/cm2-receptor`); código a `main` por PR (salvo que el Flujo de arriba diga directo a main). `cursor/*` solo cloud agents. **Nunca force-push**, no mergees PRs sin OK de Germán, no borres ramas ni stashes ajenos ni toques archivos sin commitear de otra sesión.
5. **Cierre de sesión (DoD)**: tests corridos y anotados, historia/kanban actualizados, **commit + push del vault** (`cooperledge`, `main`, solo tus archivos) y del código en su rama. Nada queda solo en la PC.
<!-- agent-session-rules:end -->
