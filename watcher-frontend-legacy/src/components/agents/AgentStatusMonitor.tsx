import { useState, useEffect } from 'react';
import { SimpleGrid, Paper, Text, Group, Stack, Badge, RingProgress, ThemeIcon } from '@mantine/core';
import { IconActivity, IconAlertTriangle, IconCircleCheck } from '@tabler/icons-react';

interface AgentHealthData {
  system_status: string;
  agents: Array<{
    agent_type: string;
    status: string;
    is_available: boolean;
    tasks_processed: number;
  }>;
  active_workflows: number;
  total_tasks_completed: number;
}

export function AgentStatusMonitor() {
  const [health, setHealth] = useState<AgentHealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000); // Actualizar cada 5 segundos
    return () => clearInterval(interval);
  }, []);

  const fetchHealth = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/v1/agents/health');
      if (!response.ok) {
        console.warn('Agents API not available yet');
        setLoading(false);
        return;
      }
      const data = await response.json();
      setHealth(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching health:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return <Text>Loading agent health...</Text>;
  }

  if (!health) {
    return (
      <Paper p="md" withBorder>
        <Stack gap="md">
          <Text c="dimmed" ta="center">
            Agents API not available. Make sure the backend is running with the latest code.
          </Text>
          <Text size="sm" c="dimmed" ta="center">
            Restart the backend: uvicorn app.main:app --reload --port 8001
          </Text>
        </Stack>
      </Paper>
    );
  }

  const healthPercentage = health.system_status === 'healthy' ? 100 : 50;
  const healthColor = health.system_status === 'healthy' ? 'green' : 'yellow';

  return (
    <Paper p="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between">
          <Text size="lg" fw={600}>System Health</Text>
          <Badge 
            color={healthColor} 
            variant="light" 
            size="lg"
            leftSection={
              <ThemeIcon size="sm" color={healthColor} variant="transparent">
                {health.system_status === 'healthy' ? (
                  <IconCircleCheck size={14} />
                ) : (
                  <IconAlertTriangle size={14} />
                )}
              </ThemeIcon>
            }
          >
            {health.system_status}
          </Badge>
        </Group>

        <SimpleGrid cols={3}>
          <Paper p="sm" withBorder>
            <Stack gap="xs" align="center">
              <RingProgress
                size={80}
                thickness={8}
                sections={[{ value: healthPercentage, color: healthColor }]}
                label={
                  <ThemeIcon color={healthColor} variant="light" size="lg" radius="xl">
                    <IconActivity size={18} />
                  </ThemeIcon>
                }
              />
              <Text size="sm" fw={500}>Active Agents</Text>
              <Text size="xl" fw={700}>{health.agents.length}</Text>
            </Stack>
          </Paper>

          <Paper p="sm" withBorder>
            <Stack gap="xs" align="center">
              <RingProgress
                size={80}
                thickness={8}
                sections={[{ value: health.active_workflows > 0 ? 100 : 0, color: 'blue' }]}
                label={
                  <ThemeIcon color="blue" variant="light" size="lg" radius="xl">
                    <IconActivity size={18} />
                  </ThemeIcon>
                }
              />
              <Text size="sm" fw={500}>Active Workflows</Text>
              <Text size="xl" fw={700}>{health.active_workflows}</Text>
            </Stack>
          </Paper>

          <Paper p="sm" withBorder>
            <Stack gap="xs" align="center">
              <RingProgress
                size={80}
                thickness={8}
                sections={[{ value: 100, color: 'teal' }]}
                label={
                  <ThemeIcon color="teal" variant="light" size="lg" radius="xl">
                    <IconCircleCheck size={18} />
                  </ThemeIcon>
                }
              />
              <Text size="sm" fw={500}>Tasks Completed</Text>
              <Text size="xl" fw={700}>{health.total_tasks_completed}</Text>
            </Stack>
          </Paper>
        </SimpleGrid>

        <Stack gap="xs">
          <Text size="sm" fw={600}>Agent Status:</Text>
          {health.agents.map((agent) => (
            <Group key={agent.agent_type} justify="space-between">
              <Text size="sm">{agent.agent_type}</Text>
              <Badge 
                color={agent.is_available ? 'green' : 'red'} 
                variant="light"
              >
                {agent.status}
              </Badge>
            </Group>
          ))}
        </Stack>
      </Stack>
    </Paper>
  );
}

