import { Card, Stack, Group, Button, Title } from '@mantine/core';
import { IconFilterOff } from '@tabler/icons-react';
import { ReactNode } from 'react';

interface FilterPanelProps {
  children: ReactNode;
  onReset: () => void;
  title?: string;
}

export function FilterPanel({ children, onReset, title = 'Filtros' }: FilterPanelProps) {
  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={4}>{title}</Title>
          <Button 
            variant="subtle" 
            size="xs"
            leftSection={<IconFilterOff size="1rem" />}
            onClick={onReset}
          >
            Limpiar
          </Button>
        </Group>
        {children}
      </Stack>
    </Card>
  );
}

