import { Card, Title, Text, Stack } from '@mantine/core';
import { ReactNode } from 'react';

interface ChartContainerProps {
  title: string;
  description?: string;
  children: ReactNode;
}

export function ChartContainer({ title, description, children }: ChartContainerProps) {
  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="md">
        <div>
          <Title order={4} mb="xs">{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        {children}
      </Stack>
    </Card>
  );
}

