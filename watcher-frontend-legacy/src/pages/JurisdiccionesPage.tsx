/**
 * JurisdiccionesPage - Vista Principal de Jurisdicciones
 * 
 * Dashboard organizado jerárquicamente mostrando:
 * - Provincia de Córdoba
 * - Ciudad de Córdoba (Capital)
 * - Municipalidades
 * - Comunas
 */

import React, { useState, useEffect } from 'react';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Paper,
  Tabs,
  Grid,
  Card,
  Badge,
  Loader,
  Button,
  TextInput,
  Select,
  SimpleGrid,
  Box,
  ActionIcon,
  Divider,
  ThemeIcon
} from '@mantine/core';
import {
  IconMapPin,
  IconBuilding,
  IconHome,
  IconUsers,
  IconSearch,
  IconFilter,
  IconChevronRight,
  IconFileText,
  IconAlertCircle
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

interface JurisdiccionStats {
  jurisdiccion_id: number;
  nombre: string;
  tipo: string;
  total_boletines: number;
  total_menciones: number;
  poblacion?: number;
}

interface TipoInfo {
  tipo: string;
  cantidad: number;
  label: string;
}

const JurisdiccionesPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<JurisdiccionStats[]>([]);
  const [tipos, setTipos] = useState<TipoInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>('todos');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDepartamento, setSelectedDepartamento] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch estadísticas
      const statsRes = await fetch('/api/v1/jurisdicciones/stats?limite=100');
      if (!statsRes.ok) throw new Error('Error cargando estadísticas');
      const statsData = await statsRes.json();
      setStats(statsData);
      
      // Fetch tipos disponibles
      const tiposRes = await fetch('/api/v1/jurisdicciones/tipos/disponibles');
      if (tiposRes.ok) {
        const tiposData = await tiposRes.json();
        setTipos(tiposData.tipos || []);
      }
      
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getIconByTipo = (tipo: string, size: number = 20) => {
    switch (tipo) {
      case 'provincia':
        return <IconMapPin size={size} />;
      case 'capital':
        return <IconBuilding size={size} />;
      case 'municipalidad':
        return <IconHome size={size} />;
      case 'comuna':
        return <IconUsers size={size} />;
      default:
        return <IconMapPin size={size} />;
    }
  };

  const getColorByTipo = (tipo: string): string => {
    switch (tipo) {
      case 'provincia':
        return 'blue';
      case 'capital':
        return 'red';
      case 'municipalidad':
        return 'green';
      case 'comuna':
        return 'yellow';
      default:
        return 'gray';
    }
  };

  // Filtrar stats según tab y búsqueda
  const filteredStats = stats.filter(s => {
    const matchesTab = activeTab === 'todos' || s.tipo === activeTab;
    const matchesSearch = !searchTerm || s.nombre.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesTab && matchesSearch;
  });

  // Separar por tipo para mostrar destacados
  const provincia = stats.find(s => s.tipo === 'provincia');
  const capital = stats.find(s => s.tipo === 'capital');
  const municipalidades = stats.filter(s => s.tipo === 'municipalidad');
  const comunas = stats.filter(s => s.tipo === 'comuna');

  // Calcular totales
  const totalBoletines = stats.reduce((acc, s) => acc + s.total_boletines, 0);
  const totalMenciones = stats.reduce((acc, s) => acc + s.total_menciones, 0);

  if (loading) {
    return (
      <Container size="xl" py="xl">
        <Group justify="center" py="xl">
          <Loader size="lg" />
          <Text>Cargando jurisdicciones...</Text>
        </Group>
      </Container>
    );
  }

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        {/* Header */}
        <div>
          <Title order={1} mb="xs">
            Jurisdicciones de Córdoba
          </Title>
          <Text c="dimmed" size="lg">
            Explorar boletines oficiales organizados por jurisdicción
          </Text>
        </div>

        {/* Resumen General */}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
          <Paper p="md" withBorder>
            <Group justify="space-between" mb="xs">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Total Boletines
              </Text>
              <ThemeIcon variant="light" size="lg">
                <IconFileText size={20} />
              </ThemeIcon>
            </Group>
            <Text size="xl" fw={700}>
              {totalBoletines.toLocaleString()}
            </Text>
          </Paper>

          <Paper p="md" withBorder>
            <Group justify="space-between" mb="xs">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Menciones
              </Text>
              <ThemeIcon variant="light" size="lg" color="green">
                <IconAlertCircle size={20} />
              </ThemeIcon>
            </Group>
            <Text size="xl" fw={700} c="green">
              {totalMenciones.toLocaleString()}
            </Text>
          </Paper>

          <Paper p="md" withBorder>
            <Group justify="space-between" mb="xs">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Municipalidades
              </Text>
              <ThemeIcon variant="light" size="lg" color="blue">
                <IconHome size={20} />
              </ThemeIcon>
            </Group>
            <Text size="xl" fw={700}>
              {municipalidades.length}
            </Text>
          </Paper>

          <Paper p="md" withBorder>
            <Group justify="space-between" mb="xs">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Comunas
              </Text>
              <ThemeIcon variant="light" size="lg" color="yellow">
                <IconUsers size={20} />
              </ThemeIcon>
            </Group>
            <Text size="xl" fw={700}>
              {comunas.length}
            </Text>
          </Paper>
        </SimpleGrid>

        {/* Jurisdicciones Principales */}
        <div>
          <Title order={2} size="h3" mb="md">
            Jurisdicciones Principales
          </Title>
          
          <Grid gutter="lg">
            {/* Provincia */}
            {provincia && (
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card
                  p="lg"
                  withBorder
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/jurisdicciones/${provincia.jurisdiccion_id}`)}
                >
                  <Group justify="space-between" mb="md">
                    <Group>
                      <ThemeIcon size="xl" variant="light" color={getColorByTipo('provincia')}>
                        {getIconByTipo('provincia', 24)}
                      </ThemeIcon>
                      <div>
                        <Text fw={600} size="lg">{provincia.nombre}</Text>
                        <Badge size="sm" variant="light" color={getColorByTipo('provincia')}>
                          Boletín Provincial
                        </Badge>
                      </div>
                    </Group>
                    <ActionIcon variant="subtle">
                      <IconChevronRight size={20} />
                    </ActionIcon>
                  </Group>

                  <Divider mb="md" />

                  <SimpleGrid cols={2}>
                    <Box>
                      <Text size="xs" c="dimmed">Boletines</Text>
                      <Text size="xl" fw={700} c="blue">
                        {provincia.total_boletines.toLocaleString()}
                      </Text>
                    </Box>
                    <Box>
                      <Text size="xs" c="dimmed">Menciones</Text>
                      <Text size="xl" fw={700} c="green">
                        {provincia.total_menciones.toLocaleString()}
                      </Text>
                    </Box>
                  </SimpleGrid>
                </Card>
              </Grid.Col>
            )}

            {/* Capital */}
            {capital && (
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card
                  p="lg"
                  withBorder
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/jurisdicciones/${capital.jurisdiccion_id}`)}
                >
                  <Group justify="space-between" mb="md">
                    <Group>
                      <ThemeIcon size="xl" variant="light" color={getColorByTipo('capital')}>
                        {getIconByTipo('capital', 24)}
                      </ThemeIcon>
                      <div>
                        <Text fw={600} size="lg">{capital.nombre}</Text>
                        <Badge size="sm" variant="light" color={getColorByTipo('capital')}>
                          Boletín Municipal
                        </Badge>
                      </div>
                    </Group>
                    <ActionIcon variant="subtle">
                      <IconChevronRight size={20} />
                    </ActionIcon>
                  </Group>

                  <Divider mb="md" />

                  <SimpleGrid cols={2}>
                    <Box>
                      <Text size="xs" c="dimmed">Boletines</Text>
                      <Text size="xl" fw={700} c="blue">
                        {capital.total_boletines.toLocaleString()}
                      </Text>
                    </Box>
                    <Box>
                      <Text size="xs" c="dimmed">Menciones</Text>
                      <Text size="xl" fw={700} c="green">
                        {capital.total_menciones.toLocaleString()}
                      </Text>
                    </Box>
                  </SimpleGrid>
                </Card>
              </Grid.Col>
            )}
          </Grid>
        </div>

        {/* Lista Completa con Tabs */}
        <div>
          <Title order={2} size="h3" mb="md">
            Todas las Jurisdicciones
          </Title>

          <Paper p="md" withBorder>
            {/* Buscador y Filtros */}
            <Group mb="md">
              <TextInput
                placeholder="Buscar jurisdicción..."
                leftSection={<IconSearch size={16} />}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.currentTarget.value)}
                style={{ flex: 1 }}
              />
              <Button
                variant="light"
                leftSection={<IconFilter size={16} />}
                onClick={() => setSearchTerm('')}
              >
                Limpiar
              </Button>
            </Group>

            {/* Tabs por Tipo */}
            <Tabs value={activeTab} onChange={(val) => setActiveTab(val || 'todos')}>
              <Tabs.List>
                <Tabs.Tab value="todos">
                  Todas ({stats.length})
                </Tabs.Tab>
                {tipos.map(tipo => (
                  <Tabs.Tab
                    key={tipo.tipo}
                    value={tipo.tipo}
                    leftSection={getIconByTipo(tipo.tipo, 16)}
                  >
                    {tipo.label} ({tipo.cantidad})
                  </Tabs.Tab>
                ))}
              </Tabs.List>

              <Tabs.Panel value={activeTab} pt="md">
                {filteredStats.length === 0 ? (
                  <Text c="dimmed" ta="center" py="xl">
                    No se encontraron jurisdicciones
                  </Text>
                ) : (
                  <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
                    {filteredStats.map(stat => (
                      <Card
                        key={stat.jurisdiccion_id}
                        p="md"
                        withBorder
                        style={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/jurisdicciones/${stat.jurisdiccion_id}`)}
                      >
                        <Group justify="space-between" mb="xs">
                          <Group gap="xs">
                            <ThemeIcon
                              size="md"
                              variant="light"
                              color={getColorByTipo(stat.tipo)}
                            >
                              {getIconByTipo(stat.tipo, 16)}
                            </ThemeIcon>
                            <Text fw={600} lineClamp={1}>
                              {stat.nombre}
                            </Text>
                          </Group>
                          <IconChevronRight size={16} />
                        </Group>

                        <Group grow mt="xs">
                          <Box>
                            <Text size="xs" c="dimmed">BOE</Text>
                            <Text fw={600}>{stat.total_boletines}</Text>
                          </Box>
                          {stat.total_menciones > 0 && (
                            <Box>
                              <Text size="xs" c="dimmed">Refs</Text>
                              <Text fw={600} c="green">{stat.total_menciones}</Text>
                            </Box>
                          )}
                        </Group>

                        {stat.poblacion && (
                          <Text size="xs" c="dimmed" mt="xs">
                            Población: {stat.poblacion.toLocaleString()}
                          </Text>
                        )}
                      </Card>
                    ))}
                  </SimpleGrid>
                )}
              </Tabs.Panel>
            </Tabs>
          </Paper>
        </div>
      </Stack>
    </Container>
  );
};

export default JurisdiccionesPage;
