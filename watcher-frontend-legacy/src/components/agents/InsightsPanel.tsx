import { useState, useEffect } from 'react';
import { 
  Paper, 
  Text, 
  Stack, 
  Group,
  SimpleGrid,
  RingProgress,
  Badge,
  Title,
  ScrollArea,
  Loader,
  Alert
} from '@mantine/core';
import { 
  IconAlertTriangle, 
  IconFileText, 
  IconFlag, 
  IconChartBar,
  IconInfoCircle
} from '@tabler/icons-react';

interface Statistics {
  total_documents: number;
  total_analyzed: number;
  total_results: number;
  high_risk_documents: number;
  total_red_flags: number;
  high_severity_flags: number;
  avg_transparency_score: number;
  documents_by_period: Array<{
    year: number;
    month: number;
    count: number;
  }>;
}

interface TopRiskDocument {
  document_id: number;
  filename: string;
  year: number;
  month: number;
  day: number;
  transparency_score: number;
  num_red_flags: number;
  risk_level: string;
}

export function InsightsPanel() {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [topRisk, setTopRisk] = useState<TopRiskDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInsights();
    // Refrescar cada 30 segundos
    const interval = setInterval(fetchInsights, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchInsights = async () => {
    try {
      setError(null);
      
      // Fetch statistics
      const statsResponse = await fetch('http://localhost:8001/api/v1/agents/insights/statistics');
      if (!statsResponse.ok) throw new Error('Failed to fetch statistics');
      const statsData = await statsResponse.json();
      setStatistics(statsData);

      // Fetch top risk documents
      const riskResponse = await fetch('http://localhost:8001/api/v1/agents/insights/top-risk?limit=5');
      if (!riskResponse.ok) throw new Error('Failed to fetch top risk documents');
      const riskData = await riskResponse.json();
      setTopRisk(riskData.documents || []);
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching insights:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Paper p="md" withBorder>
        <Group justify="center" py="xl">
          <Loader size="lg" />
          <Text>Cargando insights...</Text>
        </Group>
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert icon={<IconInfoCircle size={16} />} title="Error" color="red">
        No se pudieron cargar los insights: {error}
      </Alert>
    );
  }

  if (!statistics) {
    return (
      <Alert icon={<IconInfoCircle size={16} />} title="Sin datos" color="gray">
        No hay datos disponibles
      </Alert>
    );
  }

  const transparencyPercentage = Math.round(statistics.avg_transparency_score);
  const analysisPercentage = statistics.total_documents > 0 
    ? Math.round((statistics.total_analyzed / statistics.total_documents) * 100)
    : 0;

  return (
    <Stack gap="md">
      {/* Métricas Principales */}
      <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
        <Paper p="md" withBorder>
          <Group gap="xs">
            <IconFileText size={20} color="blue" />
            <div>
              <Text size="xs" c="dimmed">Total Documentos</Text>
              <Text size="xl" fw={700}>{statistics.total_documents.toLocaleString()}</Text>
              <Text size="xs" c="dimmed">
                {statistics.total_analyzed} analizados ({analysisPercentage}%)
              </Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group gap="xs">
            <IconFlag size={20} color="red" />
            <div>
              <Text size="xs" c="dimmed">Red Flags</Text>
              <Text size="xl" fw={700}>{statistics.total_red_flags.toLocaleString()}</Text>
              <Text size="xs" c="red">
                {statistics.high_severity_flags} alta severidad
              </Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group gap="xs">
            <IconAlertTriangle size={20} color="orange" />
            <div>
              <Text size="xs" c="dimmed">Alto Riesgo</Text>
              <Text size="xl" fw={700}>{statistics.high_risk_documents}</Text>
              <Text size="xs" c="dimmed">
                documentos críticos
              </Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group gap="xs" align="center">
            <RingProgress
              size={60}
              thickness={6}
              sections={[{ value: transparencyPercentage, color: transparencyPercentage > 70 ? 'green' : transparencyPercentage > 50 ? 'yellow' : 'red' }]}
              label={
                <Text size="xs" ta="center" fw={700}>
                  {transparencyPercentage}
                </Text>
              }
            />
            <div>
              <Text size="xs" c="dimmed">Transparencia</Text>
              <Text size="sm" fw={600}>
                Score Promedio
              </Text>
            </div>
          </Group>
        </Paper>
      </SimpleGrid>

      {/* Top Documentos de Riesgo */}
      <Paper p="md" withBorder>
        <Group mb="md">
          <IconAlertTriangle size={20} />
          <Title order={4}>🔴 Top Documentos de Alto Riesgo</Title>
        </Group>
        
        {topRisk.length === 0 ? (
          <Text c="dimmed" ta="center" py="md">
            No hay documentos de alto riesgo en este momento
          </Text>
        ) : (
          <ScrollArea h={200}>
            <Stack gap="xs">
              {topRisk.map((doc, index) => (
                <Paper key={doc.document_id} p="sm" withBorder bg={index === 0 ? 'red.0' : undefined}>
                  <Group justify="space-between" wrap="nowrap">
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Group gap="xs">
                        <Badge size="sm" color="red">#{index + 1}</Badge>
                        <Text size="sm" fw={500} truncate>
                          {doc.filename}
                        </Text>
                      </Group>
                      <Text size="xs" c="dimmed">
                        {doc.year}-{String(doc.month).padStart(2, '0')}-{String(doc.day).padStart(2, '0')}
                      </Text>
                    </div>
                    <Group gap="md" wrap="nowrap">
                      <div>
                        <Text size="xs" c="dimmed" ta="right">Score</Text>
                        <Text size="sm" fw={600} c={doc.transparency_score < 50 ? 'red' : 'orange'}>
                          {doc.transparency_score.toFixed(1)}
                        </Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed" ta="right">Red Flags</Text>
                        <Badge size="sm" color="red">{doc.num_red_flags}</Badge>
                      </div>
                    </Group>
                  </Group>
                </Paper>
              ))}
            </Stack>
          </ScrollArea>
        )}
      </Paper>

      {/* Distribución por Período */}
      <Paper p="md" withBorder>
        <Group mb="md">
          <IconChartBar size={20} />
          <Title order={4}>📅 Documentos por Período (2025)</Title>
        </Group>
        <ScrollArea h={150}>
          <Stack gap="xs">
            {statistics.documents_by_period.slice(-6).map((period) => {
              const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
              const percentage = statistics.total_documents > 0 
                ? (period.count / statistics.total_documents) * 100 
                : 0;
              
              return (
                <Group key={`${period.year}-${period.month}`} gap="xs">
                  <Text size="sm" w={60}>
                    {monthNames[period.month - 1]} {period.year}
                  </Text>
                  <div style={{ flex: 1, background: '#e9ecef', borderRadius: 4, height: 24, position: 'relative', overflow: 'hidden' }}>
                    <div 
                      style={{ 
                        background: 'linear-gradient(90deg, #4c6ef5, #5c7cfa)', 
                        height: '100%', 
                        width: `${percentage}%`,
                        transition: 'width 0.3s ease'
                      }} 
                    />
                    <Text 
                      size="xs" 
                      fw={500} 
                      style={{ 
                        position: 'absolute', 
                        top: '50%', 
                        left: 8, 
                        transform: 'translateY(-50%)',
                        color: percentage > 50 ? 'white' : 'black'
                      }}
                    >
                      {period.count} docs
                    </Text>
                  </div>
                </Group>
              );
            })}
          </Stack>
        </ScrollArea>
      </Paper>
    </Stack>
  );
}





