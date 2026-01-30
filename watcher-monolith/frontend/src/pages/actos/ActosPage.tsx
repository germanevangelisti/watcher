import { Container, Title, Text, Stack, Group, Alert, Loader, Grid } from '@mantine/core';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { IconAlertCircle, IconFileText, IconAlertTriangle, IconInfoCircle } from '@tabler/icons-react';
import { useUserMode } from '../../contexts/UserModeContext';
import { ModeToggle } from '../../components/mode/ModeToggle';
import { StatsCard } from '../../components/shared/StatsCard';
import { ActosFilters } from './components/ActosFilters';
import { ActosList } from './components/ActosList';
import { getActos } from '../../services/api';
import type { Acto } from '../../types/actos';

export function ActosPage() {
  const navigate = useNavigate();
  const { isCiudadano } = useUserMode();
  const [actos, setActos] = useState<Acto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<{
    tipo_acto?: string;
    organismo?: string;
    nivel_riesgo?: string;
  }>({});

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await getActos({ ...filters, limit: 100 });
      setActos(response.actos);
    } catch (err) {
      setError('Error cargando actos: ' + (err as Error).message);
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
    navigate(`/actos/${id}`);
  };

  // Calculate stats
  const totalActos = actos.length;
  const actosAlto = actos.filter(a => a.nivel_riesgo === 'ALTO').length;
  const actosMedio = actos.filter(a => a.nivel_riesgo === 'MEDIO').length;
  const actosBajo = actos.filter(a => a.nivel_riesgo === 'BAJO').length;

  // Get unique values for filters
  const organismos = Array.from(new Set(actos.map(a => a.organismo))).sort();
  const tipos = Array.from(new Set(actos.map(a => a.tipo_acto))).sort();

  return (
    <Container size="xl">
      <Stack gap="xl">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={1} mb="xs">
              {isCiudadano ? 'Actos Administrativos' : 'Gestión de Actos Administrativos'}
            </Title>
            <Text size="lg" c="dimmed">
              {isCiudadano 
                ? 'Decretos, resoluciones y licitaciones oficiales' 
                : 'Actos extraídos de boletines oficiales con vinculación presupuestaria'}
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
        {!loading && (
          <Grid>
            <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
              <StatsCard
                title="Total Actos"
                value={totalActos}
                icon={IconFileText}
                color="blue"
              />
            </Grid.Col>
            
            <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
              <StatsCard
                title="Riesgo Alto"
                value={actosAlto}
                icon={IconAlertTriangle}
                color="red"
              />
            </Grid.Col>
            
            <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
              <StatsCard
                title="Riesgo Medio"
                value={actosMedio}
                icon={IconAlertCircle}
                color="yellow"
              />
            </Grid.Col>
            
            <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
              <StatsCard
                title="Riesgo Bajo"
                value={actosBajo}
                icon={IconInfoCircle}
                color="green"
              />
            </Grid.Col>
          </Grid>
        )}

        {/* Filters and List */}
        {loading ? (
          <Group justify="center" py="xl">
            <Loader size="lg" />
          </Group>
        ) : (
          <Group align="flex-start" gap="lg">
            <div style={{ width: '300px', flexShrink: 0 }}>
              <ActosFilters
                filters={filters}
                onFilterChange={handleFilterChange}
                onReset={handleResetFilters}
                organismos={organismos}
                tipos={tipos}
              />
            </div>

            <div style={{ flex: 1 }}>
              <ActosList
                actos={actos}
                onViewDetails={handleViewDetails}
              />
            </div>
          </Group>
        )}
      </Stack>
    </Container>
  );
}

