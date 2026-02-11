---
name: Sprint 0 Tooling Setup
overview: Implementar los 6 tickets del Sprint 0 para establecer contratos de agentes, herramientas de desarrollo, y CI/CD mínimo en el repositorio watcher-agent.
todos:
  - id: s0-001-agents-md
    content: Crear AGENTS.md con roles, protocolos y guías para agentes AI y contribuidores
    status: completed
  - id: s0-002-makefile
    content: "Crear Makefile con comandos: install, start, test, lint, build"
    status: completed
  - id: s0-003-env-example
    content: Crear .env.example y modificar watcher_service.py para startup graceful
    status: completed
  - id: s0-004-scripts
    content: Crear scripts/dev.sh y scripts/test.sh para desarrollo
    status: completed
  - id: s0-005-precommit
    content: Crear .pre-commit-config.yaml para Python y Frontend
    status: completed
  - id: s0-006-ci
    content: Crear .github/workflows/ci.yml con lint, test y build checks
    status: completed
---

# Sprint 0 - Tooling Contract & Repo Operating Manual

Implementar los 6 tickets definidos en [GPT-portal.MD](GPT-portal.MD) para establecer la infraestructura de desarrollo del proyecto Watcher Agent.

## Estructura del Proyecto Detectada

```
watcher-agent/
├── watcher-monolith/
│   ├── backend/          # FastAPI + Python (requirements.txt)
│   └── frontend/         # React + TypeScript + Vite (package.json)
├── watcher-lab/          # Python data science (requirements.txt)
└── scripts/              # Scripts existentes (reorganización boletines)
```

---

## S0-001: Create AGENTS.md

Crear [`AGENTS.md`](AGENTS.md) en la raíz del repositorio definiendo:
- Roles de Opus 4.5 (planificación) y Sonnet 4.5 (implementación)
- Protocolo de comunicación entre agentes
- Guías para contribuidores humanos
- Reglas operativas para Cursor Agents (ya definidas en GPT-portal.MD)

---

## S0-002: Introduce Makefile

Crear [`Makefile`](Makefile) con comandos unificados:

```makefile
# Comandos principales
install       # Instalar deps backend + frontend + lab
start         # Iniciar backend y frontend
test          # Ejecutar tests Python + Frontend
lint          # Lint Python (ruff/black) + Frontend (eslint)
build         # Build frontend
```

Aprovecha scripts npm existentes en `watcher-monolith/frontend/package.json`:
- `npm run dev`, `npm run build`, `npm run lint`

---

## S0-003: Add .env.example + Graceful Startup

**Archivo**: Crear [`.env.example`](.env.example) con:
```
OPENAI_API_KEY=your-openai-api-key-here
MAX_RETRIES=3
MAX_FRAGMENT_SIZE=2000
```

**Modificación requerida**: En [`watcher-monolith/backend/app/services/watcher_service.py`](watcher-monolith/backend/app/services/watcher_service.py), el constructor lanza `ValueError` si falta la API key:

```python
if not api_key:
    raise ValueError("OPENAI_API_KEY no encontrada...")
```

Cambiar a warning + modo fallback (similar a `InsightReportingAgent`).

---

## S0-004: Add Repo-Level Helper Scripts

Crear scripts minimos en `scripts/`:
- [`scripts/dev.sh`](scripts/dev.sh) - Inicia backend + frontend en paralelo
- [`scripts/test.sh`](scripts/test.sh) - Ejecuta tests de backend y frontend

---

## S0-005: Add Pre-commit Configuration

Crear [`.pre-commit-config.yaml`](.pre-commit-config.yaml) con hooks para:

**Python**:
- ruff (linter/formatter rapido)
- trailing whitespace, end-of-file-fixer

**Frontend (TypeScript/React)**:
- eslint
- prettier (opcional)

---

## S0-006: Add Minimal CI Workflow

Crear [`.github/workflows/ci.yml`](.github/workflows/ci.yml) con:
- Trigger: push y PR a `main`
- Jobs:
  1. **lint-python**: Ejecutar ruff sobre backend y lab
  2. **lint-frontend**: Ejecutar eslint sobre frontend
  3. **test-backend**: Ejecutar pytest (si hay tests)
  4. **build-frontend**: Verificar que el frontend compila

---

## Orden de Implementacion Sugerido

Los tickets son mayormente independientes, pero se sugiere:
1. S0-001 (AGENTS.md) - Base del contrato
2. S0-003 (.env.example) - Necesario para que otros desarrollen
3. S0-002 (Makefile) - Depende de entender los comandos
4. S0-004 (scripts) - Complementa Makefile
5. S0-005 (pre-commit) - Calidad de codigo
6. S0-006 (CI) - Automatización final