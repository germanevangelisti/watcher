import { Box, Title, Group, Divider } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import { TaskIndicator } from './TaskIndicator';
import SyncStatusWidget from '../sync/SyncStatusWidget';

export function MainHeader() {
  const navigate = useNavigate();

  const handleSyncClick = () => {
    navigate('/settings');
  };

  return (
    <Box p="xs">
      <Group justify="space-between">
        <Title order={2}>🏠 Watcher System</Title>
        <Group gap="md">
          <SyncStatusWidget onClick={handleSyncClick} />
          <Divider orientation="vertical" />
          <TaskIndicator />
        </Group>
      </Group>
    </Box>
  );
}