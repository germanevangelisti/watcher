import { useEffect, useState } from 'react';
import {
  Container,
  Title,
  Text,
  Paper,
  Grid,
  Badge,
  Group,
  Stack,
  RingProgress,
  ThemeIcon,
  Anchor,
  Accordion,
  Alert,
  Button,
  Loader,
  Center,
  Card,
  Progress,
  Tabs,
} from '@mantine/core';
import {
  IconShieldCheck,
  IconShieldX,
  IconShieldHalf,
  IconShieldQuestion,
  IconAlertTriangle,
  IconExternalLink,
  IconInfoCircle,
  IconBook,
  IconRefresh,
  IconFileText,
  IconChecklist,
} from '@tabler/icons-react';
import { getComplianceScorecard, syncComplianceChecks, executeComplianceChecks } from '../services/api';
import { DocumentInventory } from '../components/compliance/DocumentInventory';

interface CheckDetail {
  check_code: string;
  check_name: string;
  priority: string;
  category: string | null;
  legal_basis: string;
  status: string;
  score: number | null;
  last_evaluation: string | null;
  summary: string;
  citizen_explanation: string | null;
}

interface ScorecardData {
  scorecard: {
    overall_score: number | null;
    total_checks: number;
    status_breakdown: {
      pass: number;
      warn: number;
      fail: number;
      unknown: number;
    };
    evaluation_date: string;
    jurisdiccion_id: number | null;
  };
  checks: CheckDetail[];
  red_flags: CheckDetail[];
  compliance_level: string;
}

const STATUS_COLORS = {
  pass: 'green',
  warn: 'yellow',
  fail: 'red',
  unknown: 'gray',
  not_executed: 'gray',
};

const STATUS_ICONS = {
  pass: IconShieldCheck,
  warn: IconShieldHalf,
  fail: IconShieldX,
  unknown: IconShieldQuestion,
  not_executed: IconShieldQuestion,
};

const STATUS_LABELS = {
  pass: 'Cumple',
  warn: 'Cumple Parcialmente',
  fail: 'No Cumple',
  unknown: 'Sin Evaluar',
  not_executed: 'No Ejecutado',
};

const PRIORITY_COLORS = {
  critical: 'red',
  high: 'orange',
  medium: 'yellow',
  low: 'blue',
};

const PRIORITY_LABELS = {
  critical: 'Crítico',
  high: 'Alto',
  medium: 'Medio',
  low: 'Bajo',
};

const COMPLIANCE_LEVEL_LABELS = {
  excellent: 'Excelente',
  good: 'Bueno',
  acceptable: 'Aceptable',
  deficient: 'Deficiente',
  unknown: 'Desconocido',
};

const COMPLIANCE_LEVEL_COLORS = {
  excellent: 'green',
  good: 'teal',
  acceptable: 'yellow',
  deficient: 'red',
  unknown: 'gray',
};

