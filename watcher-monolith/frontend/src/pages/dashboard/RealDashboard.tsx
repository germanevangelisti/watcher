import { useEffect, useState } from 'react';
import {
  Container,
  Title,
  Text,
  Stack,
  Grid,
  Card,
  Group,
  Badge,
  RingProgress,
  Loader,
  Alert,
  ThemeIcon,
  Table,
  ScrollArea,
  Divider,
  NumberFormatter
} from '@mantine/core';
import {
  IconFile,
  IconChecks,
  IconClock,
  IconAlertTriangle,
  IconChartBar,
  IconCash,
  IconSettings,
  IconShieldCheck
} from '@tabler/icons-react';
import { getDashboardStats, getRecentRedFlags } from '../../services/api';

interface DashboardStats {
  summary: {
    total_documents: number;
    analyzed_documents: number;
    pending_documents: number;
    total_executions: number;
    completed_executions: number;
    total_red_flags: number;
    avg_transparency_score: number;
    total_amount_detected: number;
    active_configs: number;
  };
  red_flags: {
    by_severity: {
      critical: number;
      high: number;
      medium: number;
      low: number;
    };
    top_types: Array<{ type: string; count: number }>;
  };
  risk_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  documents_by_month: Array<{
    period: string;
    count: number;
    year: number;
    month: number;
  }>;
}

