import { Container, Title, Text, Stack, Group, Card, Button, Loader, Alert, Table, Divider, Badge } from '@mantine/core';
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { IconArrowLeft, IconAlertCircle, IconBuilding, IconFileText, IconFolder } from '@tabler/icons-react';
import { useUserMode } from '../../contexts/UserModeContext';
import { MontoDisplay } from '../../components/shared/MontoDisplay';
import { EjecucionProgress } from './components/EjecucionProgress';
import { RiskBadge } from '../../components/shared/RiskBadge';
import { getProgramaById } from '../../services/api';
import type { ProgramaDetail } from '../../types/presupuesto';

export function ProgramaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isCiudadano } = useUserMode();
  const [programa, setPrograma] = useState<ProgramaDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (id) {
      loadPrograma(parseInt(id));
    }
  }, [id]);

  const loadPrograma = async (programaId: number) => {
    try {
      setLoading(true);
      setError('');
      const data = await getProgramaById(programaId);
      setPrograma(data);
    } catch (err) {
      setError('Error cargando programa: ' + (err as Error).message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container size="lg">
        <Group justify="center" py="xl">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  if (error || !programa) {
    return (
      <Container size="lg">
        <Alert color="red" title="Error" icon={<IconAlertCircle size="1rem" />}>
          {error || 'Programa no encontrado'}
        </Alert>
        <Button 
          mt="md" 
          leftSection={<IconArrowLeft size="1rem" />}
          onClick={() => navigate('/presupuesto')}
        >
          Volver a Programas
        </Button>
      </Container>
    );
  }

  return (
    <Container size="xl">
      <Stack gap="xl">
        <Button 
          variant="subtle" 
          leftSection={<IconArrowLeft size="1rem" />}
          onClick={() => navigate('/presupuesto')}
        >
          Volver a Programas
        </Button>

        <Group align="flex-start" gap="lg">
          {/* Main Info */}
          <div style={{ flex: 2 }}>
            <Card withBorder shadow="md" padding="xl">
              <Stack gap="lg">
                {/* Header con año */}
                <Group justify="space-between" align="flex-start">
                  <div style={{ flex: 1 }}>
                    {/* Jerarquía visual mejorada */}
                    <Group gap="xs" mb="md" align="center">
                      <IconBuilding size={20} style={{ color: 'var(--mantine-color-blue-6)' }} />
                      <div>
                        <Text size="xs" c="dimmed" fw={500} tt="uppercase" mb={2}>
                          Organismo
                        </Text>
                        <Text size="lg" fw={600}>{programa.organismo}</Text>
                      </div>
                    </Group>

                    <Group gap="xs" mb="md" align="center" ml="xl">
                      <IconFileText size={18} style={{ color: 'var(--mantine-color-indigo-6)' }} />
                      <div>
                        <Text size="xs" c="dimmed" fw={500} tt="uppercase" mb={2}>
                          Programa
                        </Text>
                        <Title order={2} size="h3">{programa.programa}</Title>
                      </div>
                    </Group>

                    <Group gap="xs" mb="md" align="center" ml="xl">
                      <IconFolder size={16} style={{ color: 'var(--mantine-color-teal-6)' }} />
                      <div>
                        <Text size="xs" c="dimmed" fw={500} tt="uppercase" mb={2}>
                          Partida Presupuestaria
                        </Text>
                        <Text size="md" fw={600}>{programa.partida_presupuestaria}</Text>
                      </div>
                    </Group>

                    {programa.subprograma && (
                      <Group gap="xs" mb="md" align="center" ml="xl">
                        <IconFolder size={14} style={{ color: 'var(--mantine-color-gray-6)' }} />
                        <div>
                          <Text size="xs" c="dimmed" fw={500} tt="uppercase" mb={2}>
                            Subprograma
                          </Text>
                          <Text size="sm" fw={500}>{programa.subprograma}</Text>
                        </div>
                      </Group>
                    )}
                  </div>
                  <Badge size="xl" variant="light" color="blue">
                    {programa.ejercicio}
                  </Badge>
                </Group>

                {programa.descripcion && (
                  <>
                    <Divider />
                    <div>
                      <Text size="sm" fw={600} mb="xs">Descripción</Text>
                      <Text size="sm" c="dimmed">{programa.descripcion || 'Sin descripción disponible'}</Text>
                    </div>
                  </>
                )}

                {programa.meta_fisica && (
                  <>
                    <Divider />
                    <div>
                      <Text size="sm" fw={600} mb="xs">Meta Física</Text>
                      <Text size="sm">{programa.meta_fisica}</Text>
                      {programa.meta_numerica && programa.unidad_medida && (
                        <Text size="sm" c="dimmed" mt={4}>
                          {programa.meta_numerica} {programa.unidad_medida}
                        </Text>
                      )}
                    </div>
                  </>
                )}

                {programa.fuente_financiamiento && (
                  <>
                    <Divider />
                    <div>
                      <Text size="sm" fw={600} mb="xs">Fuente de Financiamiento</Text>
                      <Badge 
                        color="blue" 
                        variant="light"
                        size="md"
                      >
                        {programa.fuente_financiamiento.includes('Administración Central')
                          ? 'Administración Central'
                          : programa.fuente_financiamiento.includes('EMAEE')
                          ? 'EMAEE'
                          : programa.fuente_financiamiento.includes('.xlsx')
                          ? programa.fuente_financiamiento.split('.xlsx')[0].replace('Gastos ', '').replace('Recursos ', '')
                          : programa.fuente_financiamiento}
                      </Badge>
                      <Text size="xs" c="dimmed" mt={4}>
                        Datos extraídos de ejecución presupuestaria oficial
                      </Text>
                    </div>
                  </>
                )}

                <Divider />
                <Text size="xs" c="dimmed">
                  Fecha de Aprobación: {new Date(programa.fecha_aprobacion).toLocaleDateString('es-AR', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </Text>
              </Stack>
            </Card>

            {/* Ejecuciones Table */}
            {programa.ejecuciones.length > 0 && (
              <Card withBorder shadow="sm" padding="lg" mt="lg">
                <Stack gap="md">
                  <Title order={4}>
                    {isCiudadano ? 'Historial de Gastos' : 'Ejecuciones Registradas'}
                  </Title>
                  <Text size="sm" c="dimmed">
                    {programa.ejecuciones.length} operaciones registradas
                  </Text>

                  <Table>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Fecha</Table.Th>
                        <Table.Th>Beneficiario</Table.Th>
                        <Table.Th>Concepto</Table.Th>
                        <Table.Th>Monto</Table.Th>
                        <Table.Th>Riesgo</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {programa.ejecuciones.map((ejecucion) => (
                        <Table.Tr key={ejecucion.id}>
                          <Table.Td>
                            <Text size="sm">
                              {new Date(ejecucion.fecha_boletin).toLocaleDateString('es-AR')}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" fw={500}>{ejecucion.beneficiario}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" lineClamp={2}>{ejecucion.concepto}</Text>
                            <Text size="xs" c="dimmed">{ejecucion.tipo_operacion}</Text>
                          </Table.Td>
                          <Table.Td>
                            <MontoDisplay monto={ejecucion.monto} size="sm" />
                          </Table.Td>
                          <Table.Td>
                            <RiskBadge 
                              risk={ejecucion.riesgo_watcher as any} 
                              size="sm" 
                            />
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Stack>
              </Card>
            )}
          </div>

          {/* Sidebar with Progress */}
          <div style={{ width: '380px', flexShrink: 0 }}>
            <EjecucionProgress
              montoInicial={programa.monto_inicial}
              montoVigente={programa.monto_vigente}
              totalEjecutado={programa.total_ejecutado}
              porcentajeEjecucion={programa.porcentaje_ejecucion}
              periodo="Marzo 2025"
              esAcumulado={true}
            />
          </div>
        </Group>
      </Stack>
    </Container>
  );
}

