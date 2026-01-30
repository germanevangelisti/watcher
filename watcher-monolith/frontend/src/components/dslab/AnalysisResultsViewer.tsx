import { useState, useEffect } from 'react';
import {
  Container,
  Title,
  Text,
  Card,
  Group,
  Badge,
  Stack,
  Grid,
  RingProgress,
  Accordion,
  Table,
  ScrollArea,
  Paper,
  Divider,
  Box,
  Loader,
  Alert,
  Select,
  Tabs,
  NumberFormatter,
  Code,
  ThemeIcon,
  List,
  Tooltip
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
  IconCash,
  IconBuilding,
  IconUsers,
  IconCalendar,
  IconFileText,
  IconRobot,
  IconChartBar,
  IconBrain
} from '@tabler/icons-react';

interface RedFlag {
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  title: string;
  description: string;
  evidence: any;
  confidence_score: number;
}

interface ExtractedEntity {
  raw_text: string;
  numeric_value?: number;
  position?: number;
}

interface DocumentResult {
  id: number;
  document_id: number;
  config_id: number;
  execution_id: number;
  transparency_score: number;
  risk_level: 'high' | 'medium' | 'low';
  anomaly_score: number;
  red_flags: RedFlag[];
  ml_predictions: {
    random_forest?: {
      risk_probability: number;
      confidence: number;
    };
    isolation_forest?: {
      is_anomaly: boolean;
      anomaly_score: number;
    };
    kmeans?: {
      cluster: number;
      distance_to_centroid: number;
    };
  };
  extracted_entities: {
    amounts: ExtractedEntity[];
    beneficiaries: string[];
    organisms: string[];
    dates: string[];
    contracts: string[];
  };
  extracted_text_sample: string;
  processing_time_seconds: number;
  num_red_flags: number;
  analyzed_at: string;
}

interface ApiResponse {
  execution_id: number;
  total_results: number;
  results: DocumentResult[];
}

