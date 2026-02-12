import { createRouter, createRoute, createRootRoute, redirect } from "@tanstack/react-router"
import { AppShell } from "./components/layout/app-shell"
import { DashboardPage } from "./pages/dashboard"
import { DocumentosHub } from "./pages/documentos"
import { BoletinDetail } from "./pages/documentos/boletin-detail"
import { SearchPage } from "./pages/conocimiento/search"
import { GraphPage } from "./pages/conocimiento/graph"
import { AnalisisHub } from "./pages/analisis"
import { AgentsDashboard } from "./pages/analisis/agents-dashboard"
import AlertasPage from "./pages/analisis/alertas"
import AlertaDetailPage from "./pages/analisis/alerta-detail"
import { PipelineStatusPage } from "./pages/analisis/pipeline-status"
import { PipelineWorkflowPage } from "./pages/pipeline"

// Root route with AppShell layout
const rootRoute = createRootRoute({
  component: () => {
    const router = useRouter()
    const currentPath = router.state.location.pathname

    return (
      <AppShell 
        currentPath={currentPath}
        onNavigate={(path) => router.navigate({ to: path })}
      >
        <Outlet />
      </AppShell>
    )
  },
})

// Dashboard route
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DashboardPage,
})

// Documentos routes
const documentosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/documentos",
  component: DocumentosHub,
})

const boletinDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/documentos/$id",
  component: BoletinDetail,
})

// Conocimiento routes
const conocimientoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/conocimiento",
  beforeLoad: () => {
    throw redirect({ to: "/conocimiento/busqueda" })
  },
})

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/conocimiento/busqueda",
  component: SearchPage,
})

const graphRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/conocimiento/grafo",
  component: GraphPage,
})

// Análisis routes
const analisisRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analisis",
  component: AnalisisHub,
})

const agentsDashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analisis/agentes",
  component: AgentsDashboard,
})

const alertasRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analisis/alertas",
  component: AlertasPage,
})

const alertaDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analisis/alertas/$alertaId",
  component: AlertaDetailPage,
})

const pipelineStatusRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analisis/pipeline",
  component: PipelineStatusPage,
})

// Pipeline workflow route (top-level)
const pipelineWorkflowRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pipeline",
  component: PipelineWorkflowPage,
})

// Create route tree
const routeTree = rootRoute.addChildren([
  indexRoute,
  documentosRoute,
  boletinDetailRoute,
  conocimientoRoute,
  searchRoute,
  graphRoute,
  analisisRoute,
  agentsDashboardRoute,
  alertasRoute,
  alertaDetailRoute,
  pipelineStatusRoute,
  pipelineWorkflowRoute,
])

// Create router
export const router = createRouter({ routeTree })

// Register router for type safety
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

// Required imports for AppShell integration
import { Outlet, useRouter } from "@tanstack/react-router"
