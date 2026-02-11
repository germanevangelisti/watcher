import React, { useState, useEffect } from 'react';
import {
  Card,
  Group,
  Text,
  Badge,
  Button,
  Stack,
  Grid,
  TextInput,
  Select,
  Loader,
  Alert,
  ActionIcon,
  Tooltip,
  Pagination,
  Flex
} from '@mantine/core';
import {
  IconSearch,
  IconCalendar,
  IconFlag,
  IconFileText,
  IconAlertTriangle,
  IconDownload,
  IconAnalyze
} from '@tabler/icons-react';

interface BoletinInfo {
  filename: string;
  date: string;
  section: number;
  display_name: string;
  file_size: number;
  last_modified: string;
  is_critical?: boolean;
  red_flags_count?: number;
}

interface BoletinesListProps {
  onSelectBoletin: (filename: string) => void;
  selectedBoletin?: string;
}

const BoletinesList: React.FC<BoletinesListProps> = ({ 
  onSelectBoletin, 
  selectedBoletin 
}) => {
  const [boletines, setBoletines] = useState<BoletinInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sectionFilter, setSectionFilter] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [stats, setStats] = useState<any>(null);
  
  const itemsPerPage = 15;

  const sectionOptions = [
    { value: '1', label: '1ª Sección - Designaciones y Decretos' },
    { value: '2', label: '2ª Sección - Compras y Contrataciones' },
    { value: '3', label: '3ª Sección - Subsidios y Transferencias' },
    { value: '4', label: '4ª Sección - Obras Públicas' },
    { value: '5', label: '5ª Sección - Notificaciones Judiciales' }
  ];

  useEffect(() => {
    loadBoletines();
    loadStats();
  }, [sectionFilter]);

  const loadBoletines = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        month: '8',
        year: '2025',
        include_red_flags: 'true'
      });
      
      if (sectionFilter) {
        params.append('section', sectionFilter);
      }

      const response = await fetch(`/api/v1/boletines/list?${params}`);
      
      if (!response.ok) {
        throw new Error('Error cargando boletines');
      }

      const data = await response.json();
      setBoletines(data.boletines);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
      setBoletines([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('/api/v1/boletines/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.warn('Error cargando estadísticas:', err);
    }
  };

  // Filtrar boletines por término de búsqueda
  const filteredBoletines = boletines.filter(boletin =>
    boletin.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    boletin.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Paginación
  const totalPages = Math.ceil(filteredBoletines.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedBoletines = filteredBoletines.slice(startIndex, startIndex + itemsPerPage);

  const getSectionBadgeColor = (section: number) => {
    const colors = {
      1: 'blue',
      2: 'orange', 
      3: 'green',
      4: 'purple',
      5: 'gray'
    };
    return colors[section] || 'gray';
  };

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <Card withBorder p="xl" style={{ textAlign: 'center' }}>
        <Loader size="lg" />
        <Text mt="md" c="dimmed">Cargando boletines de agosto 2025...</Text>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert icon={<IconAlertTriangle size={16} />} title="Error" color="red">
        {error}
        <Button mt="sm" size="sm" onClick={loadBoletines}>
          Reintentar
        </Button>
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      {/* Header con estadísticas */}
      <Card withBorder p="md">
        <Group justify="space-between" align="center">
          <div>
            <Text size="lg" fw={600}>
              Boletines Oficiales - Agosto 2025
            </Text>
            <Text size="sm" c="dimmed">
              {filteredBoletines.length} de {boletines.length} boletines
              {stats && ` • ${stats.total_size_mb} MB total`}
            </Text>
          </div>
          
          {stats && (
            <Group gap="xs">
              <Badge color="red" variant="light">
                {boletines.filter(b => b.is_critical).length} críticos
              </Badge>
              <Badge color="orange" variant="light">
                {boletines.filter(b => b.red_flags_count > 0).length} con alertas
              </Badge>
            </Group>
          )}
        </Group>
      </Card>

      {/* Filtros */}
      <Card withBorder p="md">
        <Grid>
          <Grid.Col span={8}>
            <TextInput
              placeholder="Buscar por fecha o sección..."
              leftSection={<IconSearch size={16} />}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </Grid.Col>
          <Grid.Col span={4}>
            <Select
              placeholder="Filtrar por sección"
              data={sectionOptions}
              value={sectionFilter}
              onChange={setSectionFilter}
              clearable
            />
          </Grid.Col>
        </Grid>
      </Card>

      {/* Lista de boletines */}
      <Stack gap="xs">
        {paginatedBoletines.map((boletin) => (
          <Card
            key={boletin.filename}
            withBorder
            p="md"
            style={{
              backgroundColor: selectedBoletin === boletin.filename ? '#f8f9fa' : undefined,
              borderColor: selectedBoletin === boletin.filename ? '#228be6' : undefined,
              cursor: 'pointer'
            }}
            onClick={() => onSelectBoletin(boletin.filename)}
          >
            <Group justify="space-between" align="flex-start">
              <div style={{ flex: 1 }}>
                <Group gap="xs" mb="xs">
                  <Badge 
                    color={getSectionBadgeColor(boletin.section)}
                    variant="filled"
                    size="sm"
                  >
                    {boletin.section}ª Sección
                  </Badge>
                  
                  {boletin.is_critical && (
                    <Badge color="red" variant="filled" size="sm">
                      <IconAlertTriangle size={12} style={{ marginRight: 4 }} />
                      CRÍTICO
                    </Badge>
                  )}
                  
                  {boletin.red_flags_count > 0 && (
                    <Badge color="orange" variant="light" size="sm">
                      <IconFlag size={12} style={{ marginRight: 4 }} />
                      {boletin.red_flags_count} alertas
                    </Badge>
                  )}
                </Group>

                <Text fw={500} size="sm" mb="xs">
                  {boletin.display_name}
                </Text>

                <Group gap="md">
                  <Group gap="xs">
                    <IconCalendar size={14} />
                    <Text size="xs" c="dimmed">
                      {formatDate(boletin.date)}
                    </Text>
                  </Group>
                  
                  <Group gap="xs">
                    <IconFileText size={14} />
                    <Text size="xs" c="dimmed">
                      {formatFileSize(boletin.file_size)}
                    </Text>
                  </Group>
                  
                  <Text size="xs" c="dimmed">
                    {boletin.filename}
                  </Text>
                </Group>
              </div>

              <Group gap="xs">
                <Tooltip label="Analizar con Red Flags">
                  <ActionIcon
                    variant="filled"
                    color="blue"
                    size="lg"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectBoletin(boletin.filename);
                    }}
                  >
                    <IconAnalyze size={16} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            </Group>
          </Card>
        ))}
      </Stack>

      {/* Paginación */}
      {totalPages > 1 && (
        <Flex justify="center" mt="md">
          <Pagination
            total={totalPages}
            value={currentPage}
            onChange={setCurrentPage}
            size="sm"
          />
        </Flex>
      )}

      {filteredBoletines.length === 0 && !loading && (
        <Card withBorder p="xl" style={{ textAlign: 'center' }}>
          <Text c="dimmed">
            No se encontraron boletines que coincidan con los filtros seleccionados.
          </Text>
        </Card>
      )}
    </Stack>
  );
};

export default BoletinesList;
