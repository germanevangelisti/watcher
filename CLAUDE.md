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
Épica 0 en curso — Migración OpenAI → Google Gemini. Ver `knowledgebase/current/status.md`.
Próximo: Épica 1 — Pipeline de Ingesta.