# AI Agents & Contributors Contract

This document defines roles, responsibilities, and interaction protocols for AI agents and human contributors working on the Watcher Agent project.

## AI Agent Roles

### Opus 4.5 - Planning & Architecture Agent
**Responsibilities:**
- Task decomposition and sprint planning
- Ticket creation and validation
- Architecture decisions and design reviews
- Requirements clarification and scope definition
- Code review and acceptance criteria validation

**Communication Protocol:**
- Creates tickets in the format: `S{sprint}-{number}: {Title}`
- Each ticket includes: Objective, Scope, Out of Scope, Definition of Done, Notes for AI Agents
- Validates implementation against ticket specifications
- Provides feedback through structured reviews

### Sonnet 4.5 - Implementation Agent
**Responsibilities:**
- Implementation of tickets according to specifications
- Code writing and refactoring
- Test creation and execution
- Documentation updates
- Bug fixes within ticket scope

**Communication Protocol:**
- Works on one ticket per branch
- Follows ticket specifications strictly
- Reports completion with summary of changes
- Escalates ambiguities or blockers to Opus 4.5
- Does not deviate from ticket scope without approval

## Interaction Contract

### Ticket Workflow
1. **Planning Phase** (Opus 4.5):
   - Analyzes requirements
   - Creates structured tickets
   - Defines acceptance criteria
   - Assigns to Sonnet 4.5

2. **Implementation Phase** (Sonnet 4.5):
   - Creates feature branch from ticket ID
   - Implements according to specification
   - Self-validates against Definition of Done
   - Commits with descriptive messages
   - **Updates Notion board status to "Hecho" via MCP** (see below)

3. **Review Phase** (Opus 4.5):
   - Validates implementation
   - Checks acceptance criteria
   - Approves or requests changes

### Notion Board Sync (Automated via MCP)

The project task board lives in Notion: "Tablero de tareas - Watcher".
All agents MUST update task status via the Notion MCP tool after completing work.

**Protocol:**
- When starting a task: update status to **"En progreso"**
- When finishing a task: update status to **"Hecho"**
- When blocked: update status to **"Por hacer"** and add a comment with the blocker

See `.cursor/rules/notion-sync.mdc` for the full protocol and data source IDs.

### Communication Rules
- **Clarity**: All communications must be explicit and unambiguous
- **Traceability**: Reference ticket IDs in all discussions
- **Scope Discipline**: Stay within defined ticket boundaries
- **Escalation**: Report blockers immediately, don't assume solutions
- **Documentation**: Update relevant docs with each change

## Operating Rules for Cursor Agents

### DO
- ✅ Follow ticket specifications exactly
- ✅ Use existing tools and commands in the repository
- ✅ Make minimal, incremental changes focused on ticket scope
- ✅ Document all changes clearly
- ✅ Test changes where applicable
- ✅ Align with Watcher Agent architecture
- ✅ Maintain clear communication

### DON'T
- ❌ Invent commands, tooling, or files not in repository
- ❌ Perform architectural refactors during Sprint 0
- ❌ Make large-scale redesigns without explicit approval
- ❌ Deviate from ticket scope
- ❌ Assume requirements - ask for clarification
- ❌ Skip validation steps
- ❌ Modify core architecture without planning approval

## Human Contributors Guidelines

### Getting Started
1. Read this document and [GPT-portal.MD](GPT-portal.MD)
2. Review current sprint tickets
3. Set up development environment (see Makefile)
4. Check existing documentation in `docs/`

### Contribution Workflow
1. Pick an unassigned ticket or create an issue
2. Create a branch: `feature/S{sprint}-{ticket-id}-{brief-description}`
3. Implement following the coding standards
4. Run tests and linting (see Makefile)
5. Submit PR with ticket reference
6. Address review feedback

### Coding Standards

#### Python (Backend & Lab)
- Follow PEP 8 style guide
- Use type hints where applicable
- Write docstrings for public functions/classes
- Keep functions focused and testable
- Maximum line length: 100 characters

