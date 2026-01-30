
// Archivo: /watcher-monolith/frontend/src/components/RedFlagsViewer.tsx

import React, { useState, useEffect } from 'react';
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
  Timeline,
  Highlight,
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
  evidence: string[];
  recommendation: string;
  visual_evidence?: {
    page: number;
    coordinates: { x: number; y: number; width: number; height: number }[];
    highlighted_text: string[];
  };
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

  const handleViewEvidence = (flag: RedFlag) => {
    setSelectedFlag(flag);
    setModalOpened(true);
  };

  const handleViewInPDF = (flag: RedFlag) => {
    if (pdfUrl && flag.visual_evidence) {
      const params = new URLSearchParams({
        page: flag.visual_evidence.page.toString(),
        highlight: JSON.stringify(flag.visual_evidence.coordinates)
      });
      window.open(`${pdfUrl}?${params}`, '_blank');
    }
  };

  return (
    <>
      <Card withBorder shadow="sm" radius="md">
        <Group justify="space-between" mb="md">
          <Text size="lg" fw={500}>Red Flags Detectadas</Text>
          <Badge size="lg" variant="light" color={redFlags.length > 0 ? 'red' : 'green'}>
            {redFlags.length} detectadas
          </Badge>
        </Group>

        {redFlags.length === 0 ? (
          <Alert icon={<IconFlag size={16} />} title="Sin red flags" color="green">
            No se detectaron irregularidades en este documento.
          </Alert>
        ) : (
          <Stack gap="sm">
            {redFlags.map((flag, index) => (
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
                    
                    <Text fw={500} size="sm">
                      {flag.flag_type.replace(/_/g, ' ')}
                    </Text>
                    
                    <Text size="sm" c="dimmed">
                      {flag.description}
                    </Text>
                    
                    <Group gap="xs">
                      <Button 
                        size="xs" 
                        variant="light"
                        leftSection={<IconEye size={14} />}
                        onClick={() => handleViewEvidence(flag)}
                      >
                        Ver Evidencia
                      </Button>
                      
                      {flag.visual_evidence && pdfUrl && (
                        <Tooltip label="Ver en PDF original">
                          <ActionIcon 
                            variant="light" 
                            color="blue"
                            onClick={() => handleViewInPDF(flag)}
                          >
                            <IconDownload size={14} />
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
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title={`Evidencia: ${selectedFlag?.flag_type.replace(/_/g, ' ')}`}
        size="lg"
      >
        {selectedFlag && (
          <Stack gap="md">
            <Alert 
              icon={getSeverityIcon(selectedFlag.severity)}
              color={getSeverityColor(selectedFlag.severity)}
              title={`Severidad: ${selectedFlag.severity}`}
            >
              {selectedFlag.description}
            </Alert>

            <div>
              <Text size="sm" fw={500} mb="xs">Evidencia encontrada:</Text>
              <List size="sm">
                {selectedFlag.evidence.map((evidence, idx) => (
                  <List.Item key={idx}>{evidence}</List.Item>
                ))}
              </List>
            </div>

            <div>
              <Text size="sm" fw={500} mb="xs">Recomendación:</Text>
              <Text size="sm" c="dimmed">
                {selectedFlag.recommendation}
              </Text>
            </div>

            {selectedFlag.visual_evidence && (
              <div>
                <Text size="sm" fw={500} mb="xs">Ubicación en documento:</Text>
                <Text size="sm" c="dimmed">
                  Página {selectedFlag.visual_evidence.page}
                </Text>
                
                {selectedFlag.visual_evidence.highlighted_text.length > 0 && (
                  <div>
                    <Text size="sm" fw={500} mt="xs" mb="xs">Texto destacado:</Text>
                    {selectedFlag.visual_evidence.highlighted_text.map((text, idx) => (
                      <Highlight 
                        key={idx}
                        highlight={text}
                        highlightStyles={{ backgroundColor: 'yellow', color: 'black' }}
                      >
                        {text}
                      </Highlight>
                    ))}
                  </div>
                )}

                <Button 
                  mt="md"
                  variant="filled"
                  leftSection={<IconEye size={16} />}
                  onClick={() => handleViewInPDF(selectedFlag)}
                  fullWidth
                >
                  Abrir PDF en ubicación exacta
                </Button>
              </div>
            )}
          </Stack>
        )}
      </Modal>
    </>
  );
};

export default RedFlagsViewer;
