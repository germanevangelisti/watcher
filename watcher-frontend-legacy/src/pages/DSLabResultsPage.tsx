import { useState, useEffect } from 'react';
import {
  Container,
  Title,
  Text,
  Stack,
  Card,
  Group,
  Select,
  Badge,
  Loader,
  Alert,
  Button
} from '@mantine/core';
import { IconAlertCircle, IconChartBar, IconArrowLeft } from '@tabler/icons-react';
import { useParams, useNavigate } from 'react-router-dom';
import AnalysisResultsViewer from '../components/dslab/AnalysisResultsViewer';

interface Execution {
  id: number;
  execution_name: string;
  status: string;
  total_documents: number;
  processed_documents: number;
  started_at: string;
  completed_at: string | null;
}

export default function DSLabResultsPage() {
  const { executionId } = useParams<{ executionId: string }>();
  const navigate = useNavigate();
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [currentExecution, setCurrentExecution] = useState<Execution | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>(executionId || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadExecutions();
  }, []);

  useEffect(() => {
    if (selectedExecutionId && executions.length > 0) {
      const exec = executions.find((e) => e.id.toString() === selectedExecutionId);
      setCurrentExecution(exec || null);
    }
  }, [selectedExecutionId, executions]);

  const loadExecutions = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8001/api/v1/dslab/analysis/executions');
      if (!response.ok) throw new Error('Error loading executions');
      const data = await response.json();
      
      // Filter only completed executions
      const completedExecs = data.filter(
        (exec: Execution) => exec.status === 'completed' && exec.processed_documents > 0
      );
      
      setExecutions(completedExecs);
      
      // Set initial execution if provided in URL, otherwise use first
      if (executionId) {
        setSelectedExecutionId(executionId);
      } else if (completedExecs.length > 0) {
        setSelectedExecutionId(completedExecs[0].id.toString());
      }
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
          <Text>Cargando ejecuciones...</Text>
        </Stack>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="xl" py="xl">
        <Alert color="red" title="Error" icon={<IconAlertCircle />}>
          {error}
        </Alert>
      </Container>
    );
  }

  if (executions.length === 0) {
    return (
      <Container size="xl" py="xl">
        <Stack align="center" gap="md">
          <Alert color="blue" title="Sin resultados" icon={<IconChartBar />}>
            No hay análisis completados disponibles aún. Ejecuta un análisis primero desde la página
            de ejecución.
          </Alert>
          <Button onClick={() => navigate('/dslab/analysis')}>Ir a Ejecutar Análisis</Button>
        </Stack>
      </Container>
    );
  }

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between">
          <Stack gap="xs">
            <Group>
              <Button
                variant="subtle"
                leftSection={<IconArrowLeft size={16} />}
                onClick={() => navigate('/dslab/analysis')}
              >
                Volver
              </Button>
              <Title order={2}>Visualización de Resultados</Title>
            </Group>
            <Text c="dimmed" size="sm">
              Explora los resultados detallados de tus análisis completados
            </Text>
          </Stack>
        </Group>

        {/* Execution Selector */}
        <Card shadow="sm" padding="lg">
          <Stack gap="md">
            <Text fw={500}>Seleccionar Análisis</Text>
            <Select
              label="Ejecución de Análisis"
              placeholder="Selecciona una ejecución"
              value={selectedExecutionId}
              onChange={(value) => {
                if (value) {
                  setSelectedExecutionId(value);
                  navigate(`/dslab/results/${value}`);
                }
              }}
              data={executions.map((exec) => ({
                value: exec.id.toString(),
                label: `${exec.execution_name || `Ejecución #${exec.id}`} - ${exec.processed_documents} docs - ${new Date(
                  exec.started_at
                ).toLocaleDateString('es-AR')}`
              }))}
            />

            {currentExecution && (
              <Group gap="md" mt="sm">
                <Badge variant="light" color="blue">
                  {currentExecution.total_documents} documentos
                </Badge>
                <Badge variant="light" color="green">
                  {new Date(currentExecution.started_at).toLocaleDateString('es-AR', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric'
                  })}
                </Badge>
                {currentExecution.completed_at && (
                  <Badge variant="light" color="teal">
                    Completado:{' '}
                    {new Date(currentExecution.completed_at).toLocaleTimeString('es-AR', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </Badge>
                )}
              </Group>
            )}
          </Stack>
        </Card>

        {/* Results Viewer */}
        {selectedExecutionId && (
          <AnalysisResultsViewer executionId={parseInt(selectedExecutionId)} />
        )}
      </Stack>
    </Container>
  );
}