export function RealDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentFlags, setRecentFlags] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, flagsData] = await Promise.all([
        getDashboardStats(),
        getRecentRedFlags(10)
      ]);
      setStats(statsData);
      setRecentFlags(flagsData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container size="xl" py="xl">
        <Stack align="center" gap="md">
          <Loader size="lg" />
          <Text>Cargando datos del sistema...</Text>
        </Stack>
      </Container>
    );
  }

  if (error || !stats) {
    return (
      <Container size="xl" py="xl">
        <Alert color="red" title="Error">
          {error || 'No se pudieron cargar las estadísticas'}
        </Alert>
      </Container>
    );
  }

  const { summary, red_flags, risk_distribution, documents_by_month } = stats;

  // Calculate percentages
  const analyzedPercentage = summary.total_documents > 0
    ? (summary.analyzed_documents / summary.total_documents) * 100
    : 0;

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'red';
      case 'medium':
        return 'yellow';
      case 'low':
        return 'green';
      default:
        return 'gray';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'red';
      case 'high':
        return 'orange';
      case 'medium':
        return 'yellow';
      case 'low':
        return 'blue';
      default:
        return 'gray';
    }
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between">
          <div>
            <Title order={2}>Dashboard - Watcher DS Lab</Title>
            <Text c="dimmed" size="sm">
              Análisis de Boletines Oficiales de Córdoba
            </Text>
          </div>
          <Badge size="lg" variant="light" color="blue">
            Sistema en Producción
          </Badge>
        </Group>

        {/* Main Stats Cards */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Documentos Totales
                  </Text>
                  <ThemeIcon variant="light" color="blue">
                    <IconFile size={18} />
                  </ThemeIcon>
                </Group>
                <Text size="2rem" fw={700}>
                  <NumberFormatter value={summary.total_documents} thousandSeparator="," />
                </Text>
                <Text size="xs" c="dimmed">
                  Boletines registrados
                </Text>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Docs Analizados
                  </Text>
                  <ThemeIcon variant="light" color="green">
                    <IconChecks size={18} />
                  </ThemeIcon>
                </Group>
                <Text size="2rem" fw={700}>
                  <NumberFormatter value={summary.analyzed_documents} thousandSeparator="," />
                </Text>
                <Badge size="sm" variant="light" color="green">
                  {analyzedPercentage.toFixed(1)}% del total
                </Badge>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Red Flags
                  </Text>
                  <ThemeIcon variant="light" color="orange">
                    <IconAlertTriangle size={18} />
                  </ThemeIcon>
                </Group>
                <Text size="2rem" fw={700}>
                  <NumberFormatter value={summary.total_red_flags} thousandSeparator="," />
                </Text>
                <Text size="xs" c="dimmed">
                  Problemas detectados
                </Text>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Transparencia
                  </Text>
                  <ThemeIcon variant="light" color="teal">
                    <IconShieldCheck size={18} />
                  </ThemeIcon>
                </Group>
                <Text size="2rem" fw={700}>
                  {summary.avg_transparency_score.toFixed(1)}
                </Text>
                <Text size="xs" c="dimmed">
                  Score promedio / 100
                </Text>
              </Stack>
            </Card>
          </Grid.Col>
        </Grid>

        {/* Secondary Stats */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Group>
                  <ThemeIcon variant="light" color="cyan">
                    <IconCash size={18} />
                  </ThemeIcon>
                  <Text fw={500}>Montos Detectados</Text>
                </Group>
                <Text size="xl" fw={700}>
                  <NumberFormatter
                    value={summary.total_amount_detected}
                    thousandSeparator="."
                    decimalSeparator=","
                    prefix="$ "
                    suffix=" ARS"
                  />
                </Text>
                <Text size="xs" c="dimmed">
                  Total en operaciones de alto monto
                </Text>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 4 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Group>
                  <ThemeIcon variant="light" color="violet">
                    <IconChartBar size={18} />
                  </ThemeIcon>
                  <Text fw={500}>Ejecuciones</Text>
                </Group>
                <Text size="xl" fw={700}>
                  {summary.completed_executions} / {summary.total_executions}
                </Text>
                <Text size="xs" c="dimmed">
                  Análisis completados
                </Text>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 4 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Group>
                  <ThemeIcon variant="light" color="indigo">
                    <IconSettings size={18} />
                  </ThemeIcon>
                  <Text fw={500}>Configuraciones</Text>
                </Group>
                <Text size="xl" fw={700}>
                  {summary.active_configs}
                </Text>
                <Text size="xs" c="dimmed">
                  Modelos activos
                </Text>
              </Stack>
            </Card>
          </Grid.Col>
        </Grid>

        {/* Risk Distribution & Red Flags */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Text fw={500} size="lg">
                  Distribución de Riesgo
                </Text>
                <Divider />
                <Group justify="center" gap="xl">
                  <Stack align="center" gap="xs">
                    <RingProgress
                      size={120}
                      thickness={12}
                      sections={[
                        {
                          value: risk_distribution.high > 0
                            ? (risk_distribution.high /
                                (risk_distribution.high +
                                  risk_distribution.medium +
                                  risk_distribution.low)) *
                              100
                            : 0,
                          color: 'red'
                        }
                      ]}
                      label={
                        <Text ta="center" fw={700} size="xl">
                          {risk_distribution.high}
                        </Text>
                      }
                    />
                    <Badge color="red">ALTO</Badge>
                  </Stack>

                  <Stack align="center" gap="xs">
                    <RingProgress
                      size={120}
                      thickness={12}
                      sections={[
                        {
                          value: risk_distribution.medium > 0
                            ? (risk_distribution.medium /
                                (risk_distribution.high +
                                  risk_distribution.medium +
                                  risk_distribution.low)) *
                              100
                            : 0,
                          color: 'yellow'
                        }
                      ]}
                      label={
                        <Text ta="center" fw={700} size="xl">
                          {risk_distribution.medium}
                        </Text>
                      }
                    />
                    <Badge color="yellow">MEDIO</Badge>
                  </Stack>

                  <Stack align="center" gap="xs">
                    <RingProgress
                      size={120}
                      thickness={12}
                      sections={[
                        {
                          value: risk_distribution.low > 0
                            ? (risk_distribution.low /
                                (risk_distribution.high +
                                  risk_distribution.medium +
                                  risk_distribution.low)) *
                              100
                            : 0,
                          color: 'green'
                        }
                      ]}
                      label={
                        <Text ta="center" fw={700} size="xl">
                          {risk_distribution.low}
                        </Text>
                      }
                    />
                    <Badge color="green">BAJO</Badge>
                  </Stack>
                </Group>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Text fw={500} size="lg">
                  Red Flags por Severidad
                </Text>
                <Divider />
                <Table>
                  <Table.Tbody>
                    <Table.Tr>
                      <Table.Td>
                        <Badge color="red">CRITICAL</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={700}>{red_flags.by_severity.critical}</Text>
                      </Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td>
                        <Badge color="orange">HIGH</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={700}>{red_flags.by_severity.high}</Text>
                      </Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td>
                        <Badge color="yellow">MEDIUM</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={700}>{red_flags.by_severity.medium}</Text>
                      </Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td>
                        <Badge color="blue">LOW</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={700}>{red_flags.by_severity.low}</Text>
                      </Table.Td>
                    </Table.Tr>
                  </Table.Tbody>
                </Table>
              </Stack>
            </Card>
          </Grid.Col>
        </Grid>

        {/* Top Red Flags Types */}
        <Card shadow="sm" padding="lg">
          <Stack gap="md">
            <Text fw={500} size="lg">
              Tipos de Red Flags Más Comunes
            </Text>
            <Divider />
            <ScrollArea>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Cantidad</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {red_flags.top_types.map((item, index) => (
                    <Table.Tr key={index}>
                      <Table.Td>
                        <Badge variant="light">{item.type}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={700}>{item.count}</Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </Stack>
        </Card>

        {/* Recent Red Flags */}
        {recentFlags && recentFlags.flags && recentFlags.flags.length > 0 && (
          <Card shadow="sm" padding="lg">
            <Stack gap="md">
              <Text fw={500} size="lg">
                Red Flags Recientes
              </Text>
              <Divider />
              <ScrollArea h={300}>
                <Stack gap="xs">
                  {recentFlags.flags.slice(0, 5).map((flag: any, index: number) => (
                    <Card key={index} withBorder padding="sm">
                      <Stack gap="xs">
                        <Group justify="space-between">
                          <Badge color={getSeverityColor(flag.severity)}>
                            {flag.severity.toUpperCase()}
                          </Badge>
                          {flag.document && (
                            <Text size="xs" c="dimmed">
                              {flag.document.filename}
                            </Text>
                          )}
                        </Group>
                        <Text size="sm" fw={500}>
                          {flag.title}
                        </Text>
                        <Text size="xs" c="dimmed" lineClamp={2}>
                          {flag.description}
                        </Text>
                      </Stack>
                    </Card>
                  ))}
                </Stack>
              </ScrollArea>
            </Stack>
          </Card>
        )}
      </Stack>
    </Container>
  );
}

