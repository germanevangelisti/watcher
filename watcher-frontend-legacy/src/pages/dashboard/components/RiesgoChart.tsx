import { Card, Title, Text, Stack, Group, Badge, Progress, Tooltip } from '@mantine/core';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip as RechartsTooltip } from 'recharts';
import { IconAlertTriangle, IconInfoCircle } from '@tabler/icons-react';
import type { MetricasGenerales } from '../../../types/metricas';

interface RiesgoChartProps {
  metricas: MetricasGenerales;
}

export function RiesgoChart({ metricas }: RiesgoChartProps) {
  const totalActos = metricas.total_actos;
  const porcentajeAlto = totalActos > 0 ? (metricas.actos_alto_riesgo / totalActos) * 100 : 0;
  const porcentajeMedio = totalActos > 0 ? (metricas.actos_medio_riesgo / totalActos) * 100 : 0;
  const porcentajeBajo = totalActos > 0 ? (metricas.actos_bajo_riesgo / totalActos) * 100 : 0;

  const data = [
    { name: 'Alto Riesgo', value: metricas.actos_alto_riesgo, color: '#fa5252', porcentaje: porcentajeAlto },
    { name: 'Medio Riesgo', value: metricas.actos_medio_riesgo, color: '#fcc419', porcentaje: porcentajeMedio },
    { name: 'Bajo Riesgo', value: metricas.actos_bajo_riesgo, color: '#51cf66', porcentaje: porcentajeBajo },
  ].filter(item => item.value > 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div style={{ 
          backgroundColor: 'white', 
          padding: '8px', 
          border: '1px solid #ccc',
          borderRadius: '4px'
        }}>
          <Text size="sm" fw={600}>{data.name}</Text>
          <Text size="sm">Cantidad: {data.value.toLocaleString('es-AR')}</Text>
          <Text size="sm">Porcentaje: {data.porcentaje.toFixed(1)}%</Text>
        </div>
      );
    }
    return null;
  };

  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={4} mb="xs">Distribución de Riesgo</Title>
            <Text size="sm" c="dimmed">
              Clasificación de {totalActos.toLocaleString('es-AR')} actos por nivel de riesgo
            </Text>
          </div>
          {porcentajeAlto > 20 && (
            <Tooltip label="Más del 20% de los actos son de alto riesgo. Requiere atención prioritaria." withArrow>
              <Badge color="red" variant="light" leftSection={<IconAlertTriangle size={14} />}>
                Atención
              </Badge>
            </Tooltip>
          )}
        </Group>

        {totalActos > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ porcentaje }) => `${porcentaje.toFixed(1)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  formatter={(value, entry: any) => (
                    <span style={{ color: entry.color }}>
                      {value} ({entry.payload.porcentaje.toFixed(1)}%)
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>

            <Stack gap="sm">
              <div>
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    <div style={{ width: 12, height: 12, backgroundColor: '#fa5252', borderRadius: 2 }} />
                    <Text size="sm" fw={500}>Alto Riesgo</Text>
                  </Group>
                  <Group gap="md">
                    <Text size="sm" fw={700} c="red">
                      {metricas.actos_alto_riesgo.toLocaleString('es-AR')}
                    </Text>
                    <Badge color="red" variant="light" size="sm">
                      {porcentajeAlto.toFixed(1)}%
                    </Badge>
                  </Group>
                </Group>
                <Progress value={porcentajeAlto} color="red" size="sm" />
              </div>

              <div>
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    <div style={{ width: 12, height: 12, backgroundColor: '#fcc419', borderRadius: 2 }} />
                    <Text size="sm" fw={500}>Medio Riesgo</Text>
                  </Group>
                  <Group gap="md">
                    <Text size="sm" fw={700} c="yellow">
                      {metricas.actos_medio_riesgo.toLocaleString('es-AR')}
                    </Text>
                    <Badge color="yellow" variant="light" size="sm">
                      {porcentajeMedio.toFixed(1)}%
                    </Badge>
                  </Group>
                </Group>
                <Progress value={porcentajeMedio} color="yellow" size="sm" />
              </div>

              <div>
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    <div style={{ width: 12, height: 12, backgroundColor: '#51cf66', borderRadius: 2 }} />
                    <Text size="sm" fw={500}>Bajo Riesgo</Text>
                  </Group>
                  <Group gap="md">
                    <Text size="sm" fw={700} c="green">
                      {metricas.actos_bajo_riesgo.toLocaleString('es-AR')}
                    </Text>
                    <Badge color="green" variant="light" size="sm">
                      {porcentajeBajo.toFixed(1)}%
                    </Badge>
                  </Group>
                </Group>
                <Progress value={porcentajeBajo} color="green" size="sm" />
              </div>
            </Stack>
          </>
        ) : (
          <Group justify="center" py="xl">
            <Text c="dimmed">No hay datos de actos disponibles</Text>
          </Group>
        )}
      </Stack>
    </Card>
  );
}

