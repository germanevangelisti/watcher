import { Container, Title, Text, Stack, Group, Alert, Loader, Pagination } from '@mantine/core';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { IconAlertCircle } from '@tabler/icons-react';
import { useUserMode } from '../../contexts/UserModeContext';
import { ModeToggle } from '../../components/mode/ModeToggle';
import { PresupuestoFilters } from './components/PresupuestoFilters';
import { ProgramasList } from './components/ProgramasList';
import { getProgramas } from '../../services/api';
import type { Programa } from '../../types/presupuesto';

export function PresupuestoPage() {
  const navigate = useNavigate();
  const { isCiudadano } = useUserMode();
  const [programas, setProgramas] = useState<Programa[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<{
    ejercicio?: number;
    organismo?: string;
  }>({});

  const pageSize = 10;

  useEffect(() => {
    loadData();
  }, [filters, page]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await getProgramas({ 
        ...filters, 
        skip: (page - 1) * pageSize,
        limit: pageSize 
      });
      
      setProgramas(response.programas);
      setTotal(response.total);
    } catch (err) {
      setError('Error cargando programas: ' + (err as Error).message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: number | string | undefined) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
    setPage(1); // Reset to first page on filter change
  };

  const handleResetFilters = () => {
    setFilters({});
    setPage(1);
  };

  const handleViewDetails = (id: number) => {
    navigate(`/presupuesto/${id}`);
  };

  // Get unique values for filters
  const organismos = Array.from(new Set(programas.map(p => p.organismo))).sort();
  const totalPages = Math.ceil(total / pageSize);

  return (
    <Container size="xl">
      <Stack gap="xl">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={1} mb="xs">
              {isCiudadano ? 'Explorador de Presupuesto' : 'Gestión de Programas Presupuestarios'}
            </Title>
            <Text size="lg" c="dimmed">
              {isCiudadano 
                ? 'Explora cómo se distribuye y ejecuta el presupuesto provincial' 
                : 'Programas presupuestarios con seguimiento de ejecución'}
            </Text>
            <Text size="sm" c="dimmed" mt="xs">
              Mostrando {programas.length} de {total} programas
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

        {/* Filters and List */}
        {loading ? (
          <Group justify="center" py="xl">
            <Loader size="lg" />
          </Group>
        ) : (
          <Group align="flex-start" gap="lg">
            <div style={{ width: '300px', flexShrink: 0 }}>
              <PresupuestoFilters
                filters={filters}
                onFilterChange={handleFilterChange}
                onReset={handleResetFilters}
                organismos={organismos}
              />
            </div>

            <div style={{ flex: 1 }}>
              <ProgramasList
                programas={programas}
                onViewDetails={handleViewDetails}
              />

              {totalPages > 1 && (
                <Group justify="center" mt="xl">
                  <Pagination 
                    total={totalPages} 
                    value={page} 
                    onChange={setPage}
                  />
                </Group>
              )}
            </div>
          </Group>
        )}
      </Stack>
    </Container>
  );
}

