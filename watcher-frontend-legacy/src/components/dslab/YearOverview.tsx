import React from 'react';
import {
  Card,
  Group,
  Text,
  Stack,
  Grid,
  Progress,
  Badge,
  SimpleGrid,
  RingProgress,
  Center,
  Divider
} from '@mantine/core';
import {
  IconCalendar,
  IconFileText,
  IconDatabase,
  IconCloudDownload,
  IconChartBar
} from '@tabler/icons-react';

interface MonthSummary {
  month: number;
  year: number;
  total_available: number;
  total_downloaded: number;
  total_size_mb: number;
  completion_percentage: number;
}

interface YearOverviewProps {
  year: number;
  months: MonthSummary[];
  onMonthClick?: (year: number, month: number) => void;
}

const MONTH_NAMES = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
];

const MONTH_NAMES_FULL = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

const YearOverview: React.FC<YearOverviewProps> = ({ year, months, onMonthClick }) => {
  
  // Manejar caso de datos undefined o vacíos
  if (!months || months.length === 0) {
    return (
      <Card withBorder padding="xl">
        <Center style={{ minHeight: 200 }}>
          <Stack align="center" gap="md">
            <IconCalendar size={48} style={{ opacity: 0.3 }} />
            <Text c="dimmed">No hay datos disponibles para este año</Text>
            <Text size="sm" c="dimmed">El backend debe estar corriendo para cargar los datos</Text>
          </Stack>
        </Center>
      </Card>
    );
  }
  
  // Calcular estadísticas del año
  const yearStats = months.reduce((acc, month) => ({
    total_available: acc.total_available + (month?.total_available || 0),
    total_downloaded: acc.total_downloaded + (month?.total_downloaded || 0),
    total_size_mb: acc.total_size_mb + (month?.total_size_mb || 0)
  }), {
    total_available: 0,
    total_downloaded: 0,
    total_size_mb: 0
  });
  
  const yearCompletionPercentage = yearStats.total_available > 0
    ? (yearStats.total_downloaded / yearStats.total_available) * 100
    : 0;
  
  const getMonthColor = (percentage: number) => {
    if (percentage === 0) return 'red';
    if (percentage < 50) return 'orange';
    if (percentage < 100) return 'yellow';
    return 'teal';
  };
  
  return (
    <Stack gap="md">
      {/* Resumen General del Año */}
      <Card withBorder p="lg" shadow="sm">
        <Group justify="space-between" align="flex-start">
          <div>
            <Group gap="xs" mb="sm">
              <IconCalendar size={28} />
              <Text size="xl" fw={700}>Resumen Anual {year}</Text>
            </Group>
            <Text size="sm" c="dimmed">
              Vista general de todos los boletines del año
            </Text>
          </div>
          
          <Center>
            <RingProgress
              size={120}
              thickness={14}
              sections={[
                { value: yearCompletionPercentage, color: getMonthColor(yearCompletionPercentage) }
              ]}
              label={
                <div style={{ textAlign: 'center' }}>
                  <Text size="xl" fw={700}>
                    {yearCompletionPercentage.toFixed(0)}%
                  </Text>
                  <Text size="xs" c="dimmed">
                    completo
                  </Text>
                </div>
              }
            />
          </Center>
        </Group>
        
        <Divider my="md" />
        
        <SimpleGrid cols={4} spacing="lg">
          <div>
            <Group gap="xs" mb="xs">
              <IconFileText size={18} color="#228be6" />
              <Text size="xs" c="dimmed">Disponibles</Text>
            </Group>
            <Text size="xl" fw={700}>{yearStats.total_available}</Text>
            <Text size="xs" c="dimmed">archivos</Text>
          </div>
          
          <div>
            <Group gap="xs" mb="xs">
              <IconCloudDownload size={18} color="#12b886" />
              <Text size="xs" c="dimmed">Descargados</Text>
            </Group>
            <Text size="xl" fw={700} c="teal">{yearStats.total_downloaded}</Text>
            <Text size="xs" c="dimmed">archivos</Text>
          </div>
          
          <div>
            <Group gap="xs" mb="xs">
              <IconDatabase size={18} color="#fd7e14" />
              <Text size="xs" c="dimmed">Tamaño Total</Text>
            </Group>
            <Text size="xl" fw={700}>{yearStats.total_size_mb.toFixed(1)}</Text>
            <Text size="xs" c="dimmed">MB</Text>
          </div>
          
          <div>
            <Group gap="xs" mb="xs">
              <IconChartBar size={18} color="#fa5252" />
              <Text size="xs" c="dimmed">Pendientes</Text>
            </Group>
            <Text size="xl" fw={700} c="red">
              {yearStats.total_available - yearStats.total_downloaded}
            </Text>
            <Text size="xs" c="dimmed">archivos</Text>
          </div>
        </SimpleGrid>
      </Card>
      
      {/* Grid de Meses */}
      <Text size="lg" fw={600} mt="md">Progreso por Mes</Text>
      
      <Grid gutter="md">
        {Array.from({ length: 12 }, (_, idx) => {
          const monthNumber = idx + 1;
          const monthData = months.find(m => m.month === monthNumber);
          
          const downloaded = monthData?.total_downloaded || 0;
          const available = monthData?.total_available || 0;
          const size = monthData?.total_size_mb || 0;
          const percentage = monthData?.completion_percentage || 0;
          
          return (
            <Grid.Col key={monthNumber} span={3}>
              <Card
                withBorder
                p="md"
                style={{
                  cursor: available > 0 ? 'pointer' : 'default',
                  transition: 'all 0.2s ease',
                  opacity: available === 0 ? 0.6 : 1
                }}
                onClick={() => available > 0 && onMonthClick?.(year, monthNumber)}
              >
                <Stack gap="xs">
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text size="lg" fw={600}>{MONTH_NAMES[idx]}</Text>
                      <Text size="xs" c="dimmed">{year}</Text>
                    </div>
                    
                    {percentage > 0 && (
                      <Badge
                        color={getMonthColor(percentage)}
                        variant={percentage === 100 ? 'filled' : 'light'}
                        size="lg"
                      >
                        {percentage.toFixed(0)}%
                      </Badge>
                    )}
                  </Group>
                  
                  {available > 0 ? (
                    <>
                      <Progress
                        value={percentage}
                        color={getMonthColor(percentage)}
                        size="sm"
                        striped={percentage > 0 && percentage < 100}
                      />
                      
                      <Group justify="space-between">
                        <Text size="sm">
                          <strong>{downloaded}</strong>
                          <Text component="span" c="dimmed"> / {available}</Text>
                        </Text>
                        <Text size="xs" c="dimmed">
                          {size.toFixed(1)} MB
                        </Text>
                      </Group>
                    </>
                  ) : (
                    <Text size="sm" c="dimmed" ta="center" py="md">
                      Sin datos
                    </Text>
                  )}
                </Stack>
              </Card>
            </Grid.Col>
          );
        })}
      </Grid>
    </Stack>
  );
};

export default YearOverview;

