import { useEffect, useState } from 'react';
import {
  Container,
  Title,
  Text,
  Paper,
  Table,
  Badge,
  Group,
  Stack,
  Loader,
  Center,
  Alert,
  Select,
  TextInput,
  Button,
  Pagination,
} from '@mantine/core';
import { IconMapPin, IconAlertTriangle, IconSearch, IconFilter } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

export function MencionesPage() {
  const [loading, setLoading] = useState(true);
  const [menciones, setMenciones] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [tipoFilter, setTipoFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const limit = 20;

  useEffect(() => {
    loadMenciones();
  }, [page, tipoFilter]);

  const loadMenciones = async () => {
    try {
      setLoading(true);
      // TODO: Implementar API call cuando el endpoint esté listo
      // const params = {
      //   offset: (page - 1) * limit,
      //   limit,
      //   tipo_mencion: tipoFilter,
      // };
      // const data = await getMenciones(params);
      // setMenciones(data.menciones);
      // setTotal(data.total);
      
      // Placeholder para mostrar que la página existe
      setMenciones([]);
      setTotal(0);
    } catch (err: any) {
      console.error('Error loading menciones:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    loadMenciones();
  };

  if (loading && menciones.length === 0) {
    return (
      <Center style={{ height: '80vh' }}>
        <Stack align="center">
          <Loader size="xl" />
          <Text size="lg">Cargando menciones jurisdiccionales...</Text>
        </Stack>
      </Center>
    );
  }

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <div>
          <Title order={1}>Menciones Jurisdiccionales</Title>
          <Text c="dimmed" size="sm" mt="xs">
            Seguimiento de menciones de jurisdicciones (municipalidades, comunas) en boletines oficiales
            provinciales
          </Text>
        </div>

        <Alert icon={<IconAlertTriangle size="1rem" />} variant="light" color="blue">
          Esta funcionalidad permite rastrear cuándo y cómo se mencionan las diferentes jurisdicciones de Córdoba
          en el Boletín Oficial Provincial. Por ejemplo: decretos que afectan a una municipalidad, resoluciones sobre
          comunas, licitaciones regionales, etc.
        </Alert>

        {/* Filters */}
        <Paper p="md" withBorder>
          <Group>
            <Select
              placeholder="Filtrar por tipo"
              leftSection={<IconFilter size="1rem" />}
              data={[
                { value: 'decreto', label: 'Decreto' },
                { value: 'resolucion', label: 'Resolución' },
                { value: 'licitacion', label: 'Licitación' },
                { value: 'ordenanza', label: 'Ordenanza' },
                { value: 'convenio', label: 'Convenio' },
                { value: 'subsidio', label: 'Subsidio' },
                { value: 'transferencia', label: 'Transferencia' },
                { value: 'otro', label: 'Otro' },
              ]}
              value={tipoFilter}
              onChange={setTipoFilter}
              clearable
              style={{ width: 200 }}
            />

            <TextInput
              placeholder="Buscar jurisdicción..."
              leftSection={<IconSearch size="1rem" />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ flex: 1 }}
            />

            <Button onClick={handleSearch}>Buscar</Button>
          </Group>
        </Paper>

        {/* Content */}
        {menciones.length === 0 ? (
          <Paper p="xl" withBorder>
            <Stack align="center" gap="md">
              <IconMapPin size={48} color="gray" />
              <Title order={3}>Sistema en Implementación</Title>
              <Text c="dimmed" ta="center" maw={600}>
                El backend de menciones jurisdiccionales está implementado y funcional (5 endpoints API listos), pero
                la interfaz de usuario completa está pendiente. Mientras tanto, puedes ver menciones relacionadas en
                las páginas de detalle de cada jurisdicción y boletín.
              </Text>
              <Group>
                <Button onClick={() => navigate('/jurisdicciones')} variant="light">
                  Ver Jurisdicciones
                </Button>
                <Button onClick={() => navigate('/documentos')} variant="light">
                  Ver Documentos
                </Button>
              </Group>
            </Stack>
          </Paper>
        ) : (
          <>
            {/* Table */}
            <Paper withBorder>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th>Boletín</Table.Th>
                    <Table.Th>Jurisdicción</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Extracto</Table.Th>
                    <Table.Th>Confianza</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {menciones.map((mencion) => (
                    <Table.Tr key={mencion.id}>
                      <Table.Td>{mencion.fecha}</Table.Td>
                      <Table.Td>{mencion.boletin}</Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <IconMapPin size="1rem" />
                          {mencion.jurisdiccion}
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Badge>{mencion.tipo_mencion}</Badge>
                      </Table.Td>
                      <Table.Td style={{ maxWidth: 300 }}>
                        <Text size="sm" lineClamp={2}>
                          {mencion.extracto}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge color={mencion.confianza > 0.8 ? 'green' : 'yellow'}>
                          {(mencion.confianza * 100).toFixed(0)}%
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>

            {/* Pagination */}
            {total > limit && (
              <Group justify="center">
                <Pagination
                  value={page}
                  onChange={setPage}
                  total={Math.ceil(total / limit)}
                />
              </Group>
            )}
          </>
        )}
      </Stack>
    </Container>
  );
}
