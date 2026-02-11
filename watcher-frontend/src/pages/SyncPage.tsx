import { Container, Title, Text, Stack } from '@mantine/core';
import SyncDashboard from '../components/sync/SyncDashboard';

export function SyncPage() {
  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>🔄 Sincronización Automática</Title>
          <Text c="dimmed">
            Configura la sincronización automática de boletines desde el último procesado hasta hoy
          </Text>
        </div>

        <SyncDashboard />
      </Stack>
    </Container>
  );
}
