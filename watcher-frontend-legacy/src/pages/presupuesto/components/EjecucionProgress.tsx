import { Card, Stack, Group, Text, Progress, Badge, Alert, Divider, Tooltip } from '@mantine/core';
import { IconInfoCircle, IconAlertTriangle, IconHelpCircle, IconCalendar } from '@tabler/icons-react';
import { MontoDisplay } from '../../../components/shared/MontoDisplay';

interface EjecucionProgressProps {
  montoInicial: number;
  montoVigente: number;
  totalEjecutado: number;
  porcentajeEjecucion: number;
  periodo?: string;
  esAcumulado?: boolean;
}

export function EjecucionProgress({ 
  montoInicial, 
  montoVigente, 
  totalEjecutado, 
  porcentajeEjecucion,
  periodo = 'Marzo 2025',
  esAcumulado = true
}: EjecucionProgressProps) {
  const getProgressColor = (porcentaje: number) => {
    if (porcentaje < 20) return 'red';
    if (porcentaje < 50) return 'orange';
    if (porcentaje < 80) return 'yellow';
    return 'green';
  };

  const getProgressLabel = (porcentaje: number) => {
    if (porcentaje === 0) return 'Sin ejecución';
    if (porcentaje < 20) return 'Muy Bajo';
    if (porcentaje < 50) return 'Bajo';
    if (porcentaje < 80) return 'Medio';
    return 'Alto';
  };

  // Calcular valores absolutos (sin signos negativos confusos)
  const montoInicialAbs = Math.abs(montoInicial);
  const montoVigenteAbs = Math.abs(montoVigente);
  const totalEjecutadoAbs = Math.abs(totalEjecutado);
  const montoDisponible = montoVigenteAbs - totalEjecutadoAbs;

  // Detectar reducción de presupuesto
  const reduccionPresupuesto = montoVigenteAbs < montoInicialAbs;
  const porcentajeReduccion = reduccionPresupuesto 
    ? ((1 - montoVigenteAbs / montoInicialAbs) * 100).toFixed(1)
    : null;

  // Formatear monto para mostrar en el progreso
  const formatMonto = (monto: number) => {
    return new Intl.NumberFormat('es-AR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(monto);
  };

  return (
    <Card withBorder shadow="sm" padding="lg">
      <Stack gap="md">
        {/* Header con período */}
        <Group justify="space-between" align="center">
          <Text fw={600} size="lg">Estado de Ejecución</Text>
          <Badge 
            color="blue" 
            variant="light"
            leftSection={<IconCalendar size={14} />}
          >
            {periodo} {esAcumulado && '(Acumulado)'}
          </Badge>
        </Group>

        {/* Progreso mejorado */}
        <Card withBorder padding="md" bg="gray.0">
          <Stack gap="xs">
            <Group justify="space-between" align="center">
              <Text size="sm" c="dimmed">Progreso de Ejecución</Text>
              <Text size="xl" fw={700}>{porcentajeEjecucion.toFixed(1)}%</Text>
            </Group>
            <Progress 
              value={porcentajeEjecucion} 
              size="xl" 
              color={getProgressColor(porcentajeEjecucion)}
            />
            <Group justify="space-between" align="center">
              <Text size="xs" c="dimmed" ta="center" style={{ flex: 1 }}>
                {porcentajeEjecucion === 0 
                  ? "Sin ejecución registrada" 
                  : `${formatMonto(totalEjecutadoAbs)} de ${formatMonto(montoVigenteAbs)}`}
              </Text>
              <Badge 
                size="sm" 
                color={getProgressColor(porcentajeEjecucion)}
                variant="light"
              >
                {getProgressLabel(porcentajeEjecucion)}
              </Badge>
            </Group>
          </Stack>
        </Card>

        {/* Alertas informativas */}
        {porcentajeEjecucion === 0 && (
          <Alert 
            icon={<IconInfoCircle size={16} />} 
            color="blue" 
            variant="light"
            title="Sin ejecución registrada"
          >
            Este programa aún no registra ejecución presupuestaria. Esto puede ser normal 
            al inicio del período fiscal o si el programa aún no ha iniciado actividades.
          </Alert>
        )}

        {reduccionPresupuesto && porcentajeReduccion && parseFloat(porcentajeReduccion) > 10 && (
          <Alert 
            icon={<IconAlertTriangle size={16} />} 
            color="orange" 
            variant="light"
            title="Reducción de presupuesto"
          >
            El presupuesto vigente es {porcentajeReduccion}% menor que el inicial 
            ({formatMonto(montoInicialAbs - montoVigenteAbs)} menos). 
            Ver modificaciones presupuestarias para más detalles.
          </Alert>
        )}

        {/* Montos con tooltips */}
        <Stack gap="sm">
          <Group justify="space-between" align="center">
            <Tooltip 
              label="Monto aprobado originalmente en la Ley de Presupuesto. Puede modificarse durante el año mediante decretos o resoluciones."
              withArrow
            >
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="sm">Presupuesto Inicial</Text>
                <IconHelpCircle size={14} style={{ color: 'var(--mantine-color-gray-6)' }} />
              </Group>
            </Tooltip>
            <MontoDisplay monto={montoInicialAbs} size="sm" />
          </Group>

          <Group justify="space-between" align="center">
            <Tooltip 
              label="Presupuesto actual después de modificaciones presupuestarias durante el año."
              withArrow
            >
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="sm" fw={600}>Presupuesto Vigente</Text>
                <IconHelpCircle size={14} style={{ color: 'var(--mantine-color-gray-6)' }} />
              </Group>
            </Tooltip>
            <Group gap="xs">
              <MontoDisplay monto={montoVigenteAbs} size="sm" fw={600} />
              {reduccionPresupuesto && porcentajeReduccion && (
                <Badge size="xs" color="orange" variant="light">
                  -{porcentajeReduccion}%
                </Badge>
              )}
            </Group>
          </Group>

          <Divider />

          <Group justify="space-between" align="center">
            <Tooltip 
              label="Total ejecutado acumulado hasta el período indicado. Incluye todos los gastos registrados desde el inicio del año."
              withArrow
            >
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="sm">Ejecutado</Text>
                <IconHelpCircle size={14} style={{ color: 'var(--mantine-color-gray-6)' }} />
              </Group>
            </Tooltip>
            <MontoDisplay monto={totalEjecutadoAbs} size="sm" c="green" fw={700} />
          </Group>

          <Group justify="space-between" align="center">
            <Tooltip 
              label="Monto disponible para ejecutar. Calculado como Presupuesto Vigente menos Ejecutado."
              withArrow
            >
              <Group gap={4} style={{ cursor: 'help' }}>
                <Text size="sm">Disponible</Text>
                <IconHelpCircle size={14} style={{ color: 'var(--mantine-color-gray-6)' }} />
              </Group>
            </Tooltip>
            <MontoDisplay 
              monto={montoDisponible >= 0 ? montoDisponible : 0} 
              size="sm" 
              c="orange" 
              fw={600} 
            />
          </Group>
        </Stack>
      </Stack>
    </Card>
  );
}

