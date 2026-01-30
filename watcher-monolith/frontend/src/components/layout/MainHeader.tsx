import { Box, Title, Group } from '@mantine/core';
import { TaskIndicator } from './TaskIndicator';

export function MainHeader() {
  return (
    <Box p="xs">
      <Group justify="space-between">
        <Title order={2}>🏠 Watcher System</Title>
        <TaskIndicator />
      </Group>
    </Box>
  );
}