import { useState, useEffect } from 'react';
import { 
  Paper, 
  Text, 
  Stack, 
  Group,
  Badge,
  ScrollArea,
  Loader,
  Title,
  ActionIcon,
  Tooltip
} from '@mantine/core';
import { IconFlag, IconRefresh, IconAlertCircle } from '@tabler/icons-react';

interface RedFlag {
  id: number;
  flag_type: string;
  severity: string;
  category: string;
  title: string;
  description: string;
  confidence_score: number;
  page_number: number;
  created_at: string;
}

interface RedFlagDistribution {
  total: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  by_type: Record<string, number>;
}

export function RedFlagsMonitor() {
  const [distribution, setDistribution] = useState<RedFlagDistribution | null>(null);
  const [recentFlags, setRecentFlags] = useState<RedFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchRedFlags();
  }, []);

  const fetchRedFlags = async () => {
    const isRefresh = !loading;
    if (isRefresh) setRefreshing(true);
    
    try {
      // Fetch distribution
      const distResponse = await fetch('http://localhost:8001/api/v1/agents/insights/red-flag-distribution');
      if (distResponse.ok) {
        const data = await distResponse.json();
        setDistribution(data);
      }

      // Fetch recent flags (simulated - you'd need to add this endpoint)
      // For now, we'll just show the distribution
      
      setLoading(false);
      setRefreshing(false);
    } catch (error) {
      console.error('Error fetching red flags:', error);
      setLoading(false);
      setRefreshing(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      high: 'red',
      medium: 'orange',
      low: 'yellow'
    };
    return colors[severity] || 'gray';
  };

  if (loading) {
    return (
      <Paper p="md" withBorder>
        <Group justify="center" py="xl">
          <Loader size="md" />
        </Group>
      </Paper>
    );
  }

  return (
    <Paper p="md" withBorder>
      <Group justify="space-between" mb="md">
        <Group>
          <IconFlag size={20} color="red" />
          <Title order={4}>🚩 Red Flags Detectadas</Title>
        </Group>
        <Tooltip label="Actualizar">
          <ActionIcon 
            variant="subtle" 
            onClick={fetchRedFlags}
            loading={refreshing}
          >
            <IconRefresh size={18} />
          </ActionIcon>
        </Tooltip>
      </Group>

      {distribution ? (
        <Stack gap="md">
          <Group>
            <Text size="xl" fw={700}>{distribution.total}</Text>
            <Text size="sm" c="dimmed">red flags totales</Text>
          </Group>

          {/* Por Severidad */}
          <div>
            <Text size="sm" fw={600} mb="xs">Por Severidad</Text>
            <Group gap="xs">
              {Object.entries(distribution.by_severity).map(([severity, count]) => (
                <Badge 
                  key={severity} 
                  size="lg" 
                  color={getSeverityColor(severity)}
                  variant="light"
                >
                  {severity}: {count}
                </Badge>
              ))}
            </Group>
          </div>

          {/* Por Categoría */}
          <div>
            <Text size="sm" fw={600} mb="xs">Por Categoría</Text>
            <Stack gap="xs">
              {Object.entries(distribution.by_category).map(([category, count]) => {
                const percentage = (count / distribution.total) * 100;
                return (
                  <div key={category}>
                    <Group justify="space-between" mb={4}>
                      <Text size="sm">{category}</Text>
                      <Text size="sm" c="dimmed">{count}</Text>
                    </Group>
                    <div style={{ 
                      background: '#e9ecef', 
                      borderRadius: 4, 
                      height: 8,
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        background: 'linear-gradient(90deg, #fa5252, #ff8787)',
                        height: '100%',
                        width: `${percentage}%`,
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                  </div>
                );
              })}
            </Stack>
          </div>

          {/* Top Tipos */}
          <div>
            <Text size="sm" fw={600} mb="xs">Top Tipos de Red Flags</Text>
            <ScrollArea h={120}>
              <Stack gap="xs">
                {Object.entries(distribution.by_type)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 5)
                  .map(([type, count]) => (
                    <Group key={type} justify="space-between">
                      <Text size="sm" truncate style={{ flex: 1 }}>
                        {type.replace(/_/g, ' ')}
                      </Text>
                      <Badge size="sm" color="red" variant="filled">
                        {count}
                      </Badge>
                    </Group>
                  ))}
              </Stack>
            </ScrollArea>
          </div>
        </Stack>
      ) : (
        <Group justify="center" py="xl">
          <IconAlertCircle size={20} />
          <Text c="dimmed">No hay datos disponibles</Text>
        </Group>
      )}
    </Paper>
  );
}

