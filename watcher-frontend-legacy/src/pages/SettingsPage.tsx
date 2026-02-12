import { useState } from 'react';
import {
  Container,
  Title,
  Tabs,
  Stack,
  Text,
  Paper,
  Group,
  TextInput,
  Alert,
  Badge
} from '@mantine/core';
import {
  IconRobot,
  IconKey,
  IconInfoCircle
} from '@tabler/icons-react';

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<string | null>('agents');

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>⚙️ Configuración del Sistema</Title>
          <Text c="dimmed">Gestiona la configuración de agentes IA y API keys</Text>
        </div>

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="agents" leftSection={<IconRobot size={16} />}>
              Agentes IA
            </Tabs.Tab>
            <Tabs.Tab value="api" leftSection={<IconKey size={16} />}>
              API Keys
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="agents" pt="xl">
            <Stack gap="md">
              <Alert icon={<IconInfoCircle size={16} />} color="blue">
                Configuración de agentes IA (próximamente)
              </Alert>
              
              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text fw={500}>🤖 Document Intelligence Agent</Text>
                    <Badge color="green">Activo</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    Extracción inteligente de información de documentos
                  </Text>
                </Stack>
              </Paper>

              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text fw={500}>🔍 Anomaly Detection Agent</Text>
                    <Badge color="green">Activo</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    Detección de anomalías y red flags
                  </Text>
                </Stack>
              </Paper>

              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text fw={500}>💡 Insight & Reporting Agent</Text>
                    <Badge color="green">Activo</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    Generación de insights y reportes inteligentes
                  </Text>
                </Stack>
              </Paper>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="api" pt="xl">
            <Stack gap="md">
              <Alert icon={<IconInfoCircle size={16} />} color="blue">
                Gestiona las API keys para servicios externos
              </Alert>

              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Text fw={500}>OpenAI API Key</Text>
                  <TextInput
                    placeholder="sk-..."
                    type="password"
                    description="Necesaria para funciones de IA avanzadas"
                  />
                  <Text size="xs" c="dimmed">
                    ℹ️ Esta key se configura en el archivo .env del backend
                  </Text>
                </Stack>
              </Paper>
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}

