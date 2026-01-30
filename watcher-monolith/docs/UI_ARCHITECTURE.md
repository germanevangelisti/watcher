# UI Architecture - Sistema Watcher Fiscal

## Overview

This document describes the UI architecture for the Watcher Fiscal system, which provides a comprehensive interface for citizens and auditors to monitor fiscal activities, analyze administrative acts, and track budget execution.

## Technology Stack

- **Frontend Framework**: React 18 with TypeScript
- **UI Library**: Mantine UI 7.5
- **Routing**: React Router 6
- **State Management**: React Context API (UserModeContext)
- **Charts**: Recharts (needs installation: `npm install recharts`)
- **HTTP Client**: Axios
- **Build Tool**: Vite

## Architecture Principles

### 1. User Mode System

The application supports two user modes:
- **Ciudadano (Citizen)**: Simplified language, essential information, visual focus
- **Auditor**: Technical details, full data access, advanced metrics

Mode is managed via `UserModeContext` and persisted in localStorage.

### 2. Component Structure

```
src/
├── contexts/
│   └── UserModeContext.tsx       # Global mode management
├── components/
│   ├── shared/                   # Reusable components
│   │   ├── RiskBadge.tsx
│   │   ├── MontoDisplay.tsx
│   │   ├── ActoCard.tsx
│   │   ├── AlertCard.tsx
│   │   ├── StatsCard.tsx
│   │   ├── FilterPanel.tsx
│   │   ├── DataTable.tsx
│   │   └── ChartContainer.tsx
│   ├── mode/                     # Mode-specific wrappers
│   │   ├── ModeToggle.tsx
│   │   ├── CiudadanoView.tsx
│   │   └── AuditorView.tsx
│   └── layout/                   # Layout components
│       ├── AppShell.tsx
│       ├── MainHeader.tsx
│       └── MainNavbar.tsx
├── pages/                        # Feature pages
│   ├── alertas/
│   ├── actos/
│   ├── dashboard/
│   └── presupuesto/
├── services/
│   └── api.ts                    # API client
├── types/                        # TypeScript definitions
│   ├── alertas.ts
│   ├── actos.ts
│   ├── presupuesto.ts
│   └── metricas.ts
└── routes/
    └── index.tsx                 # Route configuration
```

### 3. Data Flow

```
API Backend (FastAPI)
    ↓
Services Layer (api.ts)
    ↓
Pages (State Management)
    ↓
Components (Props)
    ↓
UI Rendering (Conditional by Mode)
```

### 4. Scalability Features

#### Component Reusability
- All shared components accept `mode?: UserMode` prop
- Base components have no business logic
- Composition over inheritance

#### Performance Optimization
- Pagination on all list views (10-50 items per page)
- Lazy loading ready (React.lazy can be added)
- Efficient re-rendering with proper key usage

#### Extensibility
- New views follow established patterns
- Easy to add new filters
- API client easily extended with new endpoints

## Key Features

### 1. Alertas Ciudadanas (Citizen Alerts)
**Route**: `/alertas` and `/alertas/:id`

**Components**:
- `AlertasPage.tsx`: Main listing with filters and stats
- `AlertaDetailPage.tsx`: Detailed view with actions
- `AlertasFilters.tsx`: Filter panel
- `AlertasList.tsx`: Grid of alert cards
- `AlertasStats.tsx`: Statistics dashboard

**Features**:
- 15 configurable alert types
- Severity-based filtering
- Citizen-friendly action suggestions
- Real-time status updates

### 2. Actos Administrativos (Administrative Acts)
**Route**: `/actos` and `/actos/:id`

**Components**:
- `ActosPage.tsx`: Main listing
- `ActoDetailPage.tsx`: Detailed view with budget links
- `ActosFilters.tsx`: Type, organism, risk filters
- `ActosList.tsx`: Grid of act cards
- `VinculosTable.tsx`: Budget linkage table

**Features**:
- Risk classification (ALTO/MEDIO/BAJO)
- Budget program linkage with confidence scores
- Original document fragment display (auditor mode)
- Multiple matching methods

### 3. Dashboard de Métricas (Metrics Dashboard)
**Route**: `/dashboard`

**Components**:
- `DashboardPage.tsx`: Executive dashboard
- `MetricasGenerales.tsx`: 7 key stats cards
- `RiesgoChart.tsx`: Risk distribution chart
- `EjecucionChart.tsx`: Budget execution progress
- `TopOrganismos.tsx`: Top organisms by budget/risk

