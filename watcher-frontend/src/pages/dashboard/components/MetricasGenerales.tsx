import { Grid, Tooltip, Group, Text, Badge } from '@mantine/core';
import { 
  IconCash, 
  IconTrendingUp, 
  IconFileText, 
  IconAlertTriangle,
  IconLink,
  IconInfoCircle,
  IconTrendingDown
} from '@tabler/icons-react';
import { StatsCard } from '../../../components/shared/StatsCard';
import type { MetricasGenerales } from '../../../types/metricas';

interface MetricasGeneralesProps {
  metricas: MetricasGenerales;
}

export function MetricasGenerales({ metricas }: MetricasGeneralesProps) {
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

  // Calcular variación presupuestaria
  const variacionPresupuesto = metricas.monto_total_vigente !== 0 
    ? ((metricas.monto_total_vigente - metricas.monto_total_inicial) / metricas.monto_total_inicial) * 100
    : 0;

  // Calcular porcentaje de riesgo
  const porcentajeRiesgo = metricas.total_actos > 0
    ? (metricas.actos_alto_riesgo / metricas.total_actos) * 100
    : 0;

  // Calcular monto disponible
  const montoDisponible = metricas.monto_total_vigente - metricas.monto_total_ejecutado;

  return (
    <Grid>
      {/* Primera fila - Métricas principales */}
      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Programas Presupuestarios"
          value={metricas.total_programas.toLocaleString('es-AR')}
          icon={IconFileText}
          color="blue"
          description="Total de programas activos"
        />
      </Grid.Col>

      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Presupuesto Vigente"
          value={formatMonto(metricas.monto_total_vigente)}
          icon={IconCash}
          color="green"
          description={
            <Tooltip label={formatMontoCompleto(metricas.monto_total_vigente)} withArrow>
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="xs" c="dimmed">
                  {variacionPresupuesto !== 0 && (
                    <>
                      {variacionPresupuesto > 0 ? (
                        <IconTrendingUp size={12} style={{ display: 'inline' }} />
                      ) : (
                        <IconTrendingDown size={12} style={{ display: 'inline' }} />
                      )}
                      {' '}
                      {Math.abs(variacionPresupuesto).toFixed(1)}% vs inicial
                    </>
                  )}
                </Text>
                <IconInfoCircle size={12} />
              </Group>
            </Tooltip>
          }
        />
      </Grid.Col>

      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Ejecución Presupuestaria"
          value={`${metricas.porcentaje_ejecucion_global.toFixed(1)}%`}
          icon={IconTrendingUp}
          color={metricas.porcentaje_ejecucion_global > 80 ? 'green' : metricas.porcentaje_ejecucion_global > 50 ? 'yellow' : 'cyan'}
          description={
            <Tooltip label={`Ejecutado: ${formatMontoCompleto(metricas.monto_total_ejecutado)} | Disponible: ${formatMontoCompleto(montoDisponible)}`} withArrow>
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="xs" c="dimmed">
                  {formatMonto(metricas.monto_total_ejecutado)} ejecutado
                </Text>
                <IconInfoCircle size={12} />
              </Group>
            </Tooltip>
          }
        />
      </Grid.Col>

      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Monto Disponible"
          value={formatMonto(montoDisponible)}
          icon={IconCash}
          color="orange"
          description={
            <Tooltip label={formatMontoCompleto(montoDisponible)} withArrow>
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="xs" c="dimmed">
                  Por ejecutar
                </Text>
                <IconInfoCircle size={12} />
              </Group>
            </Tooltip>
          }
        />
      </Grid.Col>

      {/* Segunda fila - Actos y Riesgo */}
      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Actos Administrativos"
          value={metricas.total_actos.toLocaleString('es-AR')}
          icon={IconFileText}
          color="violet"
          description="Total de actos registrados"
        />
      </Grid.Col>

      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Actos de Alto Riesgo"
          value={metricas.actos_alto_riesgo.toLocaleString('es-AR')}
          icon={IconAlertTriangle}
          color="red"
          description={
            <Group gap={4}>
              <Badge size="xs" color="red" variant="light">
                {porcentajeRiesgo.toFixed(1)}% del total
              </Badge>
              {metricas.actos_medio_riesgo > 0 && (
                <Text size="xs" c="dimmed">
                  {metricas.actos_medio_riesgo} medio riesgo
                </Text>
              )}
            </Group>
          }
        />
      </Grid.Col>

      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Alertas Críticas"
          value={metricas.alertas_criticas.toLocaleString('es-AR')}
          icon={IconAlertTriangle}
          color="orange"
          description={
            <Group gap={4}>
              <Text size="xs" c="dimmed">
                {metricas.total_alertas} alertas totales
              </Text>
              {metricas.alertas_altas > 0 && (
                <Badge size="xs" color="orange" variant="light">
                  {metricas.alertas_altas} altas
                </Badge>
              )}
            </Group>
          }
        />
      </Grid.Col>

      <Grid.Col span={{ base: 12, xs: 6, md: 3 }}>
        <StatsCard
          title="Tasa de Vinculación"
          value={`${metricas.tasa_vinculacion.toFixed(1)}%`}
          icon={IconLink}
          color="teal"
          description={
            <Tooltip label={`${metricas.total_vinculos} vínculos creados de ${metricas.total_actos} actos totales`} withArrow>
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="xs" c="dimmed">
                  {metricas.total_vinculos} vínculos
                </Text>
                <IconInfoCircle size={12} />
              </Group>
            </Tooltip>
          }
        />
      </Grid.Col>
    </Grid>
  );
}

