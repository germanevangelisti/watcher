import { Card, Text, Group, Stack, Badge, Button } from '@mantine/core';
import { IconFileText, IconEye } from '@tabler/icons-react';
import { RiskBadge } from './RiskBadge';
import { MontoDisplay } from './MontoDisplay';

interface ActoCardProps {
  tipo: string;
  numero?: string;
  organismo: string;
  monto?: number;
  riesgo: 'ALTO' | 'MEDIO' | 'BAJO';
  descripcion: string;
  fecha?: string;
  onViewDetails?: () => void;
}

export function ActoCard({
  tipo,
  numero,
  organismo,
  monto,
  riesgo,
  descripcion,
  fecha,
  onViewDetails,
}: ActoCardProps) {
  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="sm">
        <Group justify="space-between">
          <Group gap="xs">
            <IconFileText size="1.2rem" />
            <Text fw={600} size="lg">
              {tipo} {numero && `N° ${numero}`}
            </Text>
          </Group>
          <RiskBadge risk={riesgo} />
        </Group>

        <Text size="sm" c="dimmed">{organismo}</Text>

        {fecha && (
          <Text size="xs" c="dimmed">
            Fecha: {new Date(fecha).toLocaleDateString('es-AR')}
          </Text>
        )}

        <Text size="sm" lineClamp={3}>
          {descripcion}
        </Text>

        {monto && (
          <MontoDisplay monto={monto} size="lg" />
        )}

        {onViewDetails && (
          <Button 
            variant="light" 
            leftSection={<IconEye size="1rem" />}
            onClick={onViewDetails}
            fullWidth
          >
            Ver Detalle
          </Button>
        )}
      </Stack>
    </Card>
  );
}

