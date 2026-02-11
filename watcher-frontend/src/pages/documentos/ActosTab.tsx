import { Stack, Group, Alert, Loader, Grid, Text } from '@mantine/core';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  IconAlertCircle, 
  IconFileText, 
  IconAlertTriangle,
  IconAlertOctagon,
  IconCheck
} from '@tabler/icons-react';
import { StatsCard } from '../../components/shared/StatsCard';
import { ActosFilters } from '../actos/components/ActosFilters';
import { ActosList } from '../actos/components/ActosList';
import { getActos } from '../../services/api';
import type { Acto } from '../../types/actos';

export function ActosTab() {
  const navigate = useNavigate();
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
    navigate(`/documentos/actos/${id}`);
  };

  // Calculate stats
  const totalActos = actos.length;
  const actosAlto = actos.filter(a => a.nivel_riesgo === 'ALTO').length;
  const actosMedio = actos.filter(a => a.nivel_riesgo === 'MEDIO').length;
  const actosBajo = actos.filter(a => a.nivel_riesgo === 'BAJO').length;

  // Get unique values for filters
  const organismos = Array.from(new Set(actos.map(a => a.organismo))).sort();
  const tipos = Array.from(new Set(actos.map(a => a.tipo_acto))).sort();

  if (loading) {
    return (
      <Stack align="center" py="xl">
        <Loader size="lg" />
        <Text>Cargando actos administrativos...</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="xl">
      {error && (
        <Alert icon={<IconAlertCircle size="1rem" />} title="Error" color="red">
          {error}
        </Alert>
      )}

      {/* Stats */}
      <Grid>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatsCard
            title="Total de Actos"
            value={totalActos.toString()}
            icon={IconFileText}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatsCard
            title="Riesgo Alto"
            value={actosAlto.toString()}
            icon={IconAlertOctagon}
            color="red"
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatsCard
            title="Riesgo Medio"
            value={actosMedio.toString()}
            icon={IconAlertTriangle}
            color="yellow"
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
          <StatsCard
            title="Riesgo Bajo"
            value={actosBajo.toString()}
            icon={IconCheck}
            color="green"
          />
        </Grid.Col>
      </Grid>

      {/* Filters */}
      <ActosFilters
        filters={filters}
        organismos={organismos}
        tipos={tipos}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
      />

      {/* List */}
      <ActosList
        actos={actos}
        loading={loading}
        onViewDetails={handleViewDetails}
      />
    </Stack>
  );
}

