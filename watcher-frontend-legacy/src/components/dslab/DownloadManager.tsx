import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Group,
  Text,
  Button,
  Stack,
  MultiSelect,
  Switch,
  Progress,
  Alert,
  Badge,
  Divider,
  ActionIcon,
  Tooltip,
  Timeline,
  Box,
  Select,
  Table,
  ScrollArea,
  Accordion
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import {
  IconDownload,
  IconPlayerPlay,
  IconPlayerStop,
  IconCheck,
  IconAlertCircle,
  IconClock,
  IconRefresh,
  IconCalendarMonth,
  IconAlertTriangle
} from '@tabler/icons-react';

interface DownloadProgress {
  total_files: number;
  downloaded: number;
  failed: number;
  current_file: string | null;
  status: 'downloading' | 'completed' | 'failed' | 'cancelled';
  errors: string[];
}

interface DownloadManagerProps {
  onDownloadComplete?: () => void;
}

const DownloadManager: React.FC<DownloadManagerProps> = ({ onDownloadComplete }) => {
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [selectedSections, setSelectedSections] = useState<string[]>(['1', '2', '3', '4', '5']);
  const [skipWeekends, setSkipWeekends] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  
  const MONTH_NAMES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  const sectionOptions = [
    { value: '1', label: '1ª Sección - Designaciones y Decretos' },
    { value: '2', label: '2ª Sección - Compras y Contrataciones' },
    { value: '3', label: '3ª Sección - Subsidios y Transferencias' },
    { value: '4', label: '4ª Sección - Obras Públicas' },
    { value: '5', label: '5ª Sección - Notificaciones Judiciales' }
  ];
  
  // Memoizar las opciones del mes para evitar recrearlas en cada render
  const monthPresetOptions = useMemo(() => {
    const options: Array<{ value: string; label: string }> = [];
    
    // Generar opciones para 2024, 2025, 2026 (más recientes primero)
    for (let year = 2026; year >= 2024; year--) {
      for (let month = 1; month <= 12; month++) {
        options.push({
          value: `${year}-${month}`,
          label: `${MONTH_NAMES[month - 1]} ${year}`
        });
      }
    }
    
    return options;
  }, []);
  
  const handleMonthPreset = (value: string | null) => {
    if (!value) return;
    
    setSelectedPreset(value);
    const [year, month] = value.split('-').map(Number);
    
    // Primer día del mes
    const firstDay = new Date(year, month - 1, 1);
    
    // Último día del mes
    const lastDay = new Date(year, month, 0);
    
    setStartDate(firstDay);
    setEndDate(lastDay);
  };
  
  const parseErrorsForManualReview = (errors: string[]) => {
    // Parsear errores para identificar archivos de días hábiles no disponibles
    const manualReviewItems = errors
      .filter(error => {
        // Solo considerar errores de archivos no disponibles (no errores de red)
        return error.includes('HTTP 404') || error.includes('not_available');
      })
      .map(error => {
        const parts = error.split(':');
        const filename = parts[0].trim();
        
        // Extraer fecha del filename (YYYYMMDD_N_Secc.pdf)
        const match = filename.match(/(\d{4})(\d{2})(\d{2})_(\d)_Secc\.pdf/);
        if (match) {
          const [, year, month, day, section] = match;
          const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
          const isWeekend = date.getDay() === 0 || date.getDay() === 6;
          
          return {
            filename,
            date: date.toLocaleDateString('es-AR'),
            dateObj: date,
            section: parseInt(section),
            isWeekend,
            isWorkday: !isWeekend,
            error: parts[1]?.trim() || 'No disponible'
          };
        }
        return null;
      })
      .filter(item => item !== null);
    
    return manualReviewItems;
  };

  // Polling para obtener progreso
  useEffect(() => {
    if (!taskId || !isDownloading) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/downloader/download/status/${taskId}`);
        
        if (!response.ok) {
          throw new Error('Error obteniendo estado de descarga');
        }

        const data: DownloadProgress = await response.json();
        setProgress(data);

        // Si terminó, dejar de hacer polling
        if (data.status !== 'downloading') {
          setIsDownloading(false);
          
          if (data.status === 'completed' && onDownloadComplete) {
            onDownloadComplete();
          }
        }
      } catch (err) {
        console.error('Error polling status:', err);
      }
    }, 2000); // Poll cada 2 segundos

    return () => clearInterval(interval);
  }, [taskId, isDownloading, onDownloadComplete]);

  const handleStartDownload = async () => {
    if (!startDate || !endDate) {
      setError('Debes seleccionar fechas de inicio y fin');
      return;
    }

    if (selectedSections.length === 0) {
      setError('Debes seleccionar al menos una sección');
      return;
    }

    try {
      setError(null);
      setIsDownloading(true);

      const response = await fetch('/api/v1/downloader/download/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          start_date: formatDate(startDate),
          end_date: formatDate(endDate),
          sections: selectedSections.map(s => parseInt(s)),
          skip_weekends: skipWeekends
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error iniciando descarga');
      }

      const data = await response.json();
      setTaskId(data.task_id);
      
      // Inicializar progreso
      setProgress({
        total_files: 0,
        downloaded: 0,
        failed: 0,
        current_file: null,
        status: 'downloading',
        errors: []
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
      setIsDownloading(false);
    }
  };

  const handleCancelDownload = async () => {
    if (!taskId) return;

    try {
      const response = await fetch(`/api/v1/downloader/download/${taskId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setIsDownloading(false);
        setError('Descarga cancelada');
      }
    } catch (err) {
      console.error('Error cancelando descarga:', err);
    }
  };

  const formatDate = (date: Date | null): string => {
    if (!date) return '';
    return date.toISOString().split('T')[0];
  };

  const getProgressPercentage = (): number => {
    if (!progress || progress.total_files === 0) return 0;
    return Math.round(((progress.downloaded + progress.failed) / progress.total_files) * 100);
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'downloading': return 'blue';
      case 'completed': return 'green';
      case 'failed': return 'red';
      case 'cancelled': return 'gray';
      default: return 'gray';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'downloading': return <IconClock size={16} />;
      case 'completed': return <IconCheck size={16} />;
      case 'failed': return <IconAlertCircle size={16} />;
      case 'cancelled': return <IconPlayerStop size={16} />;
      default: return null;
    }
  };

  return (
    <Card withBorder p="lg" shadow="sm">
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Group gap="xs">
            <IconDownload size={24} />
            <Text size="xl" fw={600}>
              Descargar Boletines
            </Text>
          </Group>
          
          {progress && (
            <Badge 
              size="lg" 
              color={getStatusColor(progress.status)}
              leftSection={getStatusIcon(progress.status)}
            >
              {progress.status.toUpperCase()}
            </Badge>
          )}
        </Group>

        <Divider />

        {/* Formulario de descarga */}
        {!isDownloading && progress?.status !== 'downloading' && (
          <Stack gap="md">
            {/* Preset de mes completo */}
            <Card withBorder p="sm" style={{ backgroundColor: '#f8f9fa' }}>
              <Stack gap="xs">
                <Group gap="xs">
                  <IconCalendarMonth size={20} />
                  <Text size="sm" fw={600}>Descarga Rápida por Mes Completo</Text>
                </Group>
                <Select
                  placeholder="Selecciona un mes para descargar del 1 al último día"
                  data={monthPresetOptions}
                  value={selectedPreset}
                  onChange={handleMonthPreset}
                  searchable
                  clearable
                />
                {selectedPreset && (
                  <Alert color="blue" variant="light">
                    <Text size="sm">
                      Se descargará del {startDate?.toLocaleDateString('es-AR')} al {endDate?.toLocaleDateString('es-AR')}
                    </Text>
                  </Alert>
                )}
              </Stack>
            </Card>
            
            <Divider label="O selecciona fechas personalizadas" labelPosition="center" />
            
            <Group grow>
              <DatePickerInput
                label="Fecha de inicio"
                placeholder="Selecciona fecha"
                value={startDate}
                onChange={(date) => {
                  setStartDate(date);
                  setSelectedPreset(null); // Limpiar preset si se cambia manualmente
                }}
                clearable
              />
              <DatePickerInput
                label="Fecha de fin"
                placeholder="Selecciona fecha"
                value={endDate}
                onChange={(date) => {
                  setEndDate(date);
                  setSelectedPreset(null); // Limpiar preset si se cambia manualmente
                }}
                clearable
              />
            </Group>

            <MultiSelect
              label="Secciones a descargar"
              placeholder="Selecciona secciones"
              data={sectionOptions}
              value={selectedSections}
              onChange={setSelectedSections}
              searchable
              clearable
            />

            <Switch
              label="Omitir fines de semana"
              description="Los boletines no se publican los sábados y domingos"
              checked={skipWeekends}
              onChange={(event) => setSkipWeekends(event.currentTarget.checked)}
            />

            <Button
              leftSection={<IconPlayerPlay size={20} />}
              size="lg"
              fullWidth
              onClick={handleStartDownload}
              disabled={!startDate || !endDate || selectedSections.length === 0}
            >
              Iniciar Descarga
            </Button>
          </Stack>
        )}

        {/* Progreso de descarga */}
        {progress && isDownloading && (
          <Stack gap="md">
            <Box>
              <Group justify="space-between" mb="xs">
                <Text size="sm" fw={500}>Progreso de descarga</Text>
                <Text size="sm" c="dimmed">
                  {progress.downloaded + progress.failed} / {progress.total_files}
                </Text>
              </Group>
              
              <Progress 
                value={getProgressPercentage()} 
                size="xl" 
                animated
                striped
                color={progress.failed > 0 ? 'orange' : 'blue'}
              />
              
              <Group justify="space-between" mt="xs">
                <Text size="xs" c="dimmed">
                  {getProgressPercentage()}% completado
                </Text>
                <Group gap="md">
                  <Text size="xs" c="teal">
                    ✓ {progress.downloaded} exitosos
                  </Text>
                  {progress.failed > 0 && (
                    <Text size="xs" c="red">
                      ✗ {progress.failed} fallidos
                    </Text>
                  )}
                </Group>
              </Group>
            </Box>

            {progress.current_file && (
              <Alert color="blue" icon={<IconDownload size={16} />}>
                <Text size="sm">Descargando: <strong>{progress.current_file}</strong></Text>
              </Alert>
            )}

            <Button
              color="red"
              variant="light"
              leftSection={<IconPlayerStop size={16} />}
              onClick={handleCancelDownload}
              fullWidth
            >
              Cancelar Descarga
            </Button>
          </Stack>
        )}

        {/* Resultado final */}
        {progress && !isDownloading && progress.status !== 'downloading' && (
          <Stack gap="md">
            {progress.status === 'completed' && (
              <Alert 
                color="green" 
                icon={<IconCheck size={20} />}
                title="¡Descarga completada!"
              >
                <Stack gap="xs">
                  <Text size="sm">
                    Se descargaron exitosamente {progress.downloaded} de {progress.total_files} archivos
                  </Text>
                  {progress.failed > 0 && (
                    <Text size="sm" c="orange">
                      {progress.failed} archivos no pudieron descargarse (probablemente no estaban disponibles)
                    </Text>
                  )}
                </Stack>
              </Alert>
            )}

            {progress.status === 'failed' && (
              <Alert 
                color="red" 
                icon={<IconAlertCircle size={20} />}
                title="Error en la descarga"
              >
                <Text size="sm">
                  La descarga falló. Revisa los errores a continuación.
                </Text>
              </Alert>
            )}

            {progress.status === 'cancelled' && (
              <Alert 
                color="gray" 
                icon={<IconPlayerStop size={20} />}
                title="Descarga cancelada"
              >
                <Text size="sm">
                  Se descargaron {progress.downloaded} archivos antes de cancelar
                </Text>
              </Alert>
            )}

            {/* Archivos no disponibles para revisión manual */}
            {progress.errors.length > 0 && (
              <Accordion variant="contained">
                <Accordion.Item value="errors">
                  <Accordion.Control icon={<IconAlertTriangle size={20} color="#fa5252" />}>
                    <Group justify="space-between" pr="md">
                      <div>
                        <Text size="sm" fw={600}>Archivos No Disponibles</Text>
                        <Text size="xs" c="dimmed">
                          Requieren verificación manual
                        </Text>
                      </div>
                      <Badge color="red" size="lg">
                        {progress.errors.length}
                      </Badge>
                    </Group>
                  </Accordion.Control>
                  <Accordion.Panel>
                    {(() => {
                      const manualReviewItems = parseErrorsForManualReview(progress.errors);
                      const workdayErrors = manualReviewItems.filter(item => item?.isWorkday);
                      const weekendErrors = manualReviewItems.filter(item => !item?.isWorkday);
                      
                      return (
                        <Stack gap="md">
                          {workdayErrors.length > 0 && (
                            <Box>
                              <Alert color="red" icon={<IconAlertTriangle size={16} />} mb="sm">
                                <Text size="sm" fw={600}>
                                  ⚠️ {workdayErrors.length} archivo(s) de días hábiles no disponibles
                                </Text>
                                <Text size="xs">
                                  Estos archivos deberían estar disponibles. Verifica manualmente en el sitio oficial.
                                </Text>
                              </Alert>
                              
                              <ScrollArea h={200}>
                                <Table striped highlightOnHover>
                                  <Table.Thead>
                                    <Table.Tr>
                                      <Table.Th>Fecha</Table.Th>
                                      <Table.Th>Sección</Table.Th>
                                      <Table.Th>Archivo</Table.Th>
                                      <Table.Th>Estado</Table.Th>
                                    </Table.Tr>
                                  </Table.Thead>
                                  <Table.Tbody>
                                    {workdayErrors.map((item, idx) => (
                                      <Table.Tr key={idx}>
                                        <Table.Td>
                                          <Text size="sm">{item?.date}</Text>
                                        </Table.Td>
                                        <Table.Td>
                                          <Badge color="blue" size="sm">
                                            {item?.section}ª Secc.
                                          </Badge>
                                        </Table.Td>
                                        <Table.Td>
                                          <Text size="xs" style={{ fontFamily: 'monospace' }}>
                                            {item?.filename}
                                          </Text>
                                        </Table.Td>
                                        <Table.Td>
                                          <Badge color="red" size="sm">
                                            No disponible
                                          </Badge>
                                        </Table.Td>
                                      </Table.Tr>
                                    ))}
                                  </Table.Tbody>
                                </Table>
                              </ScrollArea>
                              
                              <Button
                                variant="light"
                                color="blue"
                                size="xs"
                                mt="sm"
                                fullWidth
                                component="a"
                                href="https://boletinoficial.cba.gov.ar"
                                target="_blank"
                              >
                                Verificar en Sitio Oficial
                              </Button>
                            </Box>
                          )}
                          
                          {weekendErrors.length > 0 && (
                            <Box>
                              <Text size="sm" fw={500} c="dimmed" mb="xs">
                                Archivos de fin de semana ({weekendErrors.length})
                              </Text>
                              <Text size="xs" c="dimmed">
                                Normal: Los boletines no se publican los fines de semana
                              </Text>
                            </Box>
                          )}
                          
                          {manualReviewItems.length === 0 && (
                            <Alert color="orange">
                              <Text size="sm">
                                Errores de conexión o formato. Intenta nuevamente.
                              </Text>
                              <ScrollArea h={150} mt="sm">
                                {progress.errors.map((error, idx) => (
                                  <Text key={idx} size="xs" c="dimmed" style={{ fontFamily: 'monospace' }}>
                                    {error}
                                  </Text>
                                ))}
                              </ScrollArea>
                            </Alert>
                          )}
                        </Stack>
                      );
                    })()}
                  </Accordion.Panel>
                </Accordion.Item>
              </Accordion>
            )}

            <Group grow>
              <Button
                variant="light"
                leftSection={<IconRefresh size={16} />}
                onClick={() => {
                  setProgress(null);
                  setTaskId(null);
                  setError(null);
                }}
              >
                Nueva Descarga
              </Button>
              
              {progress.status === 'completed' && onDownloadComplete && (
                <Button
                  color="teal"
                  leftSection={<IconCheck size={16} />}
                  onClick={onDownloadComplete}
                >
                  Ver Resultados
                </Button>
              )}
            </Group>
          </Stack>
        )}

        {/* Mensajes de error */}
        {error && !progress && (
          <Alert 
            color="red" 
            icon={<IconAlertCircle size={16} />}
            title="Error"
            withCloseButton
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        )}
      </Stack>
    </Card>
  );
};

export default DownloadManager;

