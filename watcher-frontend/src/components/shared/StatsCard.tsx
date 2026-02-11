import { Card, Text, Group, Stack } from '@mantine/core';
import type { Icon } from '@tabler/icons-react';
import type { ReactNode } from 'react';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: Icon;
  color?: string;
  description?: string | ReactNode;
  trend?: {
    value: number;
    label: string;
  };
}

export function StatsCard({ 
  title, 
  value, 
  icon: Icon, 
  color = 'blue',
  description,
  trend 
}: StatsCardProps) {
  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="xs">
        <Group justify="space-between">
          <Text size="sm" c="dimmed" tt="uppercase" fw={700}>
            {title}
          </Text>
          <Icon size="1.5rem" style={{ color: `var(--mantine-color-${color}-6)` }} />
        </Group>

        <Text size="xl" fw={700}>
          {value}
        </Text>

        {description && (
          typeof description === 'string' ? (
            <Text size="xs" c="dimmed">
              {description}
            </Text>
          ) : (
            <div>{description}</div>
          )
        )}

        {trend && (
          <Group gap="xs">
            <Text 
              size="xs" 
              c={trend.value > 0 ? 'green' : trend.value < 0 ? 'red' : 'dimmed'}
              fw={600}
            >
              {trend.value > 0 ? '↑' : trend.value < 0 ? '↓' : '='} {Math.abs(trend.value)}%
            </Text>
            <Text size="xs" c="dimmed">
              {trend.label}
            </Text>
          </Group>
        )}
      </Stack>
    </Card>
  );
}

