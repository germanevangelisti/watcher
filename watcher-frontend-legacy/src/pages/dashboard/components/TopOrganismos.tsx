import { Card, Title, Text, Stack, Table, Badge, Progress, Group, Tooltip, Grid } from '@mantine/core';
import { IconBuilding, IconAlertTriangle, IconInfoCircle, IconCash } from '@tabler/icons-react';
import type { MetricasGenerales } from '../../../types/metricas';

interface TopOrganismosProps {
  metricas: MetricasGenerales;
}

export function TopOrganismos({ metricas }: TopOrganismosProps) {
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

  const totalPresupuesto = metricas.monto_total_vigente;
  const maxMonto = metricas.top_organismos_presupuesto.length > 0
    ? Math.max(...metricas.top_organismos_presupuesto.map(o => Math.abs(o.monto)))
    : 1;
  const maxRiesgo = metricas.top_organismos_riesgo.length > 0
    ? Math.max(...metricas.top_organismos_riesgo.map(o => o.actos_alto_riesgo))
    : 1;

  return (
    <Grid>
      {/* Top por Presupuesto */}
      <Grid.Col span={{ base: 12, md: 6 }}>
        <Card withBorder shadow="sm" padding="lg">
          <Stack gap="md">
            <Group justify="space-between" align="flex-start">
              <div>
                <Title order={4} mb="xs">Top Organismos por Presupuesto</Title>
                <Text size="sm" c="dimmed">
                  Organismos con mayor presupuesto vigente
                </Text>
              </div>
              <IconBuilding size={24} style={{ color: 'var(--mantine-color-blue-6)' }} />
            </Group>

            {metricas.top_organismos_presupuesto.length > 0 ? (
              <>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th style={{ width: '50px' }}>#</Table.Th>
                      <Table.Th>Organismo</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Presupuesto</Table.Th>
                      <Table.Th style={{ width: '120px' }}>% del Total</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {metricas.top_organismos_presupuesto.map((org, idx) => {
                      const porcentajeTotal = totalPresupuesto > 0
                        ? (Math.abs(org.monto) / totalPresupuesto) * 100
                        : 0;
                      return (
                        <Table.Tr key={idx}>
                          <Table.Td>
                            <Badge 
                              size="lg" 
                              variant="light" 
                              color={idx === 0 ? 'blue' : 'gray'}
                            >
                              {idx + 1}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Tooltip label={org.organismo} withArrow>
                              <Text size="sm" fw={500} lineClamp={1} style={{ maxWidth: '200px' }}>
                                {org.organismo}
                              </Text>
                            </Tooltip>
                          </Table.Td>
                          <Table.Td style={{ textAlign: 'right' }}>
                            <Tooltip label={formatMontoCompleto(org.monto)} withArrow>
                              <Group gap={4} justify="flex-end" style={{ cursor: 'help' }}>
                                <Text size="sm" fw={600}>
                                  {formatMonto(org.monto)}
                                </Text>
                                <IconInfoCircle size={12} style={{ color: 'var(--mantine-color-gray-6)' }} />
                              </Group>
                            </Tooltip>
                          </Table.Td>
                          <Table.Td>
                            <Group gap="xs">
                              <Progress 
                                value={(Math.abs(org.monto) / maxMonto) * 100} 
                                color="blue"
                                size="sm"
                                style={{ flex: 1 }}
                              />
                              <Text size="xs" c="dimmed" style={{ minWidth: '45px' }}>
                                {porcentajeTotal.toFixed(1)}%
                              </Text>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>

                <Group justify="space-between" p="sm" style={{ backgroundColor: 'var(--mantine-color-blue-0)', borderRadius: '8px' }}>
                  <Group gap="xs">
                    <IconCash size={16} style={{ color: 'var(--mantine-color-blue-6)' }} />
                    <Text size="xs" c="dimmed">Total Top 5:</Text>
                  </Group>
                  <Text size="sm" fw={600}>
                    {formatMonto(
                      metricas.top_organismos_presupuesto.reduce((sum, org) => sum + Math.abs(org.monto), 0)
                    )}
                  </Text>
                </Group>
              </>
            ) : (
              <Text c="dimmed" ta="center" py="md">
                No hay datos de organismos disponibles
              </Text>
            )}
          </Stack>
        </Card>
      </Grid.Col>

      {/* Top por Riesgo */}
      <Grid.Col span={{ base: 12, md: 6 }}>
        <Card withBorder shadow="sm" padding="lg">
          <Stack gap="md">
            <Group justify="space-between" align="flex-start">
              <div>
                <Title order={4} mb="xs">Top Organismos por Riesgo</Title>
                <Text size="sm" c="dimmed">
                  Organismos con más actos de alto riesgo
                </Text>
              </div>
              <IconAlertTriangle size={24} style={{ color: 'var(--mantine-color-red-6)' }} />
            </Group>

            {metricas.top_organismos_riesgo.length > 0 ? (
              <>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th style={{ width: '50px' }}>#</Table.Th>
                      <Table.Th>Organismo</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Alto Riesgo</Table.Th>
                      <Table.Th style={{ width: '120px' }}>Proporción</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {metricas.top_organismos_riesgo.map((org, idx) => {
                      const porcentajeTotal = metricas.actos_alto_riesgo > 0
                        ? (org.actos_alto_riesgo / metricas.actos_alto_riesgo) * 100
                        : 0;
                      return (
                        <Table.Tr key={idx}>
                          <Table.Td>
                            <Badge 
                              size="lg" 
                              variant="light" 
                              color={idx === 0 ? 'red' : 'gray'}
                            >
                              {idx + 1}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Tooltip label={org.organismo} withArrow>
                              <Text size="sm" fw={500} lineClamp={1} style={{ maxWidth: '200px' }}>
                                {org.organismo}
                              </Text>
                            </Tooltip>
                          </Table.Td>
                          <Table.Td style={{ textAlign: 'right' }}>
                            <Badge color="red" size="lg" variant="filled">
                              {org.actos_alto_riesgo}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Group gap="xs">
                              <Progress 
                                value={(org.actos_alto_riesgo / maxRiesgo) * 100} 
                                color="red"
                                size="sm"
                                style={{ flex: 1 }}
                              />
                              <Text size="xs" c="dimmed" style={{ minWidth: '45px' }}>
                                {porcentajeTotal.toFixed(1)}%
                              </Text>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>

                <Group justify="space-between" p="sm" style={{ backgroundColor: 'var(--mantine-color-red-0)', borderRadius: '8px' }}>
                  <Group gap="xs">
                    <IconAlertTriangle size={16} style={{ color: 'var(--mantine-color-red-6)' }} />
                    <Text size="xs" c="dimmed">Total Top 5:</Text>
                  </Group>
                  <Badge color="red" size="lg">
                    {metricas.top_organismos_riesgo.reduce((sum, org) => sum + org.actos_alto_riesgo, 0)} actos
                  </Badge>
                </Group>
              </>
            ) : (
              <Text c="dimmed" ta="center" py="md">
                No hay datos de riesgo disponibles
              </Text>
            )}
          </Stack>
        </Card>
      </Grid.Col>
    </Grid>
  );
}

