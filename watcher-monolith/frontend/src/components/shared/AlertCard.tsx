import { Card, Text, Group, Stack, Badge, Button, Collapse } from '@mantine/core';
import { IconAlertTriangle, IconEye, IconChevronDown, IconChevronUp } from '@tabler/icons-react';
import { useState } from 'react';
import { useUserMode } from '../../contexts/UserModeContext';

interface AlertCardProps {
  titulo: string;
  descripcion: string;
  severidad: 'CRITICA' | 'ALTA' | 'MEDIA' | 'BAJA';
  tipo: string;
  organismo: string;
  fecha: string;
  accionesSugeridas?: string[];
  valorDetectado?: number;
  valorEsperado?: number;
  onViewDetails?: () => void;
}

export function AlertCard({
  titulo,
  descripcion,
  severidad,
  tipo,
  organismo,
  fecha,
  accionesSugeridas = [],
  valorDetectado,
  valorEsperado,
  onViewDetails,
}: AlertCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { isCiudadano } = useUserMode();

  const severidadConfig = {
    CRITICA: { color: 'red', label: isCiudadano ? 'Urgente' : 'Crítica' },
    ALTA: { color: 'orange', label: isCiudadano ? 'Importante' : 'Alta' },
    MEDIA: { color: 'yellow', label: isCiudadano ? 'A Revisar' : 'Media' },
    BAJA: { color: 'blue', label: isCiudadano ? 'Información' : 'Baja' },
  };

  const { color, label } = severidadConfig[severidad] || severidadConfig.BAJA;

  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="sm">
        <Group justify="space-between">
          <Group gap="xs">
            <IconAlertTriangle size="1.2rem" color={color === 'red' ? 'var(--mantine-color-red-6)' : undefined} />
            <Text fw={600} size="lg">
              {titulo}
            </Text>
          </Group>
          <Badge color={color} size="lg">
            {label}
          </Badge>
        </Group>

        <Text size="sm" c="dimmed">{organismo}</Text>
        
        <Text size="xs" c="dimmed">
          {new Date(fecha).toLocaleDateString('es-AR', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          })}
        </Text>

        <Text size="sm">
          {descripcion}
        </Text>

        {!isCiudadano && (valorDetectado !== undefined || valorEsperado !== undefined) && (
          <Group gap="md">
            {valorDetectado !== undefined && (
              <Text size="xs">
                <Text span fw={600}>Detectado:</Text> {valorDetectado}
              </Text>
            )}
            {valorEsperado !== undefined && (
              <Text size="xs">
                <Text span fw={600}>Esperado:</Text> {valorEsperado}
              </Text>
            )}
          </Group>
        )}

        {accionesSugeridas.length > 0 && (
          <>
            <Button
              variant="subtle"
              size="xs"
              onClick={() => setExpanded(!expanded)}
              rightSection={expanded ? <IconChevronUp size="1rem" /> : <IconChevronDown size="1rem" />}
            >
              {isCiudadano ? 'Qué puedo hacer' : 'Acciones sugeridas'}
            </Button>

            <Collapse in={expanded}>
              <Stack gap="xs" mt="xs">
                {accionesSugeridas.map((accion, idx) => (
                  <Text key={idx} size="sm">
                    • {accion}
                  </Text>
                ))}
              </Stack>
            </Collapse>
          </>
        )}

        {onViewDetails && (
          <Button 
            variant="light" 
            leftSection={<IconEye size="1rem" />}
            onClick={onViewDetails}
            fullWidth
            mt="xs"
          >
            Ver Detalle Completo
          </Button>
        )}
      </Stack>
    </Card>
  );
}