export default function AnalysisResultsViewer({ executionId }: { executionId: number }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [selectedDocIndex, setSelectedDocIndex] = useState(0);

  useEffect(() => {
    loadResults();
  }, [executionId]);

  const loadResults = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8001/api/v1/dslab/analysis/executions/${executionId}/results`
      );
      if (!response.ok) throw new Error('Error loading results');
      const jsonData = await response.json();
      setData(jsonData);
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
          <Text>Cargando resultados del análisis...</Text>
        </Stack>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="xl" py="xl">
        <Alert color="red" title="Error" icon={<IconAlertTriangle />}>
          {error}
        </Alert>
      </Container>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <Container size="xl" py="xl">
        <Alert color="blue" title="Sin resultados" icon={<IconInfoCircle />}>
          No hay resultados disponibles para esta ejecución.
        </Alert>
      </Container>
    );
  }

  const currentDoc = data.results[selectedDocIndex];

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

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'teal';
    if (score >= 50) return 'yellow';
    return 'red';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <Box>
            <Title order={2}>Resultados del Análisis</Title>
            <Text c="dimmed" size="sm">
              Ejecución #{executionId} • {data.total_results} documentos analizados
            </Text>
          </Box>

          <Select
            label="Seleccionar documento"
            placeholder="Documento"
            value={selectedDocIndex.toString()}
            onChange={(value) => setSelectedDocIndex(parseInt(value || '0'))}
            data={data.results.map((_, index) => ({
              value: index.toString(),
              label: `Documento ${index + 1} (ID: ${data.results[index].document_id})`
            }))}
            style={{ minWidth: 250 }}
          />
        </Group>

        {/* Overview Cards */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Score de Transparencia
                  </Text>
                  <ThemeIcon variant="light" color={getScoreColor(currentDoc.transparency_score)}>
                    <IconChartBar size={16} />
                  </ThemeIcon>
                </Group>
                <RingProgress
                  size={120}
                  thickness={12}
                  sections={[
                    {
                      value: currentDoc.transparency_score,
                      color: getScoreColor(currentDoc.transparency_score)
                    }
                  ]}
                  label={
                    <Text ta="center" fw={700} size="xl">
                      {currentDoc.transparency_score.toFixed(1)}
                    </Text>
                  }
                />
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Nivel de Riesgo
                  </Text>
                  <ThemeIcon variant="light" color={getRiskColor(currentDoc.risk_level)}>
                    <IconAlertTriangle size={16} />
                  </ThemeIcon>
                </Group>
                <Box>
                  <Badge
                    color={getRiskColor(currentDoc.risk_level)}
                    size="xl"
                    variant="filled"
                    fullWidth
                  >
                    {currentDoc.risk_level.toUpperCase()}
                  </Badge>
                  <Text size="xs" c="dimmed" ta="center" mt="xs">
                    Anomaly Score: {currentDoc.anomaly_score.toFixed(2)}
                  </Text>
                </Box>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Red Flags
                  </Text>
                  <ThemeIcon variant="light" color="red">
                    <IconAlertTriangle size={16} />
                  </ThemeIcon>
                </Group>
                <Box>
                  <Text size="3xl" fw={700} ta="center">
                    {currentDoc.num_red_flags}
                  </Text>
                  <Text size="xs" c="dimmed" ta="center">
                    problemas detectados
                  </Text>
                </Box>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 3 }}>
            <Card shadow="sm" padding="lg">
              <Stack gap="md">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Tiempo de Procesamiento
                  </Text>
                  <ThemeIcon variant="light" color="blue">
                    <IconInfoCircle size={16} />
                  </ThemeIcon>
                </Group>
                <Box>
                  <Text size="3xl" fw={700} ta="center">
                    {currentDoc.processing_time_seconds.toFixed(2)}s
                  </Text>
                  <Text size="xs" c="dimmed" ta="center">
                    Doc ID: {currentDoc.document_id}
                  </Text>
                </Box>
              </Stack>
            </Card>
          </Grid.Col>
        </Grid>

        {/* Tabs with Detailed Information */}
        <Tabs defaultValue="redflags">
          <Tabs.List>
            <Tabs.Tab value="redflags" leftSection={<IconAlertTriangle size={16} />}>
              Red Flags ({currentDoc.num_red_flags})
            </Tabs.Tab>
            <Tabs.Tab value="entities" leftSection={<IconUsers size={16} />}>
              Entidades Extraídas
            </Tabs.Tab>
            <Tabs.Tab value="ml" leftSection={<IconBrain size={16} />}>
              Predicciones ML
            </Tabs.Tab>
            <Tabs.Tab value="text" leftSection={<IconFileText size={16} />}>
              Texto Extraído
            </Tabs.Tab>
          </Tabs.List>

          {/* Red Flags Tab */}
          <Tabs.Panel value="redflags" pt="md">
            <Card shadow="sm">
              {currentDoc.red_flags.length === 0 ? (
                <Alert color="green" icon={<IconCircleCheck />}>
                  No se detectaron red flags en este documento.
                </Alert>
              ) : (
                <Accordion>
                  {currentDoc.red_flags.map((flag, index) => (
                    <Accordion.Item key={index} value={`flag-${index}`}>
                      <Accordion.Control>
                        <Group justify="space-between">
                          <Group>
                            <Badge color={getSeverityColor(flag.severity)}>
                              {flag.severity.toUpperCase()}
                            </Badge>
                            <Text size="sm" fw={500}>
                              {flag.title}
                            </Text>
                          </Group>
                          {flag.confidence_score && (
                            <Badge variant="outline" color="gray">
                              Confianza: {(flag.confidence_score * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </Group>
                      </Accordion.Control>
                      <Accordion.Panel>
                        <Stack gap="sm">
                          <Text size="sm">{flag.description}</Text>
                          <Group gap="xs">
                            <Badge variant="light">{flag.type}</Badge>
                            <Badge variant="light">{flag.category}</Badge>
                          </Group>
                          {flag.evidence && (
                            <Box>
                              <Text size="sm" fw={500} mb="xs">
                                Evidencia:
                              </Text>
                              <Code block>{JSON.stringify(flag.evidence, null, 2)}</Code>
                            </Box>
                          )}
                        </Stack>
                      </Accordion.Panel>
                    </Accordion.Item>
                  ))}
                </Accordion>
              )}
            </Card>
          </Tabs.Panel>

          {/* Entities Tab */}
          <Tabs.Panel value="entities" pt="md">
            <Grid>
              {/* Amounts */}
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card shadow="sm">
                  <Stack gap="md">
                    <Group>
                      <ThemeIcon color="green" variant="light">
                        <IconCash size={18} />
                      </ThemeIcon>
                      <Text fw={500}>Montos Detectados ({currentDoc.extracted_entities.amounts.length})</Text>
                    </Group>
                    <Divider />
                    <ScrollArea h={300}>
                      <Table striped highlightOnHover>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>Monto</Table.Th>
                            <Table.Th>Texto Original</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {currentDoc.extracted_entities.amounts
                            .sort((a, b) => (b.numeric_value || 0) - (a.numeric_value || 0))
                            .map((amount, index) => (
                              <Table.Tr key={index}>
                                <Table.Td>
                                  <Text fw={500}>
                                    {formatCurrency(amount.numeric_value || 0)}
                                  </Text>
                                </Table.Td>
                                <Table.Td>
                                  <Code>{amount.raw_text}</Code>
                                </Table.Td>
                              </Table.Tr>
                            ))}
                        </Table.Tbody>
                      </Table>
                    </ScrollArea>
                  </Stack>
                </Card>
              </Grid.Col>

              {/* Beneficiaries */}
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card shadow="sm">
                  <Stack gap="md">
                    <Group>
                      <ThemeIcon color="blue" variant="light">
                        <IconUsers size={18} />
                      </ThemeIcon>
                      <Text fw={500}>
                        Beneficiarios ({currentDoc.extracted_entities.beneficiaries.length})
                      </Text>
                    </Group>
                    <Divider />
                    <ScrollArea h={300}>
                      <List size="sm">
                        {currentDoc.extracted_entities.beneficiaries.map((beneficiary, index) => (
                          <List.Item key={index}>{beneficiary}</List.Item>
                        ))}
                      </List>
                    </ScrollArea>
                  </Stack>
                </Card>
              </Grid.Col>

              {/* Organisms */}
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card shadow="sm">
                  <Stack gap="md">
                    <Group>
                      <ThemeIcon color="violet" variant="light">
                        <IconBuilding size={18} />
                      </ThemeIcon>
                      <Text fw={500}>
                        Organismos ({currentDoc.extracted_entities.organisms.length})
                      </Text>
                    </Group>
                    <Divider />
                    <ScrollArea h={300}>
                      <List size="sm">
                        {currentDoc.extracted_entities.organisms.map((org, index) => (
                          <List.Item key={index}>
                            <Text size="sm" lineClamp={2}>
                              {org}
                            </Text>
                          </List.Item>
                        ))}
                      </List>
                    </ScrollArea>
                  </Stack>
                </Card>
              </Grid.Col>

              {/* Dates */}
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card shadow="sm">
                  <Stack gap="md">
                    <Group>
                      <ThemeIcon color="orange" variant="light">
                        <IconCalendar size={18} />
                      </ThemeIcon>
                      <Text fw={500}>
                        Fechas ({currentDoc.extracted_entities.dates.length})
                      </Text>
                    </Group>
                    <Divider />
                    <ScrollArea h={300}>
                      <List size="sm">
                        {currentDoc.extracted_entities.dates.map((date, index) => (
                          <List.Item key={index}>
                            <Code>{date}</Code>
                          </List.Item>
                        ))}
                      </List>
                    </ScrollArea>
                  </Stack>
                </Card>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>

          {/* ML Predictions Tab */}
          <Tabs.Panel value="ml" pt="md">
            <Grid>
              {/* Random Forest */}
              {currentDoc.ml_predictions.random_forest && (
                <Grid.Col span={{ base: 12, md: 4 }}>
                  <Card shadow="sm">
                    <Stack gap="md">
                      <Group>
                        <ThemeIcon color="teal" variant="light">
                          <IconRobot size={18} />
                        </ThemeIcon>
                        <Text fw={500}>Random Forest</Text>
                      </Group>
                      <Divider />
                      <Box>
                        <Text size="sm" c="dimmed">
                          Probabilidad de Riesgo
                        </Text>
                        <Text size="xl" fw={700}>
                          {(currentDoc.ml_predictions.random_forest.risk_probability * 100).toFixed(
                            1
                          )}
                          %
                        </Text>
                      </Box>
                      <Box>
                        <Text size="sm" c="dimmed">
                          Confianza del Modelo
                        </Text>
                        <Text size="xl" fw={700}>
                          {(currentDoc.ml_predictions.random_forest.confidence * 100).toFixed(1)}%
                        </Text>
                      </Box>
                    </Stack>
                  </Card>
                </Grid.Col>
              )}

              {/* Isolation Forest */}
              {currentDoc.ml_predictions.isolation_forest && (
                <Grid.Col span={{ base: 12, md: 4 }}>
                  <Card shadow="sm">
                    <Stack gap="md">
                      <Group>
                        <ThemeIcon color="indigo" variant="light">
                          <IconBrain size={18} />
                        </ThemeIcon>
                        <Text fw={500}>Isolation Forest</Text>
                      </Group>
                      <Divider />
                      <Box>
                        <Text size="sm" c="dimmed">
                          Estado
                        </Text>
                        <Badge
                          color={
                            currentDoc.ml_predictions.isolation_forest.is_anomaly ? 'red' : 'green'
                          }
                          size="lg"
                        >
                          {currentDoc.ml_predictions.isolation_forest.is_anomaly
                            ? 'ANOMALÍA'
                            : 'NORMAL'}
                        </Badge>
                      </Box>
                      <Box>
                        <Text size="sm" c="dimmed">
                          Anomaly Score
                        </Text>
                        <Text size="xl" fw={700}>
                          {currentDoc.ml_predictions.isolation_forest.anomaly_score.toFixed(2)}
                        </Text>
                      </Box>
                    </Stack>
                  </Card>
                </Grid.Col>
              )}

              {/* K-Means */}
              {currentDoc.ml_predictions.kmeans && (
                <Grid.Col span={{ base: 12, md: 4 }}>
                  <Card shadow="sm">
                    <Stack gap="md">
                      <Group>
                        <ThemeIcon color="grape" variant="light">
                          <IconChartBar size={18} />
                        </ThemeIcon>
                        <Text fw={500}>K-Means Clustering</Text>
                      </Group>
                      <Divider />
                      <Box>
                        <Text size="sm" c="dimmed">
                          Cluster Asignado
                        </Text>
                        <Text size="xl" fw={700}>
                          #{currentDoc.ml_predictions.kmeans.cluster}
                        </Text>
                      </Box>
                      <Box>
                        <Text size="sm" c="dimmed">
                          Distancia al Centroide
                        </Text>
                        <Text size="xl" fw={700}>
                          {currentDoc.ml_predictions.kmeans.distance_to_centroid.toFixed(2)}
                        </Text>
                      </Box>
                    </Stack>
                  </Card>
                </Grid.Col>
              )}
            </Grid>
          </Tabs.Panel>

          {/* Text Extract Tab */}
          <Tabs.Panel value="text" pt="md">
            <Card shadow="sm">
              <Stack gap="md">
                <Group>
                  <ThemeIcon color="cyan" variant="light">
                    <IconFileText size={18} />
                  </ThemeIcon>
                  <Text fw={500}>Muestra del Texto Extraído</Text>
                </Group>
                <Divider />
                <ScrollArea h={400}>
                  <Code block>{currentDoc.extracted_text_sample}</Code>
                </ScrollArea>
                <Text size="xs" c="dimmed">
                  Analizado el: {new Date(currentDoc.analyzed_at).toLocaleString('es-AR')}
                </Text>
              </Stack>
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}