export function CompliancePage() {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [scorecard, setScorecard] = useState<ScorecardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadScorecard = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getComplianceScorecard();
      setScorecard(data);
    } catch (err: any) {
      setError(err.message || 'Error al cargar el scorecard');
      console.error('Error loading scorecard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      await syncComplianceChecks();
      await loadScorecard();
    } catch (err: any) {
      setError(err.message || 'Error al sincronizar checks');
    } finally {
      setSyncing(false);
    }
  };

  const handleExecute = async () => {
    try {
      setExecuting(true);
      await executeComplianceChecks();
      await loadScorecard();
    } catch (err: any) {
      setError(err.message || 'Error al ejecutar checks');
    } finally {
      setExecuting(false);
    }
  };

  useEffect(() => {
    loadScorecard();
  }, []);

  if (loading) {
    return (
      <Center style={{ height: '80vh' }}>
        <Stack align="center">
          <Loader size="xl" />
          <Text size="lg">Cargando scorecard de compliance...</Text>
        </Stack>
      </Center>
    );
  }

  if (error) {
    return (
      <Container size="lg" py="xl">
        <Alert icon={<IconAlertTriangle size="1rem" />} title="Error" color="red">
          {error}
        </Alert>
      </Container>
    );
  }

  if (!scorecard) {
    return (
      <Container size="lg" py="xl">
        <Alert icon={<IconInfoCircle size="1rem" />} title="Sin datos">
          No se encontró información de compliance
        </Alert>
      </Container>
    );
  }

  const { overall_score, total_checks, status_breakdown, evaluation_date } = scorecard.scorecard;
  const score = overall_score ?? 0;

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        {/* Header */}
        <div>
          <Title order={1}>Compliance Fiscal</Title>
          <Text c="dimmed" size="sm" mt="xs">
            Monitoreo de transparencia basado en obligaciones legales
          </Text>
        </div>

        <Tabs defaultValue="scorecard" variant="outline">
          <Tabs.List>
            <Tabs.Tab value="scorecard" leftSection={<IconChecklist size="1rem" />}>
              Scorecard de Checks
            </Tabs.Tab>
            <Tabs.Tab value="documents" leftSection={<IconFileText size="1rem" />}>
              Inventario de Documentos
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="scorecard" pt="xl">
            <Stack gap="xl">
              {/* Action Buttons */}
              <Group justify="flex-end">
                <Button
                  leftSection={<IconRefresh size="1rem" />}
                  variant="light"
                  onClick={handleSync}
                  loading={syncing}
                >
                  Sincronizar Checks
                </Button>
                <Button leftSection={<IconShieldCheck size="1rem" />} onClick={handleExecute} loading={executing}>
                  Ejecutar Evaluación
                </Button>
              </Group>

              <Alert icon={<IconInfoCircle size="1rem" />} variant="light" color="blue">
                Este scorecard evalúa si la Provincia de Córdoba cumple con las obligaciones de transparencia fiscal
                establecidas en la Ley 25.917 (Régimen Federal de Responsabilidad Fiscal) y su adhesión provincial (Ley
                10.471).
              </Alert>

        {/* Score Overview */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Paper p="xl" withBorder style={{ height: '100%' }}>
              <Stack align="center" gap="md">
                <RingProgress
                  size={180}
                  thickness={20}
                  sections={[
                    {
                      value: score,
                      color: score >= 75 ? 'green' : score >= 50 ? 'yellow' : 'red',
                    },
                  ]}
                  label={
                    <div style={{ textAlign: 'center' }}>
                      <Text size="xl" fw={700}>
                        {score.toFixed(0)}%
                      </Text>
                      <Text size="xs" c="dimmed">
                        Score General
                      </Text>
                    </div>
                  }
                />
                <Badge size="lg" color={COMPLIANCE_LEVEL_COLORS[scorecard.compliance_level as keyof typeof COMPLIANCE_LEVEL_COLORS]}>
                  {COMPLIANCE_LEVEL_LABELS[scorecard.compliance_level as keyof typeof COMPLIANCE_LEVEL_LABELS]}
                </Badge>
                <Text size="xs" c="dimmed">
                  Evaluado el {new Date(evaluation_date).toLocaleDateString()}
                </Text>
              </Stack>
            </Paper>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 8 }}>
            <Paper p="md" withBorder style={{ height: '100%' }}>
              <Title order={4} mb="md">
                Desglose por Estado
              </Title>
              <Stack gap="md">
                <div>
                  <Group justify="space-between" mb={5}>
                    <Group gap="xs">
                      <ThemeIcon size="sm" color="green" variant="light">
                        <IconShieldCheck size="0.8rem" />
                      </ThemeIcon>
                      <Text size="sm">Cumple</Text>
                    </Group>
                    <Text size="sm" fw={600}>
                      {status_breakdown.pass}
                    </Text>
                  </Group>
                  <Progress value={(status_breakdown.pass / total_checks) * 100} color="green" />
                </div>

                <div>
                  <Group justify="space-between" mb={5}>
                    <Group gap="xs">
                      <ThemeIcon size="sm" color="yellow" variant="light">
                        <IconShieldHalf size="0.8rem" />
                      </ThemeIcon>
                      <Text size="sm">Cumple Parcialmente</Text>
                    </Group>
                    <Text size="sm" fw={600}>
                      {status_breakdown.warn}
                    </Text>
                  </Group>
                  <Progress value={(status_breakdown.warn / total_checks) * 100} color="yellow" />
                </div>

                <div>
                  <Group justify="space-between" mb={5}>
                    <Group gap="xs">
                      <ThemeIcon size="sm" color="red" variant="light">
                        <IconShieldX size="0.8rem" />
                      </ThemeIcon>
                      <Text size="sm">No Cumple</Text>
                    </Group>
                    <Text size="sm" fw={600}>
                      {status_breakdown.fail}
                    </Text>
                  </Group>
                  <Progress value={(status_breakdown.fail / total_checks) * 100} color="red" />
                </div>

                <div>
                  <Group justify="space-between" mb={5}>
                    <Group gap="xs">
                      <ThemeIcon size="sm" color="gray" variant="light">
                        <IconShieldQuestion size="0.8rem" />
                      </ThemeIcon>
                      <Text size="sm">Sin Evaluar</Text>
                    </Group>
                    <Text size="sm" fw={600}>
                      {status_breakdown.unknown}
                    </Text>
                  </Group>
                  <Progress value={(status_breakdown.unknown / total_checks) * 100} color="gray" />
                </div>
              </Stack>
            </Paper>
          </Grid.Col>
        </Grid>

        {/* Red Flags */}
        {scorecard.red_flags.length > 0 && (
          <Paper p="md" withBorder>
            <Group mb="md">
              <ThemeIcon size="lg" color="red" variant="light">
                <IconAlertTriangle size="1.2rem" />
              </ThemeIcon>
              <div>
                <Title order={3}>Red Flags de Compliance</Title>
                <Text size="sm" c="dimmed">
                  Obligaciones que no se están cumpliendo o se cumplen parcialmente
                </Text>
              </div>
            </Group>

            <Stack gap="sm">
              {scorecard.red_flags.map((flag) => {
                const StatusIcon = STATUS_ICONS[flag.status as keyof typeof STATUS_ICONS];
                return (
                  <Card key={flag.check_code} padding="md" withBorder>
                    <Group justify="space-between" mb="sm">
                      <Group>
                        <StatusIcon size="1.2rem" color={STATUS_COLORS[flag.status as keyof typeof STATUS_COLORS]} />
                        <div>
                          <Text fw={600}>{flag.check_name}</Text>
                          <Text size="xs" c="dimmed">
                            {flag.legal_basis}
                          </Text>
                        </div>
                      </Group>
                      <Group>
                        <Badge color={PRIORITY_COLORS[flag.priority as keyof typeof PRIORITY_COLORS]}>
                          {PRIORITY_LABELS[flag.priority as keyof typeof PRIORITY_LABELS]}
                        </Badge>
                        <Badge color={STATUS_COLORS[flag.status as keyof typeof STATUS_COLORS]}>
                          {STATUS_LABELS[flag.status as keyof typeof STATUS_LABELS]}
                        </Badge>
                      </Group>
                    </Group>
                    <Text size="sm">{flag.summary}</Text>
                  </Card>
                );
              })}
            </Stack>
          </Paper>
        )}

        {/* All Checks */}
        <Paper p="md" withBorder>
          <Title order={3} mb="md">
            Todos los Checks de Compliance
          </Title>

          <Accordion variant="separated">
            {scorecard.checks.map((check) => {
              const StatusIcon = STATUS_ICONS[check.status as keyof typeof STATUS_ICONS];
              return (
                <Accordion.Item key={check.check_code} value={check.check_code}>
                  <Accordion.Control
                    icon={<StatusIcon size="1rem" color={STATUS_COLORS[check.status as keyof typeof STATUS_COLORS]} />}
                  >
                    <Group justify="space-between">
                      <div>
                        <Text fw={500}>{check.check_name}</Text>
                        <Text size="xs" c="dimmed">
                          {check.legal_basis}
                        </Text>
                      </div>
                      <Group gap="xs">
                        <Badge size="sm" color={PRIORITY_COLORS[check.priority as keyof typeof PRIORITY_COLORS]}>
                          {PRIORITY_LABELS[check.priority as keyof typeof PRIORITY_LABELS]}
                        </Badge>
                        <Badge size="sm" color={STATUS_COLORS[check.status as keyof typeof STATUS_COLORS]}>
                          {STATUS_LABELS[check.status as keyof typeof STATUS_LABELS]}
                        </Badge>
                      </Group>
                    </Group>
                  </Accordion.Control>
                  <Accordion.Panel>
                    <Stack gap="md">
                      <div>
                        <Text fw={600} size="sm" mb={5}>
                          Estado Actual:
                        </Text>
                        <Text size="sm">{check.summary}</Text>
                      </div>

                      {check.citizen_explanation && (
                        <Alert icon={<IconBook size="1rem" />} variant="light" color="blue">
                          <Text fw={600} size="sm" mb={5}>
                            ¿Por qué es importante?
                          </Text>
                          <Text size="sm">{check.citizen_explanation}</Text>
                        </Alert>
                      )}

                      {check.last_evaluation && (
                        <Text size="xs" c="dimmed">
                          Última evaluación: {new Date(check.last_evaluation).toLocaleDateString()}
                        </Text>
                      )}
                    </Stack>
                  </Accordion.Panel>
                </Accordion.Item>
              );
            })}
          </Accordion>
        </Paper>

              {/* Footer Info */}
              <Alert icon={<IconInfoCircle size="1rem" />} variant="light">
                <Text size="sm">
                  <strong>Nota:</strong> Este sistema está en desarrollo. Actualmente, los checks están marcados como
                  "Sin Evaluar" hasta que se implementen los validadores automáticos específicos. El objetivo es
                  automatizar la verificación de cumplimiento mediante scraping y validación de los portales oficiales.
                </Text>
              </Alert>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="documents" pt="xl">
            <DocumentInventory />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
