import { useState, useEffect } from 'react';
import { 
  Container, 
  Title, 
  SimpleGrid, 
  Paper, 
  Text, 
  Stack, 
  Group,
  Badge,
  Button,
  Timeline,
  Tabs,
  Progress,
  RingProgress,
  ThemeIcon,
  Loader,
  Card,
  Grid
} from '@mantine/core';
import { 
  IconRobot, 
  IconTimeline, 
  IconChecklist, 
  IconAlertCircle,
  IconMessageChatbot,
  IconChartBar,
  IconClock,
  IconPlayerPlay,
  IconCheck,
  IconX,
  IconRefresh
} from '@tabler/icons-react';
import { AgentCard } from '../components/agents/AgentCard';
import { AgentStatusMonitor } from '../components/agents/AgentStatusMonitor';
import { AgentChat } from '../components/agents/AgentChat';
import { InsightsPanel } from '../components/agents/InsightsPanel';
import { WorkflowActions } from '../components/agents/WorkflowActions';
import { RedFlagsMonitor } from '../components/agents/RedFlagsMonitor';

interface WorkflowSummary {
  workflow_id: string;
  workflow_name: string;
  status: string;
  progress_percentage: number;
  total_tasks: number;
  completed_tasks: number;
  awaiting_approval: number;
  created_at: string;
}

