import { Card, Badge, Text, Group, Stack, Progress, ThemeIcon, ActionIcon } from '@mantine/core';
import { 
  IconRobot, 
  IconCircleCheck, 
  IconAlertCircle, 
  IconClock,
  IconRefresh 
} from '@tabler/icons-react';

interface AgentCardProps {
  agentType: string;
  status: 'active' | 'idle' | 'processing' | 'error';
  tasksProcessed?: number;
  currentTask?: string;
  onRefresh?: () => void;
}

const statusColors = {
  active: 'green',
  idle: 'gray',
  processing: 'blue',
  error: 'red'
};

const statusIcons = {
  active: IconCircleCheck,
  idle: IconClock,
  processing: IconClock,
  error: IconAlertCircle
};

const agentNames = {
  document_intelligence: 'Document Intelligence',
  anomaly_detection: 'Anomaly Detection',
  insight_reporting: 'Insight & Reporting',
  orchestrator: 'Orchestrator'
};

export function AgentCard({ 
  agentType, 
  status, 
  tasksProcessed = 0, 
  currentTask,
  onRefresh 
}: AgentCardProps) {
  const StatusIcon = statusIcons[status];
  const color = statusColors[status];

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Group justify="space-between" mb="xs">
        <Group>
          <ThemeIcon size="lg" radius="md" color={color} variant="light">
            <IconRobot size={20} />
          </ThemeIcon>
          <div>
            <Text fw={500}>{agentNames[agentType] || agentType}</Text>
            <Badge color={color} variant="light" size="sm">
              {status}
            </Badge>
          </div>
        </Group>
        
        {onRefresh && (
          <ActionIcon variant="subtle" onClick={onRefresh}>
            <IconRefresh size={18} />
          </ActionIcon>
        )}
      </Group>

      <Stack gap="xs">
        {currentTask && (
          <>
            <Text size="sm" c="dimmed">Current Task:</Text>
            <Text size="sm" fw={500}>{currentTask}</Text>
          </>
        )}

        <Group justify="space-between" mt="md">
          <Text size="sm" c="dimmed">
            Tasks Processed
          </Text>
          <Text size="sm" fw={500}>
            {tasksProcessed}
          </Text>
        </Group>
      </Stack>
    </Card>
  );
}





