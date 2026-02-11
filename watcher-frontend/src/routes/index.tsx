import { Routes, Route, Navigate } from 'react-router-dom';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { AgentDashboard } from '../pages/AgentDashboard';
import { HistoryPage } from '../pages/HistoryPage';
import { AlertasPage } from '../pages/alertas/AlertasPage';
import { AlertaDetailPage } from '../pages/alertas/AlertaDetailPage';
import { DocumentosPage } from '../pages/DocumentosPage';
import { ActoDetailPage } from '../pages/actos/ActoDetailPage';
import { PresupuestoPage } from '../pages/presupuesto/PresupuestoPage';
import { ProgramaDetailPage } from '../pages/presupuesto/ProgramaDetailPage';
import { SettingsPage } from '../pages/SettingsPage';
import JurisdiccionesPage from '../pages/JurisdiccionesPage';
import JurisdiccionDetailPage from '../pages/JurisdiccionDetailPage';
import WizardPage from '../pages/WizardPage';
import { SyncPage } from '../pages/SyncPage';
import { DownloaderPage } from '../pages/DownloaderPage';
import { CalendarPage } from '../pages/CalendarPage';
import SearchPage from '../pages/SearchPage';
import KnowledgeGraphPage from '../pages/KnowledgeGraphPage';
import { CompliancePage } from '../pages/CompliancePage';
import { MencionesPage } from '../pages/MencionesPage';

export function AppRoutes() {
  return (
    <Routes>
      {/* Dashboard Principal */}
      <Route path="/" element={<DashboardPage />} />
      <Route path="/dashboard" element={<Navigate to="/" replace />} />
      
      {/* Asistente de Procesamiento */}
      <Route path="/wizard" element={<WizardPage />} />
      
      {/* Agentes IA */}
      <Route path="/agents" element={<AgentDashboard />} />
      
      {/* Búsqueda Semántica */}
      <Route path="/search" element={<SearchPage />} />
      
      {/* Grafo de Conocimiento */}
      <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
      
      {/* Compliance Fiscal */}
      <Route path="/compliance" element={<CompliancePage />} />
      
      {/* Menciones Jurisdiccionales */}
      <Route path="/menciones" element={<MencionesPage />} />
      
      {/* Historial */}
      <Route path="/history" element={<HistoryPage />} />
      
      {/* Alertas */}
      <Route path="/alertas" element={<AlertasPage />} />
      <Route path="/alertas/:id" element={<AlertaDetailPage />} />
      
      {/* Jurisdicciones */}
      <Route path="/jurisdicciones" element={<JurisdiccionesPage />} />
      <Route path="/jurisdicciones/:id" element={<JurisdiccionDetailPage />} />
      
      {/* Documentos (Boletines + Actos) */}
      <Route path="/documentos" element={<DocumentosPage />} />
      <Route path="/documentos/actos/:id" element={<ActoDetailPage />} />
      <Route path="/documents/:id" element={<DocumentosPage />} />
      
      {/* Presupuesto */}
      <Route path="/presupuesto" element={<PresupuestoPage />} />
      <Route path="/presupuesto/:id" element={<ProgramaDetailPage />} />
      
      {/* Gestión */}
      <Route path="/sync" element={<SyncPage />} />
      <Route path="/downloader" element={<DownloaderPage />} />
      <Route path="/calendar" element={<CalendarPage />} />
      
      {/* Configuración */}
      <Route path="/settings" element={<SettingsPage />} />
      
      {/* Redirects de rutas viejas */}
      <Route path="/boletines" element={<Navigate to="/documentos" replace />} />
      <Route path="/actos" element={<Navigate to="/documentos" replace />} />
      <Route path="/actos/:id" element={<Navigate to="/documentos/actos/:id" replace />} />
      <Route path="/analyzer" element={<Navigate to="/agents" replace />} />
      <Route path="/dslab" element={<Navigate to="/settings" replace />} />
      <Route path="/dslab/analysis" element={<Navigate to="/agents" replace />} />
      <Route path="/dslab/results" element={<Navigate to="/history" replace />} />
      <Route path="/dslab/results/:executionId" element={<Navigate to="/history" replace />} />
      <Route path="/workflows/history" element={<Navigate to="/history" replace />} />
      <Route path="/results" element={<Navigate to="/history" replace />} />
    </Routes>
  );
}