#### TypeScript/React (Frontend)
- Follow ESLint configuration
- Use functional components with hooks
- Type all props and state
- Keep components focused and reusable
- Use meaningful variable names

### Repository Structure
```
watcher-agent/
├── watcher-backend/      # FastAPI backend + agents + tests + scripts
├── watcher-frontend/         # React + TypeScript frontend (v2: shadcn/ui + TanStack)
├── watcher-frontend-legacy/  # React + Mantine frontend (v1, deprecated)
├── watcher-lab/          # Data science notebooks and tools
├── docs/                 # Project documentation
│   └── architecture/     # Legacy architecture docs
└── boletines/            # Data storage (git-ignored)
```

### Development Commands
See [Makefile](Makefile) for unified development commands:
- `make install` - Install all dependencies
- `make start` - Start development servers
- `make test` - Run all tests
- `make lint` - Run linters
- `make build` - Build for production

### Environment Setup
1. Copy `.env.example` to `.env`
2. Add your `OPENAI_API_KEY` if using AI features
3. The system will run with warnings if API key is missing

## Quality Standards

### Code Quality
- All Python code must pass ruff checks
- All TypeScript code must pass ESLint
- No linter warnings in production code
- Meaningful commit messages following conventional commits

### Testing
- Unit tests for business logic
- Integration tests for API endpoints
- Frontend component tests where applicable
- Maintain or improve test coverage

### Documentation
- Keep README.md up to date
- Document breaking changes
- Update API documentation for endpoint changes
- Add inline comments for complex logic

## Issue Reporting

### For AI Agents
- Report blockers immediately in ticket thread
- Include: current state, expected state, attempted solutions
- Tag Opus 4.5 for planning decisions
- Don't proceed with assumptions

### For Human Contributors
- Use GitHub Issues with appropriate labels
- Include: reproduction steps, expected behavior, actual behavior
- Attach logs or screenshots if relevant
- Reference related tickets/PRs

## Cursor Cloud specific instructions

- Python dependencies live in `/opt/watcher-venv` (editable install of `watcher-backend[dev,ai]`). Login shells prepend that directory via `/etc/profile.d/watcher-venv.sh`. `uvicorn`, `pytest`, `ruff`, and `alembic` are also on `/usr/local/bin`.
- Frontend dependencies are `npm ci` in `watcher-frontend` (Node 22). Dev servers: API on port 8001, Vite on port 5173. Vite proxies `/api` to the API. `watcher-frontend/.env` is copied from `.env.example` on boot when missing.
- The default database is SQLite at `watcher-backend/sqlite.db`. Neo4j stays disabled unless `NEO4J_URI` is set. Do not copy the repo-root `.env.example` to `.env` here: it enables Ollama and local sentence-transformers, and the `[local]` extra (torch) is not installed.
- Boot sets `EMBEDDING_PROVIDER=google` when that variable is unset. Development mode otherwise defaults to local embeddings. `GOOGLE_API_KEY` is optional; the API starts without it and logs that Google features are unavailable.
- Postgres and Neo4j from `docker compose` are optional. Docker is not part of this environment.
- Checks that match CI: `ruff check app agents tests` in `watcher-backend`; in `watcher-frontend`, `npm run lint`, `npm run test -- --run`, and `npm run build`. Backend tests: `pytest` from the repo root (`pytest.ini`). On Python 3.12, expect a small set of pre-existing failures (security-middleware event loop, indexing mocks, adversarial VCP corpus); the rest of the suite passes.

## Questions & Clarifications

- **For AI Agents**: Ask Opus 4.5 in ticket thread
- **For Humans**: Open a GitHub Discussion or comment on relevant ticket
- **Urgent Issues**: Tag repository maintainers

---

**Document Version**: 1.0.0  
**Last Updated**: Sprint 0  
**Maintained By**: Opus 4.5 (Planning Agent)

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
