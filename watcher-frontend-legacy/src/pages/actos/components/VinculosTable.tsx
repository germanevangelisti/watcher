import { Table, Badge, Text, Card, Stack, Group, Progress } from '@mantine/core';
import { IconLink } from '@tabler/icons-react';
import { MontoDisplay } from '../../../components/shared/MontoDisplay';
import type { Vinculo } from '../../../types/actos';
import { useUserMode } from '../../../contexts/UserModeContext';

interface VinculosTableProps {
  vinculos: Vinculo[];
}

export function VinculosTable({ vinculos }: VinculosTableProps) {
  const { isCiudadano } = useUserMode();

  if (vinculos.length === 0) {
    return (
      <Card withBorder>
        <Text c="dimmed" ta="center" py="lg">
          No se encontraron vínculos presupuestarios para este acto
        </Text>
      </Card>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'green';
    if (score >= 0.6) return 'yellow';
    return 'orange';
  };

  const getScoreLabel = (score: number) => {
    if (isCiudadano) {
      if (score >= 0.8) return 'Alta confianza';
      if (score >= 0.6) return 'Confianza media';
      return 'Confianza baja';
    }
    return `Score: ${(score * 100).toFixed(0)}%`;
  };

  return (
    <Card withBorder shadow="sm">
      <Stack gap="md">
        <Group gap="xs">
          <IconLink size="1.2rem" />
          <Text fw={600} size="lg">
            {isCiudadano ? 'Vinculación con Presupuesto' : 'Vínculos Presupuestarios Detectados'}
          </Text>
        </Group>

        <Text size="sm" c="dimmed">
          {isCiudadano 
            ? `Se encontraron ${vinculos.length} programas relacionados con este acto` 
            : `${vinculos.length} vínculos detectados con programas presupuestarios`}
        </Text>

        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Organismo</Table.Th>
              <Table.Th>Programa</Table.Th>
              <Table.Th>Presupuesto</Table.Th>
              <Table.Th>Método</Table.Th>
              <Table.Th>Confianza</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {vinculos.map((vinculo) => (
              <Table.Tr key={vinculo.id}>
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {vinculo.programa?.organismo || 'N/A'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">
                    {vinculo.programa?.programa || 'N/A'}
                  </Text>
                  {vinculo.programa?.descripcion && !isCiudadano && (
                    <Text size="xs" c="dimmed" lineClamp={1}>
                      {vinculo.programa.descripcion}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  {vinculo.programa?.monto_vigente && (
                    <MontoDisplay monto={vinculo.programa.monto_vigente} size="sm" />
                  )}
                </Table.Td>
                <Table.Td>
                  {!isCiudadano && (
                    <Badge size="sm" variant="light">
                      {vinculo.metodo_matching}
                    </Badge>
                  )}
                </Table.Td>
                <Table.Td>
                  <Stack gap="xs">
                    <Badge color={getScoreColor(vinculo.score_confianza)} size="sm">
                      {getScoreLabel(vinculo.score_confianza)}
                    </Badge>
                    {!isCiudadano && (
                      <Progress 
                        value={vinculo.score_confianza * 100} 
                        color={getScoreColor(vinculo.score_confianza)}
                        size="xs"
                      />
                    )}
                  </Stack>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Stack>
    </Card>
  );
}

