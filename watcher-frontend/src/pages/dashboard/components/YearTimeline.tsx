import { Group, Badge, Tooltip, Text, Progress, Stack } from '@mantine/core';
import { IconCheck, IconClock, IconX, IconAlertCircle } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { getMonthlyStats } from '../../../services/api';

interface MonthlyStat {
  month: string; // YYYYMM format
  total: number;
  completed: number;
  pending: number;
  failed: number;
  processing: number;
}

const MONTHS_2025 = [
  { key: '202501', label: 'Ene', full: 'Enero' },
  { key: '202502', label: 'Feb', full: 'Febrero' },
  { key: '202503', label: 'Mar', full: 'Marzo' },
  { key: '202504', label: 'Abr', full: 'Abril' },
  { key: '202505', label: 'May', full: 'Mayo' },
  { key: '202506', label: 'Jun', full: 'Junio' },
  { key: '202507', label: 'Jul', full: 'Julio' },
  { key: '202508', label: 'Ago', full: 'Agosto' },
  { key: '202509', label: 'Sep', full: 'Septiembre' },
  { key: '202510', label: 'Oct', full: 'Octubre' },
  { key: '202511', label: 'Nov', full: 'Noviembre' },
  { key: '202512', label: 'Dic', full: 'Diciembre' },
];

export function YearTimeline() {
  const [monthlyStats, setMonthlyStats] = useState<MonthlyStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMonthlyStats();
  }, []);

  const loadMonthlyStats = async () => {
    try {
      setLoading(true);
      const data = await getMonthlyStats();
      setMonthlyStats(data.monthly_stats || []);
    } catch (error) {
      console.error('Error loading monthly stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMonthData = (monthKey: string): MonthlyStat | null => {
    return monthlyStats.find(stat => stat.month === monthKey) || null;
  };

  const getMonthStatus = (monthData: MonthlyStat | null) => {
    if (!monthData || monthData.total === 0) {
      return { status: 'empty', color: 'gray', label: 'Sin datos', icon: null };
    }
    
    if (monthData.processing > 0) {
      return { status: 'processing', color: 'blue', label: 'Procesando', icon: IconClock };
    }
    
    if (monthData.failed > 0 && monthData.completed === 0) {
      return { status: 'failed', color: 'red', label: 'Error', icon: IconX };
    }
    
    if (monthData.completed === monthData.total) {
      return { status: 'completed', color: 'green', label: 'Completo', icon: IconCheck };
    }
    
    if (monthData.completed > 0) {
      return { status: 'partial', color: 'yellow', label: 'Parcial', icon: IconAlertCircle };
    }
    
    if (monthData.pending > 0) {
      return { status: 'pending', color: 'orange', label: 'Pendiente', icon: IconClock };
    }
    
    return { status: 'empty', color: 'gray', label: 'Sin datos', icon: null };
  };

  const getMonthProgress = (monthData: MonthlyStat | null): number => {
    if (!monthData || monthData.total === 0) return 0;
    return (monthData.completed / monthData.total) * 100;
  };

  const getTotalProgress = (): number => {
    const totalMonths = MONTHS_2025.length;
    const completedMonths = MONTHS_2025.filter(month => {
      const data = getMonthData(month.key);
      return data && data.completed === data.total && data.total > 0;
    }).length;
    return (completedMonths / totalMonths) * 100;
  };

  const totalProgress = getTotalProgress();
  const completedMonths = MONTHS_2025.filter(month => {
    const data = getMonthData(month.key);
    return data && data.completed === data.total && data.total > 0;
  }).length;

  if (loading) {
    return (
      <Group gap="xs">
        {MONTHS_2025.map(month => (
          <Badge key={month.key} color="gray" variant="light" size="sm">
            {month.label}
          </Badge>
        ))}
      </Group>
    );
  }

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="center">
        <Text size="sm" fw={600}>Progreso 2025</Text>
        <Group gap="xs">
          <Text size="xs" c="dimmed">
            {completedMonths}/12 meses completos
          </Text>
          <Badge color={totalProgress === 100 ? 'green' : totalProgress > 50 ? 'blue' : 'orange'} variant="light">
            {totalProgress.toFixed(0)}%
          </Badge>
        </Group>
      </Group>
      
      <Progress 
        value={totalProgress} 
        size="sm" 
        color={totalProgress === 100 ? 'green' : totalProgress > 50 ? 'blue' : 'orange'}
        style={{ width: '100%' }}
      />

      <Group gap={4} wrap="nowrap" style={{ overflowX: 'auto', paddingBottom: '4px' }}>
        {MONTHS_2025.map((month) => {
          const monthData = getMonthData(month.key);
          const status = getMonthStatus(monthData);
          const progress = getMonthProgress(monthData);
          const StatusIcon = status.icon;

          return (
            <Tooltip
              key={month.key}
              label={
                monthData ? (
                  <Stack gap={4}>
                    <Text size="sm" fw={600}>{month.full} 2025</Text>
                    <Text size="xs">Total: {monthData.total}</Text>
                    <Text size="xs" c="green">Completados: {monthData.completed}</Text>
                    {monthData.pending > 0 && (
                      <Text size="xs" c="orange">Pendientes: {monthData.pending}</Text>
                    )}
                    {monthData.failed > 0 && (
                      <Text size="xs" c="red">Fallidos: {monthData.failed}</Text>
                    )}
                    {monthData.processing > 0 && (
                      <Text size="xs" c="blue">Procesando: {monthData.processing}</Text>
                    )}
                    <Text size="xs" c="dimmed">Progreso: {progress.toFixed(0)}%</Text>
                  </Stack>
                ) : (
                  <Text size="sm">{month.full} 2025 - Sin datos procesados</Text>
                )
              }
              withArrow
              position="top"
            >
              <div style={{ 
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                minWidth: '60px',
                cursor: 'help'
              }}>
                <Badge
                  color={status.color}
                  variant={status.status === 'completed' ? 'filled' : 'light'}
                  size="lg"
                  leftSection={StatusIcon ? <StatusIcon size={14} stroke={2} /> : undefined}
                  style={{ 
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '6px 12px'
                  }}
                >
                  <Text size="xs" fw={600} style={{ lineHeight: 1 }}>{month.label}</Text>
                </Badge>
                {monthData && monthData.total > 0 && status.status !== 'completed' && (
                  <Progress
                    value={progress}
                    size="xs"
                    color={status.color}
                    style={{ width: '100%', marginTop: '4px' }}
                  />
                )}
                {monthData && monthData.total > 0 && status.status === 'completed' && (
                  <div style={{ 
                    width: '100%', 
                    height: '3px', 
                    backgroundColor: 'var(--mantine-color-green-6)',
                    borderRadius: '2px',
                    marginTop: '4px'
                  }} />
                )}
              </div>
            </Tooltip>
          );
        })}
      </Group>
    </Stack>
  );
}

