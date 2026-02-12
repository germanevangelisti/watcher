import { Container, Title, Text, Stack, Group, Card, Button, Loader, Alert, Divider } from '@mantine/core';
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { IconArrowLeft, IconAlertCircle, IconFileText, IconCalendar, IconUser } from '@tabler/icons-react';
import { useUserMode } from '../../contexts/UserModeContext';
import { RiskBadge } from '../../components/shared/RiskBadge';
import { MontoDisplay } from '../../components/shared/MontoDisplay';
import { VinculosTable } from './components/VinculosTable';
import { getActoById } from '../../services/api';
import type { ActoDetail } from '../../types/actos';

export function ActoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isCiudadano, isAuditor } = useUserMode();
  const [acto, setActo] = useState<ActoDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (id) {
      loadActo(parseInt(id));
    }
  }, [id]);

  const loadActo = async (actoId: number) => {
    try {
      setLoading(true);
      setError('');
      const data = await getActoById(actoId);
      setActo(data);
    } catch (err) {
      setError('Error cargando acto: ' + (err as Error).message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container size="md">
        <Group justify="center" py="xl">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  if (error || !acto) {
    return (
      <Container size="md">
        <Alert color="red" title="Error" icon={<IconAlertCircle size="1rem" />}>
          {error || 'Acto no encontrado'}
        </Alert>
        <Button 
          mt="md" 
          leftSection={<IconArrowLeft size="1rem" />}
          onClick={() => navigate('/actos')}
        >
          Volver a Actos
        </Button>
      </Container>
    );
  }

  return (
    <Container size="lg">
      <Stack gap="xl">
        <Button 
          variant="subtle" 
          leftSection={<IconArrowLeft size="1rem" />}
          onClick={() => navigate('/actos')}
        >
          Volver a Actos
        </Button>

        <Card withBorder shadow="md" padding="xl">
          <Stack gap="lg">
            <Group justify="space-between" align="flex-start">
              <div>
                <Group gap="xs" mb="xs">
                  <IconFileText size="1.5rem" />
                  <Title order={2}>
                    {acto.tipo_acto} {acto.numero && `N° ${acto.numero}`}
                  </Title>
                </Group>
                <Text c="dimmed" size="lg">{acto.organismo}</Text>
              </div>
              <RiskBadge risk={acto.nivel_riesgo} size="lg" />
            </Group>

            <Group gap="xl">
              {acto.fecha && (
                <Group gap="xs">
                  <IconCalendar size="1rem" />
                  <div>
                    <Text size="xs" c="dimmed">Fecha</Text>
                    <Text fw={500}>
                      {new Date(acto.fecha).toLocaleDateString('es-AR')}
                    </Text>
                  </div>
                </Group>
              )}

              {acto.beneficiario && (
                <Group gap="xs">
                  <IconUser size="1rem" />
                  <div>
                    <Text size="xs" c="dimmed">Beneficiario</Text>
                    <Text fw={500}>{acto.beneficiario}</Text>
                  </div>
                </Group>
              )}
            </Group>

            <Divider />

            <div>
              <Text fw={600} mb="xs">Descripción:</Text>
              <Text>{acto.descripcion}</Text>
            </div>

            {acto.monto && (
              <div>
                <Text fw={600} mb="xs">Monto:</Text>
                <MontoDisplay monto={acto.monto} size="xl" />
              </div>
            )}

            {acto.partida && (
              <div>
                <Text fw={600} mb="xs">Partida Presupuestaria:</Text>
                <Text>{acto.partida}</Text>
              </div>
            )}

            {isAuditor && acto.keywords && (
              <div>
                <Text fw={600} mb="xs">Keywords:</Text>
                <Text size="sm" c="dimmed">{acto.keywords}</Text>
              </div>
            )}

            {isAuditor && acto.fragmento_original && (
              <div>
                <Text fw={600} mb="xs">Fragmento Original:</Text>
                <Card withBorder bg="gray.0" p="md">
                  <Text size="sm" style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                    {acto.fragmento_original}
                  </Text>
                </Card>
                {acto.pagina && (
                  <Text size="xs" c="dimmed" mt="xs">
                    Página: {acto.pagina}
                  </Text>
                )}
              </div>
            )}
          </Stack>
        </Card>

        {/* Vínculos Presupuestarios */}
        <VinculosTable vinculos={acto.vinculos} />
      </Stack>
    </Container>
  );
}

