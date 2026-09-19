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
V.1–V.6 y **V.5 (ingesta mayo–septiembre)** están en `main`; H.1 también. El
producto mide **8 de 12 meses (feb–sep)** con el % declarando su período y su techo,
sin prorratear la Ley. Quedan **3 alertas >100%**, todas por granularidad del
denominador y todas visibles (no se silencian); **2026-01** es el único mes vencido
sin ingesta. Ver `knowledgebase/current/status.md`.
**Próxima sesión:** V.7 (fuga de monto entre columnas del extractor) y V.8 (el monto
del aviso vecino). Ojo: arreglarlas obliga a **re-extraer** el corpus. Leer
`knowledgebase/current/next-session.md`.