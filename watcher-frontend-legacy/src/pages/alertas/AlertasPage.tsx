import { Container, Title, Text, Stack, Group, Alert, Loader } from '@mantine/core';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { IconAlertCircle } from '@tabler/icons-react';
import { useUserMode } from '../../contexts/UserModeContext';
import { ModeToggle } from '../../components/mode/ModeToggle';
import { AlertasStatsComponent } from './components/AlertasStats';
import { AlertasFilters } from './components/AlertasFilters';
import { AlertasList } from './components/AlertasList';
import { getAlertas, getAlertasStats } from '../../services/api';
import type { Alerta, AlertasStats } from '../../types/alertas';

export function AlertasPage() {
  const navigate = useNavigate();
  const { isCiudadano } = useUserMode();
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [stats, setStats] = useState<AlertasStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<{
    nivel_severidad?: string;
    tipo_alerta?: string;
    organismo?: string;
    estado?: string;
  }>({});

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const [alertasResponse, statsResponse] = await Promise.all([
        getAlertas({ ...filters, limit: 100 }),
        getAlertasStats()
      ]);
      
      setAlertas(alertasResponse.alertas);
      setStats(statsResponse);
    } catch (err) {
      setError('Error cargando alertas: ' + (err as Error).message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string | undefined) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleResetFilters = () => {
    setFilters({});
  };

  const handleViewDetails = (id: number) => {
    navigate(`/alertas/${id}`);
  };

  // Get unique values for filters
  const organismos = Array.from(new Set(alertas.map(a => a.organismo))).sort();
  const tipos = Array.from(new Set(alertas.map(a => a.tipo_alerta))).sort();

  return (
    <Container size="xl">
      <Stack gap="xl">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={1} mb="xs">
              {isCiudadano ? 'Alertas de Irregularidades' : 'Sistema de Alertas - Gestión'}
            </Title>
            <Text size="lg" c="dimmed">
              {isCiudadano 
                ? 'Situaciones que requieren atención ciudadana' 
                : '15 tipos de alertas configurables para auditoría fiscal'}
            </Text>
          </div>
          <ModeToggle />
        </Group>

        {/* Error Alert */}
        {error && (
          <Alert color="red" title="Error" icon={<IconAlertCircle size="1rem" />}>
            {error}
          </Alert>
        )}

        {/* Stats */}
        {stats && !loading && (
          <AlertasStatsComponent stats={stats} />
        )}

        {/* Filters and List */}
        {loading ? (
          <Group justify="center" py="xl">
            <Loader size="lg" />
          </Group>
        ) : (
          <Group align="flex-start" gap="lg">
            <div style={{ width: '300px', flexShrink: 0 }}>
              <AlertasFilters
                filters={filters}
                onFilterChange={handleFilterChange}
                onReset={handleResetFilters}
                organismos={organismos}
                tipos={tipos}
              />
            </div>

            <div style={{ flex: 1 }}>
              <AlertasList
                alertas={alertas}
                onViewDetails={handleViewDetails}
              />
            </div>
          </Group>
        )}
      </Stack>
    </Container>
  );
}