export function AgentDashboard() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    fetchWorkflows();
    
    // Polling más frecuente cuando hay workflows activos
    const hasActiveWorkflows = workflows.some(w => 
      ['in_progress', 'waiting_approval', 'pending'].includes(w.status)
    );
    const interval = setInterval(fetchWorkflows, hasActiveWorkflows ? 2000 : 5000);
    
    return () => clearInterval(interval);
  }, [workflows.length]);

  const fetchWorkflows = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/v1/workflows');
      if (!response.ok) {
        console.warn('API not available yet, workflows will load when backend is ready');
        setWorkflows([]);
        setLoading(false);
        return;
      }
      const data = await response.json();
      // Asegurarse de que data es un array
      setWorkflows(Array.isArray(data) ? data : []);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching workflows:', error);
      setWorkflows([]);
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'green',
      in_progress: 'blue',
      failed: 'red',
      waiting_approval: 'yellow',
      pending: 'gray'
    };
    return colors[status] || 'gray';
  };

  const getStatusIcon = (status: string) => {
    const icons: Record<string, any> = {
      completed: <IconCheck size={16} />,
      in_progress: <Loader size={16} />,
      failed: <IconX size={16} />,
      waiting_approval: <IconClock size={16} />,
      pending: <IconPlayerPlay size={16} />
    };
    return icons[status] || <IconPlayerPlay size={16} />;
  };

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const activeWorkflows = workflows.filter(w => 
    ['in_progress', 'waiting_approval', 'pending'].includes(w.status)
  );
  const completedWorkflows = workflows.filter(w => w.status === 'completed');
  const failedWorkflows = workflows.filter(w => w.status === 'failed');

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        <Group justify="space-between">
          <div>
            <Title order={2}>Agent Dashboard</Title>
            <Text c="dimmed">Monitor and manage your AI agents and workflows</Text>
          </div>
          <Button 
            component="a"
            href="/workflows/history"
            variant="light"
            leftSection={<IconTimeline size={16} />}
          >
            Ver Historial
          </Button>
        </Group>

        {/* Workflow Overview Stats */}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
          <Card withBorder padding="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Workflows Activos
                </Text>
                <Group align="flex-end" gap={4} mt={5}>
                  <Text size="xl" fw={700}>{activeWorkflows.length}</Text>
                  {activeWorkflows.length > 0 && <Loader size="xs" />}
                </Group>
              </div>
              <ThemeIcon size={40} radius="md" variant="light" color="blue">
                <IconPlayerPlay size={24} />
              </ThemeIcon>
            </Group>
          </Card>

          <Card withBorder padding="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Completados
                </Text>
                <Group align="flex-end" gap={4} mt={5}>
                  <Text size="xl" fw={700}>{completedWorkflows.length}</Text>
                </Group>
              </div>
              <ThemeIcon size={40} radius="md" variant="light" color="green">
                <IconCheck size={24} />
              </ThemeIcon>
            </Group>
          </Card>

          <Card withBorder padding="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Fallidos
                </Text>
                <Group align="flex-end" gap={4} mt={5}>
                  <Text size="xl" fw={700}>{failedWorkflows.length}</Text>
                </Group>
              </div>
              <ThemeIcon size={40} radius="md" variant="light" color="red">
                <IconX size={24} />
              </ThemeIcon>
            </Group>
          </Card>

          <Card withBorder padding="lg" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Última Actualización
                </Text>
                <Group align="flex-end" gap={4} mt={5}>
                  <Text size="sm" fw={500}>{getTimeAgo(lastUpdate.toISOString())}</Text>
                </Group>
              </div>
              <ThemeIcon size={40} radius="md" variant="light" color="gray">
                <IconRefresh size={24} />
              </ThemeIcon>
            </Group>
          </Card>
        </SimpleGrid>

        {/* System Health */}
        <AgentStatusMonitor />

        {/* Insights & Metrics */}
        <Paper p="md" withBorder>
          <Group mb="md">
            <IconChartBar size={24} />
            <div>
              <Title order={3}>📊 Insights & Métricas en Tiempo Real</Title>
              <Text size="sm" c="dimmed">
                Análisis de tus 1,063 documentos y 688 red flags detectadas
              </Text>
            </div>
          </Group>
          <InsightsPanel />
        </Paper>

        {/* Workflow Actions, Red Flags & Chat */}
        <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
          <WorkflowActions onWorkflowStarted={fetchWorkflows} />
          
          <RedFlagsMonitor />
          
          <div>
            <Group mb="md">
              <IconMessageChatbot size={24} />
              <div>
                <Title order={3}>💬 Chat Agent</Title>
                <Text size="sm" c="dimmed">
                  Pregunta sobre tus datos
                </Text>
              </div>
            </Group>
            <AgentChat height={420} />
          </div>
        </SimpleGrid>

        {/* Agent Cards Grid */}
        <div>
          <Title order={3} mb="md">Active Agents</Title>
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
            <AgentCard 
              agentType="document_intelligence"
              status="active"
              tasksProcessed={0}
            />
            <AgentCard 
              agentType="anomaly_detection"
              status="active"
              tasksProcessed={0}
            />
            <AgentCard 
              agentType="insight_reporting"
              status="active"
              tasksProcessed={0}
            />
          </SimpleGrid>
        </div>

        {/* Workflows Section */}
        <Paper p="md" withBorder>
          <Title order={3} mb="md">Workflows</Title>
          
          <Tabs defaultValue="active">
            <Tabs.List>
              <Tabs.Tab value="active" leftSection={<IconTimeline size={16} />}>
                Active
              </Tabs.Tab>
              <Tabs.Tab value="completed" leftSection={<IconChecklist size={16} />}>
                Completed
              </Tabs.Tab>
              <Tabs.Tab value="failed" leftSection={<IconAlertCircle size={16} />}>
                Failed
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="active" pt="md">
              <Stack gap="md">
                {activeWorkflows.length === 0 ? (
                  <Paper p="xl" withBorder style={{ textAlign: 'center' }}>
                    <IconTimeline size={48} style={{ opacity: 0.3, margin: '0 auto 16px' }} />
                    <Text c="dimmed" size="lg" fw={500}>No active workflows</Text>
                    <Text c="dimmed" size="sm" mt="xs">
                      Inicia un workflow desde las acciones rápidas arriba
                    </Text>
                  </Paper>
                ) : (
                  activeWorkflows.map((workflow) => (
                    <Card key={workflow.workflow_id} padding="lg" withBorder radius="md" shadow="sm">
                      {/* Header */}
                      <Group justify="space-between" mb="md">
                        <div style={{ flex: 1 }}>
                          <Group gap="xs" mb={4}>
                            <Text fw={600} size="lg">{workflow.workflow_name}</Text>
                            <Badge 
                              color={getStatusColor(workflow.status)} 
                              variant="light"
                              leftSection={getStatusIcon(workflow.status)}
                            >
                              {workflow.status.replace('_', ' ')}
                            </Badge>
                          </Group>
                          <Group gap="xs">
                            <Text size="xs" c="dimmed">{workflow.workflow_id}</Text>
                            <Text size="xs" c="dimmed">•</Text>
                            <Text size="xs" c="dimmed">{getTimeAgo(workflow.created_at)}</Text>
                          </Group>
                        </div>
                        
                        {/* Ring Progress */}
                        <RingProgress
                          size={80}
                          thickness={8}
                          roundCaps
                          sections={[{ 
                            value: workflow.progress_percentage, 
                            color: getStatusColor(workflow.status) 
                          }]}
                          label={
                            <Text size="xs" ta="center" fw={700}>
                              {workflow.progress_percentage.toFixed(0)}%
                            </Text>
                          }
                        />
                      </Group>

                      {/* Progress Bar */}
                      <Progress 
                        value={workflow.progress_percentage} 
                        color={getStatusColor(workflow.status)}
                        size="lg"
                        radius="md"
                        animated={workflow.status === 'in_progress'}
                        mb="md"
                      />
                      
                      {/* Stats */}
                      <Grid gutter="md" mb="md">
                        <Grid.Col span={4}>
                          <Paper p="xs" withBorder>
                            <Text size="xs" c="dimmed" mb={4}>Total Tasks</Text>
                            <Text fw={700} size="lg">{workflow.total_tasks}</Text>
                          </Paper>
                        </Grid.Col>
                        <Grid.Col span={4}>
                          <Paper p="xs" withBorder style={{ borderColor: 'var(--mantine-color-green-5)' }}>
                            <Text size="xs" c="dimmed" mb={4}>Completed</Text>
                            <Text fw={700} size="lg" c="green">{workflow.completed_tasks}</Text>
                          </Paper>
                        </Grid.Col>
                        <Grid.Col span={4}>
                          <Paper p="xs" withBorder style={{ borderColor: workflow.awaiting_approval > 0 ? 'var(--mantine-color-yellow-5)' : undefined }}>
                            <Text size="xs" c="dimmed" mb={4}>Pending</Text>
                            <Text fw={700} size="lg" c={workflow.awaiting_approval > 0 ? 'yellow' : undefined}>
                              {workflow.total_tasks - workflow.completed_tasks}
                            </Text>
                          </Paper>
                        </Grid.Col>
                      </Grid>

                      {/* Awaiting Approval Alert */}
                      {workflow.awaiting_approval > 0 && (
                        <Paper p="md" withBorder style={{ backgroundColor: 'var(--mantine-color-yellow-0)', borderColor: 'var(--mantine-color-yellow-5)' }} mb="md">
                          <Group>
                            <ThemeIcon color="yellow" variant="light">
                              <IconClock size={20} />
                            </ThemeIcon>
                            <div style={{ flex: 1 }}>
                              <Text size="sm" fw={600}>Esperando Aprobación</Text>
                              <Text size="xs" c="dimmed">
                                {workflow.awaiting_approval} tarea{workflow.awaiting_approval > 1 ? 's' : ''} requiere{workflow.awaiting_approval === 1 ? '' : 'n'} tu aprobación
                              </Text>
                            </div>
                            <Button 
                              size="xs" 
                              color="yellow"
                              component="a"
                              href={`/workflows/${workflow.workflow_id}/approve`}
                            >
                              Revisar
                            </Button>
                          </Group>
                        </Paper>
                      )}

                      {/* Actions */}
                      <Group mt="md">
                        <Button 
                          size="xs" 
                          variant="light"
                          leftSection={<IconTimeline size={14} />}
                          component="a"
                          href={`/workflows/${workflow.workflow_id}`}
                        >
                          Ver Detalles
                        </Button>
                        <Button 
                          size="xs" 
                          variant="subtle"
                          onClick={fetchWorkflows}
                        >
                          Actualizar
                        </Button>
                      </Group>
                    </Card>
                  ))
                )}
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="completed" pt="md">
              <Stack gap="md">
                {completedWorkflows.length === 0 ? (
                  <Paper p="xl" withBorder style={{ textAlign: 'center' }}>
                    <IconChecklist size={48} style={{ opacity: 0.3, margin: '0 auto 16px' }} />
                    <Text c="dimmed" size="lg" fw={500}>No completed workflows yet</Text>
                  </Paper>
                ) : (
                  completedWorkflows.map((workflow) => (
                    <Card key={workflow.workflow_id} padding="md" withBorder>
                      <Group justify="space-between">
                        <div style={{ flex: 1 }}>
                          <Group gap="xs" mb={4}>
                            <IconCheck size={20} color="green" />
                            <Text fw={600}>{workflow.workflow_name}</Text>
                          </Group>
                          <Text size="xs" c="dimmed">
                            Completado {getTimeAgo(workflow.created_at)} • {workflow.total_tasks} tareas
                          </Text>
                        </div>
                        <Badge color="green" variant="light" leftSection={<IconCheck size={14} />}>
                          Completed
                        </Badge>
                      </Group>
                    </Card>
                  ))
                )}
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="failed" pt="md">
              <Stack gap="md">
                {failedWorkflows.length === 0 ? (
                  <Paper p="xl" withBorder style={{ textAlign: 'center' }}>
                    <IconAlertCircle size={48} style={{ opacity: 0.3, margin: '0 auto 16px' }} />
                    <Text c="dimmed" size="lg" fw={500}>No failed workflows</Text>
                    <Text c="dimmed" size="sm" mt="xs">
                      ¡Todo funciona correctamente! 🎉
                    </Text>
                  </Paper>
                ) : (
                  failedWorkflows.map((workflow) => (
                    <Card key={workflow.workflow_id} padding="md" withBorder style={{ borderColor: 'var(--mantine-color-red-5)' }}>
                      <Group justify="space-between">
                        <div style={{ flex: 1 }}>
                          <Group gap="xs" mb={4}>
                            <IconX size={20} color="red" />
                            <Text fw={600}>{workflow.workflow_name}</Text>
                          </Group>
                          <Text size="xs" c="dimmed">
                            Falló {getTimeAgo(workflow.created_at)} • {workflow.workflow_id}
                          </Text>
                        </div>
                        <Group>
                          <Badge color="red" variant="light" leftSection={<IconX size={14} />}>
                            Failed
                          </Badge>
                          <Button size="xs" variant="light" color="red">
                            Ver Logs
                          </Button>
                        </Group>
                      </Group>
                    </Card>
                  ))
                )}
              </Stack>
            </Tabs.Panel>
          </Tabs>
        </Paper>
      </Stack>
    </Container>
  );
}

