import { useState } from 'react';
import {
  Indicator,
  ActionIcon,
  Popover,
  Stack,
  Text,
  Progress,
  Badge,
  Group,
  Button,
  Paper,
  ScrollArea,
  Tooltip
} from '@mantine/core';
import {
  IconPlayerPlay,
  IconCheck,
  IconX,
  IconClock,
  IconChevronDown,
  IconTrash
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useBackgroundTasks } from '../../services/BackgroundTaskManager';

export function TaskIndicator() {
  const [opened, setOpened] = useState(false);
  const navigate = useNavigate();
  const { tasks, activeTasks, clearCompleted } = useBackgroundTasks();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <IconCheck size={14} color="green" />;
      case 'failed':
        return <IconX size={14} color="red" />;
      case 'in_progress':
        return <IconPlayerPlay size={14} color="blue" />;
      default:
        return <IconClock size={14} color="gray" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
      case 'in_progress':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const formatDuration = (startDate: Date, endDate?: Date) => {
    const end = endDate || new Date();
    const diff = end.getTime() - startDate.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  if (tasks.length === 0) {
    return null;
  }

  return (
    <Popover
      width={400}
      position="bottom-end"
      opened={opened}
      onChange={setOpened}
    >
      <Popover.Target>
        <Tooltip label={`${activeTasks.length} tarea${activeTasks.length !== 1 ? 's' : ''} activa${activeTasks.length !== 1 ? 's' : ''}`}>
          <Indicator
            inline
            size={16}
            offset={4}
            position="top-end"
            color={activeTasks.length > 0 ? 'blue' : 'gray'}
            label={activeTasks.length}
            disabled={activeTasks.length === 0}
          >
            <ActionIcon
              variant={activeTasks.length > 0 ? 'light' : 'subtle'}
              color={activeTasks.length > 0 ? 'blue' : 'gray'}
              onClick={() => setOpened(!opened)}
              size="lg"
            >
              <IconPlayerPlay size={18} />
            </ActionIcon>
          </Indicator>
        </Tooltip>
      </Popover.Target>

      <Popover.Dropdown p={0}>
        <Stack gap={0}>
          {/* Header */}
          <Group justify="space-between" p="md" style={{ borderBottom: '1px solid #e9ecef' }}>
            <Text fw={600}>⚙️ Tareas Activas</Text>
            <Group gap="xs">
              {tasks.some(t => t.status === 'completed' || t.status === 'failed') && (
                <ActionIcon
                  size="sm"
                  variant="subtle"
                  onClick={clearCompleted}
                  title="Limpiar completadas"
                >
                  <IconTrash size={14} />
                </ActionIcon>
              )}
              <ActionIcon
                size="sm"
                variant="subtle"
                onClick={() => setOpened(false)}
              >
                <IconChevronDown size={14} />
              </ActionIcon>
            </Group>
          </Group>

          {/* Tasks List */}
          <ScrollArea style={{ maxHeight: 400 }}>
            <Stack gap="xs" p="md">
              {tasks.length === 0 ? (
                <Text c="dimmed" ta="center" py="xl">
                  No hay tareas activas
                </Text>
              ) : (
                tasks.map((task) => (
                  <Paper key={task.id} p="sm" withBorder>
                    <Stack gap="xs">
                      <Group justify="space-between" wrap="nowrap">
                        <Group gap="xs" style={{ flex: 1, minWidth: 0 }}>
                          {getStatusIcon(task.status)}
                          <Text size="sm" fw={500} style={{ flex: 1 }} truncate>
                            {task.workflow_name}
                          </Text>
                        </Group>
                        <Badge size="xs" color={getStatusColor(task.status)}>
                          {task.status}
                        </Badge>
                      </Group>

                      {task.status === 'in_progress' && (
                        <>
                          <Progress
                            value={task.progress}
                            size="sm"
                            animated
                            color="blue"
                          />
                          <Group justify="space-between">
                            <Text size="xs" c="dimmed">
                              {task.completed_tasks}/{task.total_tasks} tareas
                            </Text>
                            <Text size="xs" c="dimmed">
                              {task.progress.toFixed(0)}%
                            </Text>
                          </Group>
                        </>
                      )}

                      {task.status === 'completed' && (
                        <Text size="xs" c="green">
                          ✓ Completado en {formatDuration(task.started_at, task.completed_at)}
                        </Text>
                      )}

                      {task.status === 'failed' && task.error_message && (
                        <Text size="xs" c="red">
                          ✗ Error: {task.error_message}
                        </Text>
                      )}

                      {task.status !== 'in_progress' && (
                        <Text size="xs" c="dimmed">
                          Duración: {formatDuration(task.started_at, task.completed_at)}
                        </Text>
                      )}
                    </Stack>
                  </Paper>
                ))
              )}
            </Stack>
          </ScrollArea>

          {/* Footer */}
          {tasks.length > 0 && (
            <Group justify="space-between" p="md" style={{ borderTop: '1px solid #e9ecef' }}>
              <Text size="sm" c="dimmed">
                {activeTasks.length} activa{activeTasks.length !== 1 ? 's' : ''} de {tasks.length}
              </Text>
              <Button
                size="xs"
                variant="light"
                onClick={() => {
                  navigate('/history');
                  setOpened(false);
                }}
              >
                Ver Historial
              </Button>
            </Group>
          )}
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
}


