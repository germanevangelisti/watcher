/**
 * JurisdiccionDetailPage - Vista Detallada de una Jurisdicción
 * 
 * Muestra:
 * - Información general
 * - Estadísticas de boletines
 * - Lista de boletines de la jurisdicción
 * - Menciones en otros boletines (futuro)
 */

import React, { useState, useEffect } from 'react';
import {
  Container,
  Title,
  Text,
  Group,
  Stack,
  Paper,
  Grid,
  Card,
  Badge,
  Loader,
  Button,
  Table,
  ActionIcon,
  Box,
  Divider,
  ThemeIcon,
  Breadcrumbs,
  Anchor
} from '@mantine/core';
import {
  IconMapPin,
  IconBuilding,
  IconHome,
  IconUsers,
  IconFileText,
  IconAlertCircle,
  IconDownload,
  IconEye,
  IconArrowLeft,
  IconCalendar,
  IconMapPinFilled
} from '@tabler/icons-react';
import { useParams, useNavigate } from 'react-router-dom';

interface JurisdiccionDetail {
  id: number;
  nombre: string;
  tipo: string;
  latitud?: number;
  longitud?: number;
  codigo_postal?: string;
  departamento?: string;
  poblacion?: number;
  superficie_km2?: number;
  total_boletines: number;
  total_menciones: number;
  ultima_actividad?: string;
}

interface Boletin {
  id: number;
  filename: string;
  date: string;
  section: number;
  seccion_nombre?: string;
  status: string;
  fuente: string;
}

const JurisdiccionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [jurisdiccion, setJurisdiccion] = useState<JurisdiccionDetail | null>(null);
  const [boletines, setBoletines] = useState<Boletin[]>([]);
  const [loading, setLoading] = useState(true);
  const [boletinesLoading, setBoletinesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paginaActual, setPaginaActual] = useState(1);
  const [totalBoletines, setTotalBoletines] = useState(0);
  const boletinesPorPagina = 20;

  useEffect(() => {
    if (id) {
      fetchJurisdiccion();
      fetchBoletines();
    }
  }, [id, paginaActual]);

  const fetchJurisdiccion = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/jurisdicciones/${id}`);
      if (!res.ok) throw new Error('Error cargando jurisdicción');
      const data = await res.json();
      setJurisdiccion(data);
      setError(null);
    } catch (err) {
      console.error('Error:', err);
      setError('Error cargando jurisdicción');
    } finally {
      setLoading(false);
    }
  };

  const fetchBoletines = async () => {
    try {
      setBoletinesLoading(true);
      const offset = (paginaActual - 1) * boletinesPorPagina;
      const res = await fetch(
        `/api/v1/jurisdicciones/${id}/boletines?limite=${boletinesPorPagina}&offset=${offset}`
      );
      if (!res.ok) throw new Error('Error cargando boletines');
      const data = await res.json();
      setBoletines(data.boletines || []);
      setTotalBoletines(data.total || 0);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setBoletinesLoading(false);
    }
  };

  const getIconByTipo = (tipo: string, size: number = 24) => {
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

  const getLabelByTipo = (tipo: string): string => {
    switch (tipo) {
      case 'provincia':
        return 'Provincia';
      case 'capital':
        return 'Ciudad Capital';
      case 'municipalidad':
        return 'Municipalidad';
      case 'comuna':
        return 'Comuna';
      default:
        return tipo;
    }
  };

  const handleVerBoletin = (boletinId: number) => {
    navigate(`/documents/${boletinId}`);
  };

  if (loading) {
    return (
      <Container size="xl" py="xl">
        <Group justify="center" py="xl">
          <Loader size="lg" />
          <Text>Cargando jurisdicción...</Text>
        </Group>
      </Container>
    );
  }

  if (error || !jurisdiccion) {
    return (
      <Container size="xl" py="xl">
        <Text c="red">{error || 'Jurisdicción no encontrada'}</Text>
        <Button mt="md" onClick={() => navigate('/jurisdicciones')}>
          Volver
        </Button>
      </Container>
    );
  }

  const totalPaginas = Math.ceil(totalBoletines / boletinesPorPagina);

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        {/* Breadcrumbs */}
        <Breadcrumbs>
          <Anchor onClick={() => navigate('/jurisdicciones')}>
            Jurisdicciones
          </Anchor>
          <Text>{jurisdiccion.nombre}</Text>
        </Breadcrumbs>

        {/* Header */}
        <Paper p="xl" withBorder>
          <Group justify="space-between" mb="lg">
            <Group>
              <ThemeIcon
                size="xl"
                variant="light"
                color={getColorByTipo(jurisdiccion.tipo)}
              >
                {getIconByTipo(jurisdiccion.tipo, 32)}
              </ThemeIcon>
              <div>
                <Title order={1}>{jurisdiccion.nombre}</Title>
                <Group gap="xs" mt="xs">
                  <Badge
                    size="lg"
                    variant="light"
                    color={getColorByTipo(jurisdiccion.tipo)}
                  >
                    {getLabelByTipo(jurisdiccion.tipo)}
                  </Badge>
                  {jurisdiccion.departamento && (
                    <Badge size="lg" variant="outline">
                      Depto. {jurisdiccion.departamento}
                    </Badge>
                  )}
                </Group>
              </div>
            </Group>
            
            <Button
              leftSection={<IconArrowLeft size={16} />}
              variant="light"
              onClick={() => navigate('/jurisdicciones')}
            >
              Volver
            </Button>
          </Group>

          <Divider my="lg" />

          {/* Información General */}
          <Grid gutter="lg">
            <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
              <Box>
                <Group gap="xs" mb="xs">
                  <IconFileText size={16} />
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                    Boletines
                  </Text>
                </Group>
                <Text size="xl" fw={700}>
                  {jurisdiccion.total_boletines.toLocaleString()}
                </Text>
              </Box>
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
              <Box>
                <Group gap="xs" mb="xs">
                  <IconAlertCircle size={16} />
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                    Menciones
                  </Text>
                </Group>
                <Text size="xl" fw={700} c="green">
                  {jurisdiccion.total_menciones.toLocaleString()}
                </Text>
              </Box>
            </Grid.Col>

            {jurisdiccion.poblacion && (
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Box>
                  <Group gap="xs" mb="xs">
                    <IconUsers size={16} />
                    <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                      Población
                    </Text>
                  </Group>
                  <Text size="xl" fw={700}>
                    {jurisdiccion.poblacion.toLocaleString()}
                  </Text>
                </Box>
              </Grid.Col>
            )}

            {jurisdiccion.superficie_km2 && (
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Box>
                  <Group gap="xs" mb="xs">
                    <IconMapPinFilled size={16} />
                    <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                      Superficie
                    </Text>
                  </Group>
                  <Text size="xl" fw={700}>
                    {jurisdiccion.superficie_km2.toLocaleString()} km²
                  </Text>
                </Box>
              </Grid.Col>
            )}

            {jurisdiccion.codigo_postal && (
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Box>
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700} mb="xs">
                    Código Postal
                  </Text>
                  <Text size="lg" fw={600}>
                    {jurisdiccion.codigo_postal}
                  </Text>
                </Box>
              </Grid.Col>
            )}

            {jurisdiccion.ultima_actividad && (
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Box>
                  <Group gap="xs" mb="xs">
                    <IconCalendar size={16} />
                    <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                      Última Actividad
                    </Text>
                  </Group>
                  <Text size="lg" fw={600}>
                    {new Date(jurisdiccion.ultima_actividad).toLocaleDateString()}
                  </Text>
                </Box>
              </Grid.Col>
            )}

            {jurisdiccion.latitud && jurisdiccion.longitud && (
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Box>
                  <Group gap="xs" mb="xs">
                    <IconMapPin size={16} />
                    <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                      Coordenadas
                    </Text>
                  </Group>
                  <Text size="sm" fw={500}>
                    {jurisdiccion.latitud.toFixed(4)}, {jurisdiccion.longitud.toFixed(4)}
                  </Text>
                </Box>
              </Grid.Col>
            )}
          </Grid>
        </Paper>

        {/* Lista de Boletines */}
        <div>
          <Group justify="space-between" mb="md">
            <Title order={2} size="h3">
              Boletines ({totalBoletines})
            </Title>
          </Group>

          <Paper withBorder>
            {boletinesLoading ? (
              <Group justify="center" p="xl">
                <Loader size="md" />
              </Group>
            ) : boletines.length === 0 ? (
              <Text c="dimmed" ta="center" p="xl">
                No hay boletines para esta jurisdicción
              </Text>
            ) : (
              <>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Fecha</Table.Th>
                      <Table.Th>Archivo</Table.Th>
                      <Table.Th>Sección</Table.Th>
                      <Table.Th>Fuente</Table.Th>
                      <Table.Th>Estado</Table.Th>
                      <Table.Th>Acciones</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {boletines.map((boletin) => (
                      <Table.Tr key={boletin.id}>
                        <Table.Td>
                          <Text size="sm">
                            {new Date(boletin.date).toLocaleDateString()}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" fw={500}>
                            {boletin.filename}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge size="sm" variant="outline">
                            {boletin.seccion_nombre || `Sección ${boletin.section}`}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            size="sm"
                            color={boletin.fuente === 'provincial' ? 'blue' : 'red'}
                          >
                            {boletin.fuente === 'provincial' ? 'Provincial' : 'Municipal'}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            size="sm"
                            color={
                              boletin.status === 'processed'
                                ? 'green'
                                : boletin.status === 'processing'
                                ? 'yellow'
                                : 'gray'
                            }
                          >
                            {boletin.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <ActionIcon
                              variant="light"
                              color="blue"
                              onClick={() => handleVerBoletin(boletin.id)}
                            >
                              <IconEye size={16} />
                            </ActionIcon>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>

                {/* Paginación */}
                {totalPaginas > 1 && (
                  <Group justify="center" p="md">
                    <Button
                      variant="light"
                      disabled={paginaActual === 1}
                      onClick={() => setPaginaActual(p => p - 1)}
                    >
                      Anterior
                    </Button>
                    <Text size="sm">
                      Página {paginaActual} de {totalPaginas}
                    </Text>
                    <Button
                      variant="light"
                      disabled={paginaActual === totalPaginas}
                      onClick={() => setPaginaActual(p => p + 1)}
                    >
                      Siguiente
                    </Button>
                  </Group>
                )}
              </>
            )}
          </Paper>
        </div>
      </Stack>
    </Container>
  );
};

export default JurisdiccionDetailPage;
