
// Archivo: /watcher-monolith/frontend/src/components/RedFlagsViewer.tsx

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Badge,
  Group,
  Text,
  Stack,
  Alert,
  Button,
  Modal,
  List,
  ActionIcon,
  Tooltip
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconEye,
  IconDownload,
  IconFlag,
  IconExclamationMark
} from '@tabler/icons-react';

interface RedFlag {
  id: string;
  flag_type: string;
  severity: 'CRITICO' | 'ALTO' | 'MEDIO' | 'INFORMATIVO';
  confidence: number;
  description: string;
  evidence?: string[];
  recommendation?: string;
  visual_evidence?: {
    page: number;
    coordinates: { x: number; y: number; width: number; height: number }[];
    highlighted_text?: string[];
  };
  metadata?: Record<string, any>;
}

interface RedFlagsViewerProps {
  documentId: string;
  redFlags: RedFlag[];
  pdfUrl?: string;
}

const RedFlagsViewer: React.FC<RedFlagsViewerProps> = ({ 
  documentId, 
  redFlags, 
  pdfUrl 
}) => {
  const [selectedFlag, setSelectedFlag] = useState<RedFlag | null>(null);
  const [modalOpened, setModalOpened] = useState(false);

  // Debug: log props when component renders
  useEffect(() => {
    console.log('RedFlagsViewer rendered with:', { documentId, redFlags, pdfUrl });
  }, [documentId, redFlags, pdfUrl]);

  // Debug: monitor modal state changes
  useEffect(() => {
    console.log('Modal state changed:', { modalOpened, hasSelectedFlag: !!selectedFlag });
  }, [modalOpened, selectedFlag]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICO': return 'red';
      case 'ALTO': return 'orange';
      case 'MEDIO': return 'yellow';
      case 'INFORMATIVO': return 'blue';
      default: return 'gray';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICO': return <IconExclamationMark size={16} />;
      case 'ALTO': return <IconAlertTriangle size={16} />;
      default: return <IconFlag size={16} />;
    }
  };

  const handleViewEvidence = useCallback((flag: RedFlag, event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    console.log('handleViewEvidence called with flag:', flag);
    console.log('Flag properties:', {
      hasEvidence: Array.isArray(flag.evidence),
      evidenceLength: Array.isArray(flag.evidence) ? flag.evidence.length : 0,
      hasRecommendation: !!flag.recommendation,
      hasVisualEvidence: !!flag.visual_evidence,
      allKeys: Object.keys(flag)
    });
    // Establecer ambos estados de forma síncrona
    setSelectedFlag(flag);
    setModalOpened(true);
    console.log('Modal state set - opened: true, flag:', flag.id);
  }, []);

  const handleViewInPDF = (flag: RedFlag) => {
    console.log('handleViewInPDF called with:', { pdfUrl, flag });
    if (pdfUrl && flag.visual_evidence) {
      const params = new URLSearchParams({
        page: flag.visual_evidence.page.toString(),
        highlight: JSON.stringify(flag.visual_evidence.coordinates)
      });
      const fullUrl = `${pdfUrl}?${params}`;
      console.log('Opening PDF URL:', fullUrl);
      window.open(fullUrl, '_blank');
    } else {
      console.warn('Cannot open PDF:', { pdfUrl, hasVisualEvidence: !!flag.visual_evidence });
    }
  };

  return (
    <>
      <Card withBorder shadow="sm" radius="md">
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <div>
              <Text size="lg" fw={500} mb={4}>Irregularidades Detectadas</Text>
              <Text size="xs" c="dimmed">
                Situaciones que requieren atención o revisión
              </Text>
            </div>
            <Badge size="lg" variant="light" color={redFlags.length > 0 ? 'red' : 'green'}>
              {redFlags.length} detectadas
            </Badge>
          </Group>

          {redFlags.length > 0 && (
            <Alert icon={<IconFlag size={16} />} color="blue" variant="light">
              <Text size="xs">
                <strong>¿Qué son estas irregularidades?</strong> Son situaciones detectadas en el documento 
                que pueden indicar falta de transparencia, procesos poco claros, o posibles problemas 
                en el uso de fondos públicos. Cada una incluye evidencia y recomendaciones.
              </Text>
            </Alert>
          )}
        </Stack>

        {redFlags.length === 0 ? (
          <Alert icon={<IconFlag size={16} />} title="Sin red flags" color="green">
            No se detectaron irregularidades en este documento.
          </Alert>
        ) : (
          <Stack gap="sm">
            {redFlags.map((flag) => (
              <Card key={flag.id} withBorder radius="sm" p="sm">
                <Group justify="space-between" align="flex-start">
                  <Stack gap="xs" style={{ flex: 1 }}>
                    <Group gap="xs">
                      <Badge 
                        color={getSeverityColor(flag.severity)}
                        variant="filled"
                        leftSection={getSeverityIcon(flag.severity)}
                      >
                        {flag.severity}
                      </Badge>
                      <Text size="sm" c="dimmed">
                        Confianza: {(flag.confidence * 100).toFixed(1)}%
                      </Text>
                    </Group>
                    
                    <Text fw={500} size="sm" mb={4}>
                      {flag.flag_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </Text>
                    
                    <Text size="sm" c="dimmed" lineClamp={2}>
                      {flag.description}
                    </Text>
                    
                    {flag.evidence && Array.isArray(flag.evidence) && flag.evidence.length > 0 && (
                      <Text size="xs" c="dimmed" mt={4}>
                        {flag.evidence.length} evidencia{flag.evidence.length > 1 ? 's' : ''} encontrada{flag.evidence.length > 1 ? 's' : ''}
                      </Text>
                    )}
                    
                    <Group gap="xs" mt="xs">
                      <Button 
                        size="sm" 
                        variant="filled"
                        color={getSeverityColor(flag.severity)}
                        leftSection={<IconEye size={16} />}
                        onClick={(e) => handleViewEvidence(flag, e)}
                        type="button"
                      >
                        Ver Evidencia Completa
                      </Button>
                      
                      {flag.visual_evidence && pdfUrl && (
                        <Tooltip label="Ver en PDF original en la ubicación exacta">
                          <ActionIcon 
                            variant="light" 
                            color="blue"
                            size="lg"
                            onClick={() => handleViewInPDF(flag)}
                          >
                            <IconDownload size={16} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </Group>
                  </Stack>
                </Group>
              </Card>
            ))}
          </Stack>
        )}
      </Card>

      {/* Modal de evidencia detallada */}
      <Modal
        opened={modalOpened && !!selectedFlag}
        onClose={() => {
          console.log('Modal closing - user action');
          setModalOpened(false);
          // Limpiar el flag después de que el modal se cierre
          setTimeout(() => {
            setSelectedFlag(null);
            console.log('Selected flag cleared');
          }, 300);
        }}
        title={selectedFlag ? `Evidencia: ${selectedFlag.flag_type?.replace(/_/g, ' ') || 'Red Flag'}` : 'Evidencia'}
        size="lg"
        centered
        overlayProps={{ opacity: 0.55, blur: 3 }}
        closeOnClickOutside={true}
        closeOnEscape={true}
        trapFocus={true}
        withCloseButton={true}
        keepMounted={false}
        zIndex={1000}
      >
        {(() => {
          console.log('Modal content rendering, selectedFlag:', selectedFlag);
          if (!selectedFlag) {
            return (
              <Alert color="red" title="Error">
                No se pudo cargar la información del flag seleccionado.
              </Alert>
            );
          }

          try {
            return (
              <Stack gap="md">
                {/* Información básica del flag */}
                <Alert 
                  icon={getSeverityIcon(selectedFlag.severity)}
                  color={getSeverityColor(selectedFlag.severity)}
                  title={`Severidad: ${selectedFlag.severity}`}
                >
                  {selectedFlag.description || 'Sin descripción disponible'}
                </Alert>

                {/* Información de confianza */}
                <Card withBorder p="md" bg="gray.0">
                  <Group gap="md">
                    <div>
                      <Text size="xs" c="dimmed" mb={4}>Nivel de Confianza</Text>
                      <Group gap="xs" align="center">
                        <Text size="lg" fw={600}>
                          {(selectedFlag.confidence * 100).toFixed(0)}%
                        </Text>
                        <Badge 
                          color={selectedFlag.confidence > 0.8 ? 'green' : selectedFlag.confidence > 0.6 ? 'yellow' : 'orange'}
                          variant="light"
                          size="sm"
                        >
                          {selectedFlag.confidence > 0.8 ? 'Alta' : selectedFlag.confidence > 0.6 ? 'Media' : 'Baja'}
                        </Badge>
                      </Group>
                      <Text size="xs" c="dimmed" mt={4}>
                        Probabilidad de que sea una irregularidad real
                      </Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed" mb={4}>Tipo de Irregularidad</Text>
                      <Text size="sm" fw={500}>
                        {selectedFlag.flag_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'No especificado'}
                      </Text>
                    </div>
                  </Group>
                </Card>

                {/* Evidencia encontrada */}
                <div>
                  <Text size="sm" fw={600} mb="xs">¿Qué se encontró?</Text>
                  <Text size="xs" c="dimmed" mb="sm">
                    Detalles específicos que justifican esta alerta:
                  </Text>
                  {Array.isArray(selectedFlag.evidence) && selectedFlag.evidence.length > 0 ? (
                    <Card withBorder p="sm" bg="gray.0">
                      <List size="sm" spacing="xs">
                        {selectedFlag.evidence.map((evidence, idx) => (
                          <List.Item key={idx} icon={<IconFlag size={14} />}>
                            <Text size="sm">{String(evidence)}</Text>
                          </List.Item>
                        ))}
                      </List>
                    </Card>
                  ) : (
                    <Alert color="gray" variant="light">
                      <Text size="sm" c="dimmed">
                        No hay evidencia detallada disponible para esta irregularidad.
                      </Text>
                    </Alert>
                  )}
                </div>

                {/* Recomendación */}
                <div>
                  <Text size="sm" fw={600} mb="xs">¿Qué se recomienda hacer?</Text>
                  {selectedFlag.recommendation ? (
                    <Alert color="blue" variant="light" icon={<IconFlag size={16} />}>
                      <Text size="sm">
                        {String(selectedFlag.recommendation)}
                      </Text>
                    </Alert>
                  ) : (
                    <Alert color="gray" variant="light">
                      <Text size="sm" c="dimmed">
                        Se recomienda revisar el documento completo y solicitar información adicional 
                        a la entidad responsable para aclarar esta situación.
                      </Text>
                    </Alert>
                  )}
                </div>

                {/* Evidencia visual */}
                {selectedFlag.visual_evidence ? (
                  <div>
                    <Text size="sm" fw={500} mb="xs">Ubicación en documento:</Text>
                    <Text size="sm" c="dimmed" mb="md">
                      Página {selectedFlag.visual_evidence.page || 'No especificada'}
                    </Text>
                    
                    {selectedFlag.visual_evidence.highlighted_text && 
                     Array.isArray(selectedFlag.visual_evidence.highlighted_text) &&
                     selectedFlag.visual_evidence.highlighted_text.length > 0 && (
                      <div>
                        <Text size="sm" fw={500} mt="xs" mb="xs">Texto destacado:</Text>
                        {selectedFlag.visual_evidence.highlighted_text.map((text, idx) => (
                          <Text key={idx} size="sm" p="xs" bg="yellow.1" mb="xs">
                            {String(text)}
                          </Text>
                        ))}
                      </div>
                    )}

                    {pdfUrl && (
                      <Button 
                        mt="md"
                        variant="filled"
                        leftSection={<IconEye size={16} />}
                        onClick={() => handleViewInPDF(selectedFlag)}
                        fullWidth
                      >
                        Abrir PDF en ubicación exacta
                      </Button>
                    )}
                  </div>
                ) : (
                  <div>
                    <Text size="sm" fw={500} mb="xs">Ubicación en documento:</Text>
                    <Text size="sm" c="dimmed" fs="italic">
                      No hay información de ubicación específica disponible.
                    </Text>
                  </div>
                )}

                {/* Información adicional si existe */}
                {selectedFlag.metadata && Object.keys(selectedFlag.metadata).length > 0 && (
                  <div>
                    <Text size="sm" fw={500} mb="xs">Información adicional:</Text>
                    <Text size="xs" c="dimmed" style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(selectedFlag.metadata, null, 2)}
                    </Text>
                  </div>
                )}
              </Stack>
            );
          } catch (error) {
            console.error('Error rendering modal content:', error);
            return (
              <Alert color="red" title="Error al renderizar">
                Ocurrió un error al mostrar la información: {String(error)}
              </Alert>
            );
          }
        })()}
      </Modal>
    </>
  );
};

export default RedFlagsViewer;
