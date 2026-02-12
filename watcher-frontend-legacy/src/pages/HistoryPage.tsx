import { useState, useEffect } from 'react';
import {
  Container,
  Title,
  Paper,
  Text,
  Table,
  Badge,
  Group,
  Button,
  Stack,
  Modal,
  Tabs,
  Select,
  ActionIcon,
  Tooltip,
  Card,
  SimpleGrid
} from '@mantine/core';
import {
  IconHistory,
  IconDownload,
  IconEye,
  IconTrash,
  IconRefresh,
  IconFilter,
  IconClock,
  IconCheck,
  IconX,
  IconPlayerPlay
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

interface Workflow {
  id: string;
  workflow_name: string;
  workflow_type: string;
  status: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  progress_percentage: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

interface WorkflowDetail {
  id: string;
  workflow_name: string;
  workflow_type: string;
  status: string;
  parameters?: any;
  results?: any;
  error_message?: string;
  total_tasks: number;
  completed_tasks: number;
  tasks: Array<{
    id: string;
    task_type: string;
    agent_type: string;
    status: string;
    result?: any;
    created_at: string;
  }>;
  logs: Array<{
    id: number;
    level: string;
    message: string;
    created_at: string;
  }>;
  created_at: string;
  completed_at?: string;
}

const API_BASE_URL = 'http://localhost:8001';

export function HistoryPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowDetail | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  useEffect(() => {
    fetchWorkflows();
  }, [statusFilter, typeFilter]);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (typeFilter) params.append('workflow_type', typeFilter);
      params.append('limit', '100');

      const response = await fetch(`${API_BASE_URL}/api/v1/workflows/history?${params}`);
      if (response.ok) {
        const data = await response.json();
        setWorkflows(data);
      }
    } catch (error) {
      console.error('Error fetching workflows:', error);
      notifications.show({
        title: 'Error',
        message: 'No se pudo cargar el historial',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  const viewDetails = async (workflowId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/workflows/history/${workflowId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedWorkflow(data);
        setDetailModalOpen(true);
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'No se pudo cargar el detalle',
        color: 'red'
      });
    }
  };

  const exportWorkflow = async (workflowId: string, format: 'json' | 'csv') => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/workflows/export/${workflowId}?format=${format}`
      );
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `workflow_${workflowId}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        notifications.show({
          title: 'Exportado',
          message: `Workflow exportado como ${format.toUpperCase()}`,
          color: 'green'
        });
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'No se pudo exportar el workflow',
        color: 'red'
      });
    }
  };

  const deleteWorkflow = async (workflowId: string) => {
    if (!confirm('¿Estás seguro de eliminar este workflow?')) return;
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/workflows/history/${workflowId}`,
        { method: 'DELETE' }
      );
      
      if (response.ok) {
        notifications.show({
          title: 'Eliminado',
          message: 'Workflow eliminado exitosamente',
          color: 'green'
        });
        fetchWorkflows();
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'No se pudo eliminar el workflow',
        color: 'red'
      });
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'green',
      in_progress: 'blue',
      failed: 'red',
      pending: 'gray',
      waiting_approval: 'yellow'
    };
    
    const icons: Record<string, any> = {
      completed: <IconCheck size={14} />,
      in_progress: <IconPlayerPlay size={14} />,
      failed: <IconX size={14} />,
      pending: <IconClock size={14} />,
      waiting_approval: <IconClock size={14} />
    };
    
    return (
      <Badge color={colors[status] || 'gray'} leftSection={icons[status]}>
        {status.replace('_', ' ')}
      </Badge>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-AR');
  };

  const getDuration = (start: string, end?: string) => {
    const startDate = new Date(start);
    const endDate = end ? new Date(end) : new Date();
    const diff = endDate.getTime() - startDate.getTime();
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <Group justify="space-between">
          <div>
            <Title order={2}>📜 Historial de Análisis</Title>
            <Text c="dimmed">Consulta y exporta todos los análisis ejecutados por agentes</Text>
          </div>
          <Button leftSection={<IconRefresh size={16} />} onClick={fetchWorkflows} loading={loading}>
            Actualizar
          </Button>
        </Group>

        {/* Filters */}
        <Paper p="md" withBorder>
          <Group>
            <IconFilter size={20} />
            <Select
              placeholder="Estado"
              data={[
                { value: '', label: 'Todos' },
                { value: 'completed', label: 'Completados' },
                { value: 'failed', label: 'Fallidos' },
                { value: 'in_progress', label: 'En progreso' },
                { value: 'pending', label: 'Pendientes' }
              ]}
              value={statusFilter}
              onChange={(value) => setStatusFilter(value || '')}
              style={{ width: 200 }}
            />
            <Select
              placeholder="Tipo"
              data={[
                { value: '', label: 'Todos' },
                { value: 'analyze_high_risk', label: 'Análisis Alto Riesgo' },
                { value: 'monthly_summary', label: 'Resumen Mensual' },
                { value: 'trend_analysis', label: 'Análisis de Tendencias' },
                { value: 'entity_search', label: 'Búsqueda de Entidades' }
              ]}
              value={typeFilter}
              onChange={(value) => setTypeFilter(value || '')}
              style={{ width: 250 }}
            />
            <Text c="dimmed" size="sm">
              {workflows.length} workflow{workflows.length !== 1 ? 's' : ''}
            </Text>
          </Group>
        </Paper>

        {/* Table */}
        <Paper withBorder>
          <Table striped highlightOnHover>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Tareas</th>
                <th>Progreso</th>
                <th>Creado</th>
                <th>Duración</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((workflow) => (
                <tr key={workflow.id}>
                  <td>
                    <Text fw={500}>{workflow.workflow_name}</Text>
                    <Text size="xs" c="dimmed">{workflow.id.slice(0, 8)}...</Text>
                  </td>
                  <td>
                    <Badge variant="light">{workflow.workflow_type}</Badge>
                  </td>
                  <td>{getStatusBadge(workflow.status)}</td>
                  <td>
                    <Text size="sm">
                      {workflow.completed_tasks}/{workflow.total_tasks}
                      {workflow.failed_tasks > 0 && (
                        <Text component="span" c="red" ml={4}>
                          ({workflow.failed_tasks} ❌)
                        </Text>
                      )}
                    </Text>
                  </td>
                  <td>
                    <Text size="sm">{workflow.progress_percentage.toFixed(0)}%</Text>
                  </td>
                  <td>
                    <Text size="xs">{formatDate(workflow.created_at)}</Text>
                  </td>
                  <td>
                    <Text size="sm">
                      {getDuration(workflow.created_at, workflow.completed_at)}
                    </Text>
                  </td>
                  <td>
                    <Group gap={4}>
                      <Tooltip label="Ver detalles">
                        <ActionIcon
                          variant="light"
                          color="blue"
                          onClick={() => viewDetails(workflow.id)}
                        >
                          <IconEye size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Exportar JSON">
                        <ActionIcon
                          variant="light"
                          color="green"
                          onClick={() => exportWorkflow(workflow.id, 'json')}
                        >
                          <IconDownload size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Eliminar">
                        <ActionIcon
                          variant="light"
                          color="red"
                          onClick={() => deleteWorkflow(workflow.id)}
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
          
          {workflows.length === 0 && (
            <Stack align="center" py="xl">
              <IconHistory size={48} style={{ opacity: 0.3 }} />
              <Text c="dimmed">No hay análisis en el historial</Text>
              <Text size="sm" c="dimmed">Ejecuta análisis desde la sección "Agentes IA"</Text>
            </Stack>
          )}
        </Paper>

        {/* Detail Modal - Custom para evitar problemas de rendering */}
        {detailModalOpen && selectedWorkflow && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              padding: '20px',
            }}
            onClick={() => setDetailModalOpen(false)}
          >
            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '8px',
                maxWidth: '1200px',
                width: '100%',
                maxHeight: '90vh',
                overflow: 'auto',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                position: 'relative',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div
                style={{
                  padding: '20px',
                  borderBottom: '1px solid #e9ecef',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  position: 'sticky',
                  top: 0,
                  backgroundColor: 'white',
                  zIndex: 1,
                }}
              >
                <Text size="lg" fw={600}>Análisis: {selectedWorkflow.workflow_name}</Text>
                <ActionIcon onClick={() => setDetailModalOpen(false)} variant="subtle">
                  <IconX size={20} />
                </ActionIcon>
              </div>

              {/* Content */}
              <div style={{ padding: '20px' }}>
            <Stack gap="md">
              {/* Summary */}
              <SimpleGrid cols={3}>
                <Card withBorder>
                  <Text size="xs" c="dimmed" mb={4}>Estado</Text>
                  {getStatusBadge(selectedWorkflow.status)}
                </Card>
                <Card withBorder>
                  <Text size="xs" c="dimmed" mb={4}>Tareas</Text>
                  <Text fw={600}>{selectedWorkflow.completed_tasks}/{selectedWorkflow.total_tasks}</Text>
                </Card>
                <Card withBorder>
                  <Text size="xs" c="dimmed" mb={4}>Duración</Text>
                  <Text fw={600}>{getDuration(selectedWorkflow.created_at, selectedWorkflow.completed_at)}</Text>
                </Card>
              </SimpleGrid>

              {/* Tabs */}
              <Tabs defaultValue="tasks">
                <Tabs.List>
                  <Tabs.Tab value="tasks">Tareas ({selectedWorkflow.tasks.length})</Tabs.Tab>
                  <Tabs.Tab value="logs">Logs ({selectedWorkflow.logs.length})</Tabs.Tab>
                  <Tabs.Tab value="results">Resultados</Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="tasks" pt="md">
                  <Stack gap="sm">
                    {selectedWorkflow.tasks.map((task) => (
                      <Paper key={task.id} p="md" withBorder>
                        <Group justify="space-between" mb="xs">
                          <Text fw={500}>{task.task_type}</Text>
                          {getStatusBadge(task.status)}
                        </Group>
                        <Text size="sm" c="dimmed">Agente: {task.agent_type}</Text>
                        {task.result && (
                          <Paper p="xs" mt="xs" style={{ backgroundColor: '#f8f9fa' }}>
                            <Text size="xs" style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                              {JSON.stringify(task.result, null, 2)}
                            </Text>
                          </Paper>
                        )}
                      </Paper>
                    ))}
                  </Stack>
                </Tabs.Panel>

                <Tabs.Panel value="logs" pt="md">
                  <Stack gap="xs">
                    {selectedWorkflow.logs.map((log) => (
                      <Group key={log.id} gap="xs">
                        <Badge size="sm" color={
                          log.level === 'error' ? 'red' : 
                          log.level === 'warning' ? 'yellow' : 
                          'blue'
                        }>
                          {log.level}
                        </Badge>
                        <Text size="sm">{log.message}</Text>
                        <Text size="xs" c="dimmed">{formatDate(log.created_at)}</Text>
                      </Group>
                    ))}
                  </Stack>
                </Tabs.Panel>

                <Tabs.Panel value="results" pt="md">
                  {selectedWorkflow.results ? (
                    <Paper p="md" style={{ backgroundColor: '#f8f9fa' }}>
                      <Text size="sm" style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                        {JSON.stringify(selectedWorkflow.results, null, 2)}
                      </Text>
                    </Paper>
                  ) : (
                    <Text c="dimmed">No hay resultados disponibles</Text>
                  )}
                </Tabs.Panel>
              </Tabs>

              {/* Export Buttons */}
              <Group>
                <Button
                  leftSection={<IconDownload size={16} />}
                  variant="light"
                  onClick={() => exportWorkflow(selectedWorkflow.id, 'json')}
                >
                  Exportar JSON
                </Button>
                <Button
                  leftSection={<IconDownload size={16} />}
                  variant="light"
                  color="green"
                  onClick={() => exportWorkflow(selectedWorkflow.id, 'csv')}
                >
                  Exportar CSV
                </Button>
              </Group>
            </Stack>
              </div>
            </div>
          </div>
        )}
      </Stack>
    </Container>
  );
}

