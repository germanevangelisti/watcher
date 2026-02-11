import { Card, Title, Text, Stack, Progress, Group, Badge, Tooltip, Divider, Alert } from '@mantine/core';
import { IconInfoCircle, IconTrendingUp, IconTrendingDown, IconAlertTriangle } from '@tabler/icons-react';
import type { MetricasGenerales } from '../../../types/metricas';

interface EjecucionChartProps {
  metricas: MetricasGenerales;
}

export function EjecucionChart({ metricas }: EjecucionChartProps) {
  const formatMonto = (monto: number) => {
    const absMonto = Math.abs(monto);
    if (absMonto >= 1000000000) {
      return `$${(absMonto / 1000000000).toFixed(2)}B`;
    }
    if (absMonto >= 1000000) {
      return `$${(absMonto / 1000000).toFixed(2)}M`;
    }
    if (absMonto >= 1000) {
      return `$${(absMonto / 1000).toFixed(2)}K`;
    }
    return `$${absMonto.toFixed(2)}`;
  };

  const formatMontoCompleto = (monto: number) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Math.abs(monto));
  };

  const porcentajeEjecutado = metricas.porcentaje_ejecucion_global;
  const porcentajePendiente = 100 - porcentajeEjecutado;
  const montoDisponible = metricas.monto_total_vigente - metricas.monto_total_ejecutado;
  
  // Calcular variación presupuestaria
  const variacionPresupuesto = metricas.monto_total_inicial !== 0
    ? ((metricas.monto_total_vigente - metricas.monto_total_inicial) / metricas.monto_total_inicial) * 100
    : 0;

  // Determinar estado de ejecución
  const getEjecucionStatus = () => {
    if (porcentajeEjecutado === 0) return { label: 'Sin ejecución', color: 'gray', icon: IconInfoCircle };
    if (porcentajeEjecutado < 25) return { label: 'Ejecución baja', color: 'red', icon: IconAlertTriangle };
    if (porcentajeEjecutado < 50) return { label: 'Ejecución moderada', color: 'yellow', icon: IconTrendingUp };
    if (porcentajeEjecutado < 75) return { label: 'Ejecución buena', color: 'blue', icon: IconTrendingUp };
    return { label: 'Ejecución alta', color: 'green', icon: IconTrendingUp };
  };

  const ejecucionStatus = getEjecucionStatus();
  const StatusIcon = ejecucionStatus.icon;

  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={4} mb="xs">Ejecución Presupuestaria</Title>
            <Text size="sm" c="dimmed">
              Estado de ejecución del presupuesto vigente
            </Text>
          </div>
          <Badge 
            color={ejecucionStatus.color} 
            variant="light" 
            leftSection={<StatusIcon size={14} />}
          >
            {ejecucionStatus.label}
          </Badge>
        </Group>

        {/* Barra de progreso principal */}
        <div>
          <Group justify="space-between" mb="xs">
            <Text size="sm" fw={600}>Progreso General</Text>
            <Text size="lg" fw={700} c={ejecucionStatus.color}>
              {porcentajeEjecutado.toFixed(1)}%
            </Text>
          </Group>
          <Progress 
            value={porcentajeEjecutado} 
            color={ejecucionStatus.color} 
            size="xl" 
            radius="md"
            animated={porcentajeEjecutado > 0}
          />
          <Group justify="space-between" mt="xs">
            <Text size="xs" c="dimmed">
              {formatMonto(metricas.monto_total_ejecutado)} ejecutado
            </Text>
            <Text size="xs" c="dimmed">
              {formatMonto(montoDisponible)} disponible
            </Text>
          </Group>
        </div>

        <Divider />

        {/* Desglose detallado */}
        <Stack gap="md">
          <div>
            <Group justify="space-between" mb="xs">
              <Group gap="xs">
                <Text size="sm" fw={600}>Presupuesto Vigente</Text>
                <Tooltip label={formatMontoCompleto(metricas.monto_total_vigente)} withArrow>
                  <IconInfoCircle size={14} style={{ cursor: 'help', color: 'var(--mantine-color-gray-6)' }} />
                </Tooltip>
              </Group>
              <Text size="sm" fw={700}>{formatMonto(metricas.monto_total_vigente)}</Text>
            </Group>
            <Progress value={100} color="gray" size="sm" />
          </div>

          <div>
            <Group justify="space-between" mb="xs">
              <Group gap="xs">
                <Text size="sm" fw={600} c="green">Ejecutado</Text>
                <Tooltip label={formatMontoCompleto(metricas.monto_total_ejecutado)} withArrow>
                  <IconInfoCircle size={14} style={{ cursor: 'help', color: 'var(--mantine-color-gray-6)' }} />
                </Tooltip>
              </Group>
              <Group gap="xs">
                <Text size="sm" fw={700} c="green">
                  {formatMonto(metricas.monto_total_ejecutado)}
                </Text>
                <Badge color="green" variant="light" size="sm">
                  {porcentajeEjecutado.toFixed(1)}%
                </Badge>
              </Group>
            </Group>
            <Progress value={porcentajeEjecutado} color="green" size="sm" />
          </div>

          <div>
            <Group justify="space-between" mb="xs">
              <Group gap="xs">
                <Text size="sm" fw={600} c="orange">Disponible</Text>
                <Tooltip label={formatMontoCompleto(montoDisponible)} withArrow>
                  <IconInfoCircle size={14} style={{ cursor: 'help', color: 'var(--mantine-color-gray-6)' }} />
                </Tooltip>
              </Group>
              <Group gap="xs">
                <Text size="sm" fw={700} c="orange">
                  {formatMonto(montoDisponible)}
                </Text>
                <Badge color="orange" variant="light" size="sm">
                  {porcentajePendiente.toFixed(1)}%
                </Badge>
              </Group>
            </Group>
            <Progress value={porcentajePendiente} color="orange" size="sm" />
          </div>
        </Stack>

        <Divider />

        {/* Evolución presupuestaria */}
        <div>
          <Text size="sm" fw={600} mb="md">Evolución Presupuestaria</Text>
          <Group justify="space-between" p="md" style={{ backgroundColor: 'var(--mantine-color-gray-0)', borderRadius: '8px' }}>
            <div style={{ textAlign: 'center', flex: 1 }}>
              <Text size="xs" c="dimmed" mb={4}>Presupuesto Inicial</Text>
              <Text fw={700} size="sm">{formatMonto(metricas.monto_total_inicial)}</Text>
              <Text size="xs" c="dimmed" mt={4}>
                Aprobado en Ley
              </Text>
            </div>
            <div style={{ textAlign: 'center', flex: 1 }}>
              <Text size="xs" c="dimmed" mb={4}>Presupuesto Vigente</Text>
              <Group justify="center" gap="xs">
                <Text fw={700} size="sm">{formatMonto(metricas.monto_total_vigente)}</Text>
                {variacionPresupuesto !== 0 && (
                  <Badge 
                    size="xs" 
                    color={variacionPresupuesto > 0 ? 'green' : 'red'} 
                    variant="light"
                    leftSection={variacionPresupuesto > 0 ? <IconTrendingUp size={10} /> : <IconTrendingDown size={10} />}
                  >
                    {Math.abs(variacionPresupuesto).toFixed(1)}%
                  </Badge>
                )}
              </Group>
              <Text size="xs" c="dimmed" mt={4}>
                Después de modificaciones
              </Text>
            </div>
            <div style={{ textAlign: 'center', flex: 1 }}>
              <Text size="xs" c="dimmed" mb={4}>Ejecutado</Text>
              <Text fw={700} size="sm" c="green">{formatMonto(metricas.monto_total_ejecutado)}</Text>
              <Text size="xs" c="dimmed" mt={4}>
                Acumulado
              </Text>
            </div>
          </Group>
        </div>

        {/* Alertas si hay situaciones relevantes */}
        {porcentajeEjecutado === 0 && (
          <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
            El presupuesto aún no registra ejecución. Esto puede ser normal al inicio del período fiscal.
          </Alert>
        )}

        {porcentajeEjecutado > 100 && (
          <Alert icon={<IconAlertTriangle size={16} />} color="red" variant="light">
            La ejecución supera el presupuesto vigente. Se recomienda revisar las modificaciones presupuestarias.
          </Alert>
        )}
      </Stack>
    </Card>
  );
}

