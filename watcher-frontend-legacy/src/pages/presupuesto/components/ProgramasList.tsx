import { Card, Text, Group, Stack, Badge, Button, Divider, Tooltip } from '@mantine/core';
import { IconEye, IconBuilding, IconFileText, IconFolder, IconHelpCircle } from '@tabler/icons-react';
import { MontoDisplay } from '../../../components/shared/MontoDisplay';
import type { Programa } from '../../../types/presupuesto';

interface ProgramasListProps {
  programas: Programa[];
  onViewDetails: (id: number) => void;
}

export function ProgramasList({ programas, onViewDetails }: ProgramasListProps) {
  if (programas.length === 0) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        No se encontraron programas con los filtros seleccionados
      </Text>
    );
  }

  // Extraer código del programa (ej: "001 - Fiscalía De Estado" -> "001")
  const getProgramaCode = (programaStr: string): string => {
    const match = programaStr.match(/^(\d{3})/);
    return match ? match[1] : '';
  };

  // Extraer nombre del programa sin código
  const getProgramaName = (programaStr: string): string => {
    return programaStr.replace(/^\d{3}\s*-\s*/, '');
  };

  return (
    <Stack gap="md">
      {programas.map((programa) => {
        const montoVigenteAbs = Math.abs(programa.monto_vigente);
        const montoInicialAbs = Math.abs(programa.monto_inicial);
        const reduccionPresupuesto = montoVigenteAbs < montoInicialAbs;
        const porcentajeReduccion = reduccionPresupuesto 
          ? ((1 - montoVigenteAbs / montoInicialAbs) * 100).toFixed(1)
          : null;
        const programaCode = getProgramaCode(programa.programa);
        const programaName = getProgramaName(programa.programa);

        return (
          <Card key={programa.id} withBorder shadow="sm" padding="lg" style={{ transition: 'all 0.2s' }}>
            <Stack gap="md">
              {/* Header con jerarquía visual */}
              <Group justify="space-between" align="flex-start">
                <div style={{ flex: 1 }}>
                  {/* Organismo */}
                  <Group gap="xs" mb="xs" align="center">
                    <IconBuilding size={16} style={{ color: 'var(--mantine-color-blue-6)' }} />
                    <Text size="sm" c="dimmed" fw={500}>
                      {programa.organismo}
                    </Text>
                  </Group>

                  {/* Programa con código */}
                  <Group gap="xs" mb="xs" align="center" ml="md">
                    <IconFileText size={16} style={{ color: 'var(--mantine-color-indigo-6)' }} />
                    <div>
                      {programaCode && (
                        <Badge size="sm" variant="light" color="indigo" mr="xs">
                          {programaCode}
                        </Badge>
                      )}
                      <Text fw={600} size="md" component="span">
                        {programaName}
                      </Text>
                    </div>
                  </Group>

                  {/* Partida */}
                  {programa.partida_presupuestaria && (
                    <Group gap="xs" align="center" ml="md">
                      <IconFolder size={14} style={{ color: 'var(--mantine-color-teal-6)' }} />
                      <Text size="xs" c="dimmed">
                        <Text span fw={500}>Partida:</Text> {programa.partida_presupuestaria}
                      </Text>
                    </Group>
                  )}

                  {/* Descripción si existe */}
                  {programa.descripcion && (
                    <Text size="xs" c="dimmed" lineClamp={1} mt="xs" ml="md">
                      {programa.descripcion}
                    </Text>
                  )}
                </div>
                <Badge size="lg" variant="light" color="blue">
                  {programa.ejercicio}
                </Badge>
              </Group>

              <Divider />

              {/* Montos presupuestarios */}
              <Group gap="xl" grow>
                <div>
                  <Tooltip 
                    label="Presupuesto actual después de modificaciones presupuestarias durante el año"
                    withArrow
                  >
                    <Group gap={4} style={{ cursor: 'help' }}>
                      <Text size="xs" c="dimmed">Presupuesto Vigente</Text>
                      <IconHelpCircle size={12} style={{ color: 'var(--mantine-color-gray-6)' }} />
                    </Group>
                  </Tooltip>
                  <Group gap="xs" align="center">
                    <MontoDisplay monto={montoVigenteAbs} fw={700} size="md" />
                    {reduccionPresupuesto && porcentajeReduccion && (
                      <Badge size="xs" color="orange" variant="light">
                        -{porcentajeReduccion}%
                      </Badge>
                    )}
                  </Group>
                </div>
                <div>
                  <Tooltip 
                    label="Monto aprobado originalmente en la Ley de Presupuesto"
                    withArrow
                  >
                    <Group gap={4} style={{ cursor: 'help' }}>
                      <Text size="xs" c="dimmed">Presupuesto Inicial</Text>
                      <IconHelpCircle size={12} style={{ color: 'var(--mantine-color-gray-6)' }} />
                    </Group>
                  </Tooltip>
                  <MontoDisplay monto={montoInicialAbs} size="sm" />
                </div>
              </Group>

              <Button 
                variant="light" 
                leftSection={<IconEye size="1rem" />}
                onClick={() => onViewDetails(programa.id)}
                fullWidth
                mt="xs"
              >
                Ver Detalle y Ejecución
              </Button>
            </Stack>
          </Card>
        );
      })}
    </Stack>
  );
}