**Features**:
- Real-time metrics
- Visual charts (bar charts, progress bars)
- Top 5 rankings
- Aggregated statistics

### 4. Explorador de Presupuesto (Budget Explorer)
**Route**: `/presupuesto` and `/presupuesto/:id`

**Components**:
- `PresupuestoPage.tsx`: Program listing
- `ProgramaDetailPage.tsx`: Program detail with execution
- `PresupuestoFilters.tsx`: Year and organism filters
- `ProgramasList.tsx`: Program cards
- `EjecucionProgress.tsx`: Execution progress widget

**Features**:
- 1,289+ budget programs
- Execution tracking
- Historical operations table
- Budget modifications tracking

## User Experience

### Ciudadano Mode
- Simple language ("Sospechoso" instead of "Score 0.85")
- Visual indicators (colors, progress bars)
- Action-oriented ("Qué puedo hacer")
- Hide technical details

### Auditor Mode
- Technical terminology
- Full data tables
- Numeric scores and metrics
- Export capabilities (future)
- Detailed logs

## API Integration

All pages communicate with backend via `/services/api.ts`:

```typescript
// Example usage
const alertas = await getAlertas({ 
  nivel_severidad: 'ALTA',
  limite: 50 
});
```

### Backend Endpoints
- `/api/v1/alertas/` - Alerts management
- `/api/v1/actos/` - Administrative acts
- `/api/v1/presupuesto/` - Budget programs
- `/api/v1/metricas/` - System metrics

## Installation & Setup

### Dependencies Installation

```bash
cd watcher-monolith/frontend
npm install recharts  # Required for charts
```

### Running the Application

```bash
# Backend (Terminal 1)
cd watcher-monolith/backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app.main:app --reload

# Frontend (Terminal 2)
cd watcher-monolith/frontend
npm run dev
```

## Best Practices

### Component Guidelines
1. Always destructure props at function signature
2. Use TypeScript interfaces for all props
3. Handle loading and error states
4. Implement proper accessibility (ARIA labels)
5. Use semantic HTML

### State Management
1. Keep state close to where it's used
2. Lift state only when necessary
3. Use Context for truly global state
4. Avoid prop drilling with composition

### Performance
1. Use `React.memo` for expensive components
2. Implement pagination for lists
3. Debounce filter inputs
4. Lazy load routes if needed

### Testing Strategy
1. Unit tests for utility functions
2. Integration tests for API calls
3. Component tests with React Testing Library
4. E2E tests for critical flows

## Future Enhancements

### Short Term
- [ ] Add loading skeletons
- [ ] Implement error boundaries
- [ ] Add toast notifications
- [ ] Export to CSV/PDF functionality

### Medium Term
- [ ] Real-time updates with WebSockets
- [ ] Advanced search with full-text
- [ ] Saved filters and preferences
- [ ] Dark mode support

### Long Term
- [ ] Mobile app (React Native)
- [ ] Offline mode with service workers
- [ ] AI-powered insights
- [ ] Collaborative features

## Troubleshooting

### Charts Not Displaying
**Solution**: Install recharts
```bash
npm install recharts
```

### Type Errors
**Solution**: Ensure all TypeScript types are imported:
```typescript
import type { Alerta } from '../types/alertas';
```

### API Connection Issues
**Solution**: Verify backend is running on port 8000:
```bash
curl http://localhost:8000/api/v1/
```

### CORS Errors
**Solution**: Backend already configured for localhost:5173. If using different port, update `backend/app/main.py`:
```python
allow_origins=["http://localhost:YOUR_PORT"]
```

## Maintenance

### Adding a New View
1. Create page component in `src/pages/[feature]/`
2. Create sub-components in `src/pages/[feature]/components/`
3. Add route in `src/routes/index.tsx`
4. Add navigation link in `src/components/layout/MainNavbar.tsx`
5. Add API functions in `src/services/api.ts`
6. Create TypeScript types in `src/types/[feature].ts`

### Updating Styles
- Use Mantine's theme system
- Customize in `src/App.tsx` via MantineProvider
- Follow existing color patterns (red=high risk, green=low risk)

## Support

For questions or issues:
- Review this documentation
- Check the plan file: `/ui.plan.md`
- Examine existing components for patterns
- Refer to Mantine UI documentation: https://mantine.dev/

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Author**: Watcher Fiscal Team

