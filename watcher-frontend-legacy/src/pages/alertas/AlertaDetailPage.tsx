import { Container, Title, Text, Stack, Group, Card, Badge, Button, Loader, Alert } from '@mantine/core';
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { IconArrowLeft, IconAlertCircle, IconEdit } from '@tabler/icons-react';
import { useUserMode } from '../../contexts/UserModeContext';
import { getAlertaById, updateAlertaEstado } from '../../services/api';
import type { Alerta } from '../../types/alertas';

export function AlertaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isCiudadano } = useUserMode();
  const [alerta, setAlerta] = useState<Alerta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (id) {
      loadAlerta(parseInt(id));
    }
  }, [id]);

  const loadAlerta = async (alertaId: number) => {
    try {
      setLoading(true);
      setError('');
      const data = await getAlertaById(alertaId);
      setAlerta(data);
    } catch (err) {
      setError('Error cargando alerta: ' + (err as Error).message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateEstado = async (nuevoEstado: string) => {
    if (!alerta) return;
    
    try {
      const updated = await updateAlertaEstado(alerta.id, { estado: nuevoEstado });
      setAlerta(updated);
    } catch (err) {
      setError('Error actualizando estado: ' + (err as Error).message);
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

  if (error || !alerta) {
    return (
      <Container size="md">
        <Alert color="red" title="Error" icon={<IconAlertCircle size="1rem" />}>
          {error || 'Alerta no encontrada'}
        </Alert>
        <Button 
          mt="md" 
          leftSection={<IconArrowLeft size="1rem" />}
          onClick={() => navigate('/alertas')}
        >
          Volver a Alertas
        </Button>
      </Container>
    );
  }

  const severidadConfig = {
    CRITICA: { color: 'red', label: isCiudadano ? 'Urgente' : 'Crítica' },
    ALTA: { color: 'orange', label: isCiudadano ? 'Importante' : 'Alta' },
    MEDIA: { color: 'yellow', label: isCiudadano ? 'A Revisar' : 'Media' },
    BAJA: { color: 'blue', label: isCiudadano ? 'Información' : 'Baja' },
  };

  const { color, label } = severidadConfig[alerta.nivel_severidad] || severidadConfig.BAJA;

  return (
    <Container size="md">
      <Stack gap="xl">
        <Button 
          variant="subtle" 
          leftSection={<IconArrowLeft size="1rem" />}
          onClick={() => navigate('/alertas')}
        >
          Volver a Alertas
        </Button>

        <Card withBorder shadow="md" padding="xl">
          <Stack gap="lg">
            <Group justify="space-between" align="flex-start">
              <div>
                <Title order={2} mb="xs">{alerta.titulo}</Title>
                <Text c="dimmed">{alerta.tipo_alerta}</Text>
              </div>
              <Badge color={color} size="xl">
                {label}
              </Badge>
            </Group>

            <div>
              <Text fw={600} mb="xs">Organismo:</Text>
              <Text>{alerta.organismo}</Text>
            </div>

            {alerta.programa && (
              <div>
                <Text fw={600} mb="xs">Programa:</Text>
                <Text>{alerta.programa}</Text>
              </div>
            )}

            <div>
              <Text fw={600} mb="xs">Descripción:</Text>
              <Text>{alerta.descripcion}</Text>
            </div>

            {(alerta.valor_detectado !== undefined || alerta.valor_esperado !== undefined) && (
              <Group gap="xl">
                {alerta.valor_detectado !== undefined && (
                  <div>
                    <Text fw={600} size="sm" c="dimmed">Valor Detectado</Text>
                    <Text size="xl" fw={700}>{alerta.valor_detectado}</Text>
                  </div>
                )}
                {alerta.valor_esperado !== undefined && (
                  <div>
                    <Text fw={600} size="sm" c="dimmed">Valor Esperado</Text>
                    <Text size="xl" fw={700}>{alerta.valor_esperado}</Text>
                  </div>
                )}
                {alerta.porcentaje_desvio !== undefined && (
                  <div>
                    <Text fw={600} size="sm" c="dimmed">Desvío</Text>
                    <Text size="xl" fw={700} c="red">{alerta.porcentaje_desvio}%</Text>
                  </div>
                )}
              </Group>
            )}

            {alerta.acciones_sugeridas && Object.keys(alerta.acciones_sugeridas).length > 0 && (
              <div>
                <Text fw={600} mb="xs">
                  {isCiudadano ? 'Qué puedes hacer:' : 'Acciones Sugeridas:'}
                </Text>
                <Stack gap="xs">
                  {Object.values(alerta.acciones_sugeridas).map((accion, idx) => (
                    <Text key={idx}>• {String(accion)}</Text>
                  ))}
                </Stack>
              </div>
            )}

            <div>
              <Text fw={600} mb="xs">Estado:</Text>
              <Badge color={alerta.estado === 'activa' ? 'green' : 'gray'} size="lg">
                {alerta.estado}
              </Badge>
            </div>

            <Text size="xs" c="dimmed">
              Detectada el: {new Date(alerta.fecha_deteccion).toLocaleDateString('es-AR', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })}
            </Text>

            {!isCiudadano && alerta.estado === 'activa' && (
              <Group>
                <Button
                  leftSection={<IconEdit size="1rem" />}
                  onClick={() => handleUpdateEstado('revisada')}
                  variant="light"
                >
                  Marcar como Revisada
                </Button>
                <Button
                  onClick={() => handleUpdateEstado('resuelta')}
                  color="green"
                  variant="light"
                >
                  Marcar como Resuelta
                </Button>
              </Group>
            )}
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}

