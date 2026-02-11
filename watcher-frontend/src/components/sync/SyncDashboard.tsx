import React, { useState, useEffect } from 'react';
import {
  Card,
  Group,
  Text,
  Button,
  Stack,
  Progress,
  Alert,
  Badge,
  Divider,
  Switch,
  Select,
  NumberInput,
  Timeline,
  ActionIcon,
  Tooltip,
  Grid,
  Paper,
  RingProgress,
  Center
} from '@mantine/core';
import {
  IconRefresh,
  IconPlayerPlay,
  IconPlayerStop,
  IconClock,
  IconCheck,
  IconAlertCircle,
  IconCalendar,
  IconDownload,
  IconFileText,
  IconSettings,
  IconX,
  IconTrendingUp
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import axios from 'axios';

const API_BASE = 'http://localhost:8001/api/v1/sync';

interface SyncStatus {
  status: string;
  last_synced_date: string | null;
  last_detected_date: string | null;
  last_sync_timestamp: string | null;
  next_scheduled_sync: string | null;
  boletines_pending: number;
  boletines_downloaded: number;
  boletines_processed: number;
  boletines_failed: number;
  auto_sync_enabled: boolean;
  sync_frequency: string;
  sync_hour: number;
  current_operation: string | null;
  error_message: string | null;
  is_syncing: boolean;
}

const SyncDashboard: React.FC = () => {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Configuración del scheduler
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [scheduleFrequency, setScheduleFrequency] = useState('daily');
  const [scheduleHour, setScheduleHour] = useState(6);

  const loadStatus = async () => {
    try {
      const response = await axios.get(API_BASE + '/status');
      setStatus(response.data);
      
      // Actualizar configuración local
      setScheduleEnabled(response.data.auto_sync_enabled);
      setScheduleFrequency(response.data.sync_frequency);
      setScheduleHour(response.data.sync_hour);
    } catch (error) {
      console.error('Error loading sync status:', error);
      notifications.show({
        title: 'Error',
        message: 'No se pudo cargar el estado de sincronización',
        color: 'red'
      });
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  // Auto-refresh cuando está sincronizando
  useEffect(() => {
    if (status?.is_syncing || autoRefresh) {
      const interval = setInterval(loadStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [status?.is_syncing, autoRefresh]);

  const handleStartSync = async () => {
    setLoading(true);
    try {
      await axios.post(API_BASE + '/start', {
        process_after_download: true
      });
      
      notifications.show({
        title: 'Sincronización iniciada',
        message: 'La sincronización se está ejecutando en segundo plano',
        color: 'blue'
      });
      
      setAutoRefresh(true);
      setTimeout(loadStatus, 1000);
    } catch (error: any) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'No se pudo iniciar la sincronización',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStopSync = async () => {
    try {
      await axios.post(API_BASE + '/stop');
      
      notifications.show({
        title: 'Cancelación solicitada',
        message: 'La sincronización se detendrá en breve',
        color: 'orange'
      });
      
      setTimeout(loadStatus, 1000);
    } catch (error: any) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'No se pudo cancelar la sincronización',
        color: 'red'
      });
    }
  };

  const handleUpdateSchedule = async () => {
    try {
      await axios.put(API_BASE + '/schedule', {
        enabled: scheduleEnabled,
        frequency: scheduleFrequency,
        hour: scheduleHour
      });
      
      notifications.show({
        title: 'Configuración actualizada',
        message: `Sincronización automática ${scheduleEnabled ? 'habilitada' : 'deshabilitada'}`,
        color: 'green'
      });
      
      loadStatus();
    } catch (error: any) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'No se pudo actualizar la configuración',
        color: 'red'
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'idle': return 'green';
      case 'syncing': return 'blue';
      case 'processing': return 'cyan';
      case 'completed': return 'green';
      case 'error': return 'red';
      case 'cancelled': return 'orange';
      default: return 'gray';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'idle': return <IconCheck size={20} />;
      case 'syncing': return <IconDownload size={20} />;
      case 'processing': return <IconFileText size={20} />;
      case 'completed': return <IconCheck size={20} />;
      case 'error': return <IconAlertCircle size={20} />;
      case 'cancelled': return <IconX size={20} />;
      default: return <IconClock size={20} />;
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('es-AR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString('es-AR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!status) {
    return (
      <Card withBorder p="lg">
        <Text c="dimmed">Cargando estado de sincronización...</Text>
      </Card>
    );
  }

  const completionRate = status.boletines_pending > 0 
    ? Math.round((status.boletines_downloaded / (status.boletines_downloaded + status.boletines_pending)) * 100)
    : 100;

  return (
    <Stack gap="md">
      {/* Header con estado principal */}
      <Card withBorder p="lg" shadow="sm">
        <Group justify="space-between" mb="md">
          <Group gap="xs">
            <IconTrendingUp size={28} />
            <div>
              <Text size="xl" fw={600}>Sincronización de Boletines</Text>
              <Text size="sm" c="dimmed">Mantén tu base de datos actualizada automáticamente</Text>
            </div>
          </Group>
          
          <Badge 
            size="lg" 
            color={getStatusColor(status.status)}
            leftSection={getStatusIcon(status.status)}
          >
            {status.status.toUpperCase()}
          </Badge>
        </Group>

        {/* Current operation */}
        {status.current_operation && (
          <Alert color="blue" mb="md" icon={<IconClock size={16} />}>
            <Text size="sm">{status.current_operation}</Text>
          </Alert>
        )}

        {/* Error message */}
        {status.error_message && (
          <Alert color="red" mb="md" icon={<IconAlertCircle size={16} />}>
            <Text size="sm">{status.error_message}</Text>
          </Alert>
        )}

        {/* Stats Grid */}
        <Grid mb="md">
          <Grid.Col span={3}>
            <Paper withBorder p="md" radius="md">
              <Text size="xs" c="dimmed" mb={5}>Pendientes</Text>
              <Group gap="xs">
                <IconDownload size={18} color="orange" />
                <Text size="xl" fw={600}>{status.boletines_pending}</Text>
              </Group>
            </Paper>
          </Grid.Col>
          
          <Grid.Col span={3}>
            <Paper withBorder p="md" radius="md">
              <Text size="xs" c="dimmed" mb={5}>Descargados</Text>
              <Group gap="xs">
                <IconDownload size={18} color="blue" />
                <Text size="xl" fw={600}>{status.boletines_downloaded}</Text>
              </Group>
            </Paper>
          </Grid.Col>
          
          <Grid.Col span={3}>
            <Paper withBorder p="md" radius="md">
              <Text size="xs" c="dimmed" mb={5}>Procesados</Text>
              <Group gap="xs">
                <IconFileText size={18} color="green" />
                <Text size="xl" fw={600}>{status.boletines_processed}</Text>
              </Group>
            </Paper>
          </Grid.Col>
          
          <Grid.Col span={3}>
            <Paper withBorder p="md" radius="md">
              <Text size="xs" c="dimmed" mb={5}>Fallidos</Text>
              <Group gap="xs">
                <IconX size={18} color="red" />
                <Text size="xl" fw={600}>{status.boletines_failed}</Text>
              </Group>
            </Paper>
          </Grid.Col>
        </Grid>

        {/* Progress Bar */}
        {status.is_syncing && (
          <div>
            <Group justify="space-between" mb={5}>
              <Text size="sm" fw={500}>Progreso</Text>
              <Text size="sm" c="dimmed">{completionRate}%</Text>
            </Group>
            <Progress value={completionRate} size="lg" radius="xl" animated />
          </div>
        )}

        <Divider my="md" />

        {/* Action Buttons */}
        <Group justify="space-between">
          <Group gap="xs">
            {!status.is_syncing ? (
              <Button
                leftSection={<IconPlayerPlay size={18} />}
                onClick={handleStartSync}
                loading={loading}
                disabled={status.boletines_pending === 0}
              >
                Sincronizar Ahora
              </Button>
            ) : (
              <Button
                leftSection={<IconPlayerStop size={18} />}
                onClick={handleStopSync}
                color="red"
              >
                Detener
              </Button>
            )}
            
            <Tooltip label="Actualizar estado">
              <ActionIcon 
                variant="light" 
                size="lg" 
                onClick={loadStatus}
                disabled={status.is_syncing}
              >
                <IconRefresh size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>

          <Group gap="xs">
            <Text size="xs" c="dimmed">
              Última sincronización: {formatDateTime(status.last_sync_timestamp)}
            </Text>
          </Group>
        </Group>
      </Card>

      {/* Scheduler Configuration */}
      <Card withBorder p="lg" shadow="sm">
        <Group gap="xs" mb="md">
          <IconSettings size={24} />
          <Text size="lg" fw={600}>Sincronización Automática</Text>
        </Group>

        <Stack gap="md">
          <Switch
            label="Habilitar sincronización automática"
            description="Ejecutar sincronización según el cronograma configurado"
            checked={scheduleEnabled}
            onChange={(e) => setScheduleEnabled(e.currentTarget.checked)}
          />

          {scheduleEnabled && (
            <>
              <Select
                label="Frecuencia"
                description="Con qué frecuencia sincronizar"
                value={scheduleFrequency}
                onChange={(val) => setScheduleFrequency(val || 'daily')}
                data={[
                  { value: 'daily', label: 'Diario' },
                  { value: 'weekly', label: 'Semanal (lunes)' },
                  { value: 'manual', label: 'Solo manual' }
                ]}
              />

              {scheduleFrequency !== 'manual' && (
                <NumberInput
                  label="Hora de ejecución"
                  description="Hora del día (0-23)"
                  value={scheduleHour}
                  onChange={(val) => setScheduleHour(Number(val))}
                  min={0}
                  max={23}
                  suffix=":00"
                />
              )}

              {status.next_scheduled_sync && (
                <Alert color="blue" icon={<IconCalendar size={16} />}>
                  <Text size="sm">
                    Próxima ejecución: {formatDateTime(status.next_scheduled_sync)}
                  </Text>
                </Alert>
              )}
            </>
          )}

          <Button onClick={handleUpdateSchedule} leftSection={<IconCheck size={18} />}>
            Guardar Configuración
          </Button>
        </Stack>
      </Card>

      {/* Timeline/History */}
      <Card withBorder p="lg" shadow="sm">
        <Group gap="xs" mb="md">
          <IconClock size={24} />
          <Text size="lg" fw={600}>Estado Actual</Text>
        </Group>

        <Timeline active={1} bulletSize={24} lineWidth={2}>
          <Timeline.Item 
            bullet={<IconCalendar size={12} />} 
            title="Última fecha detectada"
          >
            <Text size="sm" c="dimmed">{formatDate(status.last_detected_date)}</Text>
          </Timeline.Item>

          <Timeline.Item 
            bullet={<IconCheck size={12} />} 
            title="Última sincronización"
            color={status.last_sync_timestamp ? 'green' : 'gray'}
          >
            <Text size="sm" c="dimmed">
              {status.last_sync_timestamp 
                ? formatDateTime(status.last_sync_timestamp)
                : 'Nunca ejecutada'}
            </Text>
          </Timeline.Item>

          <Timeline.Item 
            bullet={<IconClock size={12} />} 
            title="Próxima ejecución programada"
            color={status.next_scheduled_sync ? 'blue' : 'gray'}
          >
            <Text size="sm" c="dimmed">
              {status.next_scheduled_sync 
                ? formatDateTime(status.next_scheduled_sync)
                : 'No programada'}
            </Text>
          </Timeline.Item>
        </Timeline>
      </Card>
    </Stack>
  );
};

export default SyncDashboard;
