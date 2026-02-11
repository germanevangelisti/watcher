import { useEffect, useState } from 'react';
import {
  Card,
  Text,
  Group,
  Stack,
  RingProgress,
  Badge,
  ThemeIcon,
  Button,
  Loader,
  Alert,
  Progress,
} from '@mantine/core';
import { IconShieldCheck, IconShieldX, IconShieldHalf, IconArrowRight, IconAlertTriangle } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { getComplianceStats } from '../../services/api';

interface ComplianceWidgetProps {
  variant?: 'default' | 'compact';
}

export function ComplianceWidget({ variant = 'default' }: ComplianceWidgetProps) {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await getComplianceStats();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Error al cargar datos de compliance');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card padding="md" withBorder>
        <Stack align="center">
          <Loader size="sm" />
          <Text size="xs" c="dimmed">
            Cargando compliance...
          </Text>
        </Stack>
      </Card>
    );
  }

  if (error || !stats) {
    return (
      <Card padding="md" withBorder>
        <Alert icon={<IconAlertTriangle size="1rem" />} color="yellow" variant="light">
          <Text size="xs">Sistema de compliance en configuración inicial</Text>
        </Alert>
      </Card>
    );
  }

  const score = stats.compliance_score ?? 0;
  const level = stats.compliance_level || 'unknown';
  const byStatus = stats.results_by_status || {};

  const LEVEL_COLORS: Record<string, string> = {
    excellent: 'green',
    good: 'teal',
    acceptable: 'yellow',
    deficient: 'red',
    unknown: 'gray',
  };

  const LEVEL_LABELS: Record<string, string> = {
    excellent: 'Excelente',
    good: 'Bueno',
    acceptable: 'Aceptable',
    deficient: 'Deficiente',
    unknown: 'Sin Evaluar',
  };

  if (variant === 'compact') {
    return (
      <Card padding="md" withBorder style={{ cursor: 'pointer' }} onClick={() => navigate('/compliance')}>
        <Group justify="space-between">
          <Group gap="sm">
            <ThemeIcon size="lg" variant="light" color={LEVEL_COLORS[level]}>
              <IconShieldCheck size="1.2rem" />
            </ThemeIcon>
            <div>
              <Text fw={600} size="sm">
                Compliance Fiscal
              </Text>
              <Badge size="sm" color={LEVEL_COLORS[level]}>
                {LEVEL_LABELS[level]}
              </Badge>
            </div>
          </Group>
          <Group gap="xs">
            <Text fw={700} size="xl">
              {score.toFixed(0)}%
            </Text>
            <IconArrowRight size="1rem" />
          </Group>
        </Group>
      </Card>
    );
  }

  return (
    <Card padding="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between">
          <Group>
            <ThemeIcon size="lg" variant="light" color={LEVEL_COLORS[level]}>
              <IconShieldCheck size="1.2rem" />
            </ThemeIcon>
            <div>
              <Text fw={600}>Compliance Fiscal</Text>
              <Text size="xs" c="dimmed">
                Cumplimiento de obligaciones legales
              </Text>
            </div>
          </Group>
        </Group>

        <Group justify="space-between" align="flex-start">
          <RingProgress
            size={120}
            thickness={12}
            sections={[
              {
                value: score,
                color: score >= 75 ? 'green' : score >= 50 ? 'yellow' : 'red',
              },
            ]}
            label={
              <div style={{ textAlign: 'center' }}>
                <Text size="lg" fw={700}>
                  {score.toFixed(0)}%
                </Text>
                <Text size="xs" c="dimmed">
                  Score
                </Text>
              </div>
            }
          />

          <Stack gap="xs" style={{ flex: 1 }}>
            <div>
              <Group justify="space-between" mb={3}>
                <Group gap={5}>
                  <IconShieldCheck size="0.8rem" color="green" />
                  <Text size="xs">Cumple</Text>
                </Group>
                <Text size="xs" fw={600}>
                  {byStatus.pass || 0}
                </Text>
              </Group>
              <Progress value={((byStatus.pass || 0) / stats.total_checks) * 100} color="green" size="xs" />
            </div>

            <div>
              <Group justify="space-between" mb={3}>
                <Group gap={5}>
                  <IconShieldHalf size="0.8rem" color="orange" />
                  <Text size="xs">Parcial</Text>
                </Group>
                <Text size="xs" fw={600}>
                  {byStatus.warn || 0}
                </Text>
              </Group>
              <Progress value={((byStatus.warn || 0) / stats.total_checks) * 100} color="yellow" size="xs" />
            </div>

            <div>
              <Group justify="space-between" mb={3}>
                <Group gap={5}>
                  <IconShieldX size="0.8rem" color="red" />
                  <Text size="xs">No Cumple</Text>
                </Group>
                <Text size="xs" fw={600}>
                  {byStatus.fail || 0}
                </Text>
              </Group>
              <Progress value={((byStatus.fail || 0) / stats.total_checks) * 100} color="red" size="xs" />
            </div>
          </Stack>
        </Group>

        <Button variant="light" fullWidth onClick={() => navigate('/compliance')} rightSection={<IconArrowRight size="1rem" />}>
          Ver Scorecard Completo
        </Button>
      </Stack>
    </Card>
  );
}
