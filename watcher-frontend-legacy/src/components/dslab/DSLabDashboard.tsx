import React from 'react';
import {
  Card,
  Group,
  Text,
  Stack,
  Grid,
  RingProgress,
  Badge,
  Table,
  ScrollArea,
  Box,
  Divider,
  Alert
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconFlag,
  IconFileAnalytics,
  IconChartBar,
  IconTrendingUp,
  IconDatabase
} from '@tabler/icons-react';

interface DSLabStats {
  total_files: number;
  total_size_mb: number;
  by_month: Record<string, number>;
  by_section: Record<number, number>;
}

interface RedFlag {
  severity: 'CRITICO' | 'ALTO' | 'MEDIO' | 'INFORMATIVO';
  category: string;
  description: string;
  document: string;
  confidence: number;
}

interface DSLabDashboardProps {
  stats: DSLabStats | null;
  redFlags?: RedFlag[];
}

const DSLabDashboard: React.FC<DSLabDashboardProps> = ({ stats, redFlags = [] }) => {
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICO': return 'red';
      case 'ALTO': return 'orange';
      case 'MEDIO': return 'yellow';
      case 'INFORMATIVO': return 'blue';
      default: return 'gray';
    }
  };

  const getSectionName = (section: number) => {
    const names = {
      1: 'Designaciones y Decretos',
      2: 'Compras y Contrataciones',
      3: 'Subsidios y Transferencias',
      4: 'Obras Públicas',
      5: 'Notificaciones Judiciales'
    };
    return names[section] || `Sección ${section}`;
  };

  const formatMonth = (monthKey: string) => {
    // monthKey format: YYYYMM
    const year = monthKey.substring(0, 4);
    const month = parseInt(monthKey.substring(4, 6));
    const monthNames = [
      'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
      'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
    ];
    return `${monthNames[month - 1]} ${year}`;
  };

  // Estadísticas de red flags
  const criticalCount = redFlags.filter(f => f.severity === 'CRITICO').length;
  const highCount = redFlags.filter(f => f.severity === 'ALTO').length;
  const mediumCount = redFlags.filter(f => f.severity === 'MEDIO').length;

  return (
    <Stack gap="md">
      {/* Estadísticas generales */}
      <Grid gutter="md">
        <Grid.Col span={3}>
          <Card withBorder p="md" h="100%">
            <Stack gap="xs" justify="space-between" h="100%">
              <Group gap="xs">
                <IconDatabase size={20} color="#228be6" />
                <Text size="sm" c="dimmed">Total Archivos</Text>
              </Group>
              <Text size="xl" fw={700}>
                {stats?.total_files || 0}
              </Text>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={3}>
          <Card withBorder p="md" h="100%">
            <Stack gap="xs" justify="space-between" h="100%">
              <Group gap="xs">
                <IconFileAnalytics size={20} color="#12b886" />
                <Text size="sm" c="dimmed">Tamaño Total</Text>
              </Group>
              <Text size="xl" fw={700}>
                {stats?.total_size_mb?.toFixed(1) || 0} MB
              </Text>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={3}>
          <Card withBorder p="md" h="100%">
            <Stack gap="xs" justify="space-between" h="100%">
              <Group gap="xs">
                <IconFlag size={20} color="#fa5252" />
                <Text size="sm" c="dimmed">Red Flags</Text>
              </Group>
              <Text size="xl" fw={700} c={criticalCount > 0 ? 'red' : 'gray'}>
                {redFlags.length}
              </Text>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={3}>
          <Card withBorder p="md" h="100%">
            <Stack gap="xs" justify="space-between" h="100%">
              <Group gap="xs">
                <IconAlertTriangle size={20} color="#fd7e14" />
                <Text size="sm" c="dimmed">Casos Críticos</Text>
              </Group>
              <Text size="xl" fw={700} c={criticalCount > 0 ? 'red' : 'gray'}>
                {criticalCount}
              </Text>
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>

      {/* Distribución de red flags por severidad */}
      {redFlags.length > 0 && (
        <Card withBorder p="md">
          <Group justify="space-between" align="flex-start">
            <Stack gap="xs" style={{ flex: 1 }}>
              <Group gap="xs">
                <IconChartBar size={20} />
                <Text size="lg" fw={600}>Distribución de Red Flags</Text>
              </Group>
              
              <Stack gap="xs" mt="md">
                <Group justify="space-between">
                  <Group gap="xs">
                    <Box w={12} h={12} style={{ backgroundColor: '#fa5252', borderRadius: 2 }} />
                    <Text size="sm">Crítico</Text>
                  </Group>
                  <Badge color="red">{criticalCount}</Badge>
                </Group>
                
                <Group justify="space-between">
                  <Group gap="xs">
                    <Box w={12} h={12} style={{ backgroundColor: '#fd7e14', borderRadius: 2 }} />
                    <Text size="sm">Alto</Text>
                  </Group>
                  <Badge color="orange">{highCount}</Badge>
                </Group>
                
                <Group justify="space-between">
                  <Group gap="xs">
                    <Box w={12} h={12} style={{ backgroundColor: '#ffd43b', borderRadius: 2 }} />
                    <Text size="sm">Medio</Text>
                  </Group>
                  <Badge color="yellow">{mediumCount}</Badge>
                </Group>
              </Stack>
            </Stack>

            <RingProgress
              size={160}
              thickness={16}
              sections={[
                { value: (criticalCount / redFlags.length) * 100, color: 'red', tooltip: 'Crítico' },
                { value: (highCount / redFlags.length) * 100, color: 'orange', tooltip: 'Alto' },
                { value: (mediumCount / redFlags.length) * 100, color: 'yellow', tooltip: 'Medio' }
              ]}
              label={
                <div style={{ textAlign: 'center' }}>
                  <Text size="xl" fw={700}>{redFlags.length}</Text>
                  <Text size="xs" c="dimmed">Total</Text>
                </div>
              }
            />
          </Group>
        </Card>
      )}

      {/* Distribución por sección */}
      {stats && stats.by_section && Object.keys(stats.by_section).length > 0 && (
        <Grid gutter="md">
          <Grid.Col span={6}>
            <Card withBorder p="md">
              <Group gap="xs" mb="md">
                <IconTrendingUp size={20} />
                <Text size="lg" fw={600}>Archivos por Sección</Text>
              </Group>
              
              <Stack gap="xs">
                {Object.entries(stats.by_section)
                  .sort((a, b) => b[1] - a[1])
                  .map(([section, count]) => (
                    <Group key={section} justify="space-between">
                      <Text size="sm">{getSectionName(parseInt(section))}</Text>
                      <Badge variant="filled">{count}</Badge>
                    </Group>
                  ))}
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={6}>
            <Card withBorder p="md">
              <Group gap="xs" mb="md">
                <IconFileAnalytics size={20} />
                <Text size="lg" fw={600}>Archivos por Mes</Text>
              </Group>
              
              <Stack gap="xs">
                {Object.entries(stats.by_month)
                  .sort((a, b) => a[0].localeCompare(b[0]))
                  .map(([month, count]) => (
                    <Group key={month} justify="space-between">
                      <Text size="sm">{formatMonth(month)}</Text>
                      <Badge variant="filled">{count}</Badge>
                    </Group>
                  ))}
              </Stack>
            </Card>
          </Grid.Col>
        </Grid>
      )}

      {/* Top Red Flags */}
      {redFlags.length > 0 && (
        <Card withBorder p="md">
          <Group gap="xs" mb="md">
            <IconAlertTriangle size={20} />
            <Text size="lg" fw={600}>Red Flags Detectadas</Text>
          </Group>
          
          <ScrollArea h={300}>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Severidad</Table.Th>
                  <Table.Th>Categoría</Table.Th>
                  <Table.Th>Documento</Table.Th>
                  <Table.Th>Descripción</Table.Th>
                  <Table.Th>Confianza</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {redFlags.slice(0, 10).map((flag, idx) => (
                  <Table.Tr key={idx}>
                    <Table.Td>
                      <Badge 
                        color={getSeverityColor(flag.severity)}
                        variant="filled"
                        size="sm"
                      >
                        {flag.severity}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{flag.category}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" style={{ fontFamily: 'monospace' }}>
                        {flag.document}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" lineClamp={2}>
                        {flag.description}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge color="blue" variant="light">
                        {(flag.confidence * 100).toFixed(0)}%
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
          
          {redFlags.length > 10 && (
            <Text size="xs" c="dimmed" mt="xs" ta="center">
              Mostrando 10 de {redFlags.length} red flags
            </Text>
          )}
        </Card>
      )}

      {/* Estado vacío */}
      {(!stats || stats.total_files === 0) && (
        <Alert color="blue" icon={<IconFileAnalytics size={20} />}>
          <Text size="sm">
            No hay datos disponibles. Descarga boletines para comenzar el análisis.
          </Text>
        </Alert>
      )}
    </Stack>
  );
};

export default DSLabDashboard;

