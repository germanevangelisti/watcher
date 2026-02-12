import { useEffect, useState } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Badge,
  Progress,
  Card,
  Grid,
  ThemeIcon,
  Accordion,
  Table,
  Button,
  Anchor,
  Tooltip,
  Alert,
  Loader,
  Center,
} from '@mantine/core';
import {
  IconFileText,
  IconDownload,
  IconCheck,
  IconX,
  IconClock,
  IconAlertCircle,
  IconExternalLink,
  IconDatabase,
  IconRefresh,
  IconInfoCircle,
  IconEdit,
  IconLink,
  IconUpload,
  IconPlayerPlay,
} from '@tabler/icons-react';
import { getDocumentsOverview, syncRequiredDocuments, getJurisdictionDocuments, updateDocumentUrl, uploadDocumentFile, getRequiredDocuments } from '../../services/api';
import { DocumentUrlEditor } from './DocumentUrlEditor';
import { DocumentProcessingModal } from './DocumentProcessingModal';
import { useRef } from 'react';
import { notifications } from '@mantine/notifications';

interface Document {
  id: number;
  document_name: string;
  document_type: string;
  period: string | null;
  status: string;
  expected_format: string;
  expected_url: string | null;
  local_path: string | null;
  downloaded_at: string | null;
  processed_at: string | null;
  indexed_in_rag: boolean;
  metadata: any;
}

interface JurisdictionSummary {
  jurisdiction_code: string;
  jurisdiction_id: number | null;
  jurisdiction_name: string;
  applicable_laws: string[];
  total_documents: number;
  missing: number;
  downloaded: number;
  processed: number;
  coverage_percentage: number;
  by_type: Record<string, { total: number; missing: number; processed: number }>;
}

interface OverviewData {
  jurisdictions: JurisdictionSummary[];
  total_documents: number;
  total_missing: number;
  total_processed: number;
  overall_coverage: number;
}

const STATUS_CONFIG = {
  missing: {
    label: 'Faltante',
    color: 'red',
    icon: IconX,
    description: 'No descargado ni encontrado',
  },
  downloaded: {
    label: 'Descargado',
    color: 'yellow',
    icon: IconDownload,
    description: 'Descargado pero no procesado',
  },
  processed: {
    label: 'Procesado',
    color: 'green',
    icon: IconCheck,
    description: 'Descargado y procesado con RAG',
  },
  failed: {
    label: 'Error',
    color: 'orange',
    icon: IconAlertCircle,
    description: 'Falló descarga o procesamiento',
  },
};

const FORMAT_ICONS: Record<string, string> = {
  pdf: '📄',
  csv: '📊',
  xlsx: '📊',
  txt: '📝',
  html: '🌐',
};

export function DocumentInventory() {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingDocument, setEditingDocument] = useState<{
    id: number;
    name: string;
    url: string | null;
  } | null>(null);
  const [expandedJurisdiction, setExpandedJurisdiction] = useState<string | null>(null);
  const [jurisdictionDocuments, setJurisdictionDocuments] = useState<Record<string, Document[]>>({});
  const [uploadingDocId, setUploadingDocId] = useState<number | null>(null);
  const [processingDocument, setProcessingDocument] = useState<{
    id: number;
    name: string;
  } | null>(null);
  const fileInputRefs = useRef<Record<number, HTMLInputElement>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDocumentsOverview();
      setOverview(data);
    } catch (err: any) {
      setError(err.message || 'Error al cargar inventario');
      console.error('Error loading document inventory:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      await syncRequiredDocuments();
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Error al sincronizar documentos');
    } finally {
      setSyncing(false);
    }
  };

  const loadJurisdictionDocuments = async (jurisdictionId: number | null, jurisdictionCode: string) => {
    try {
      // Para Nación (null), usar filtro directo de documentos
      if (jurisdictionId === null) {
        const data = await getRequiredDocuments({ jurisdiccion_id: undefined });
        setJurisdictionDocuments((prev) => ({
          ...prev,
          [jurisdictionCode]: data,
        }));
      } else {
        const data = await getJurisdictionDocuments(jurisdictionId);
        setJurisdictionDocuments((prev) => ({
          ...prev,
          [jurisdictionCode]: data.documents,
        }));
      }
    } catch (err: any) {
      console.error('Error loading jurisdiction documents:', err);
    }
  };

  const handleAccordionChange = async (value: string | null) => {
    setExpandedJurisdiction(value);
    
    if (value && overview) {
      const jurisdiction = overview.jurisdictions.find((j) => j.jurisdiction_code === value);
      if (jurisdiction && !jurisdictionDocuments[value]) {
        await loadJurisdictionDocuments(jurisdiction.jurisdiction_id, value);
      }
    }
  };

  const handleSaveUrl = async (documentId: number, newUrl: string) => {
    try {
      await updateDocumentUrl(documentId, newUrl);
      
      // Recargar datos
      await loadData();
      if (expandedJurisdiction) {
        const jurisdiction = overview?.jurisdictions.find((j) => j.jurisdiction_code === expandedJurisdiction);
        if (jurisdiction) {
          // Limpiar cache de documentos para forzar recarga
          setJurisdictionDocuments((prev) => {
            const newDocs = { ...prev };
            delete newDocs[expandedJurisdiction];
            return newDocs;
          });
          await loadJurisdictionDocuments(jurisdiction.jurisdiction_id, expandedJurisdiction);
        }
      }
    } catch (err: any) {
      console.error('Error saving URL:', err);
      throw err;
    }
  };

  const handleFileUpload = async (documentId: number, file: File) => {
    try {
      setUploadingDocId(documentId);
      
      await uploadDocumentFile(documentId, file);
      
      notifications.show({
        title: 'Archivo subido',
        message: 'El documento se subió correctamente',
        color: 'green',
      });
      
      // Recargar datos
      await loadData();
      if (expandedJurisdiction) {
        const jurisdiction = overview?.jurisdictions.find((j) => j.jurisdiction_code === expandedJurisdiction);
        if (jurisdiction) {
          setJurisdictionDocuments((prev) => {
            const newDocs = { ...prev };
            delete newDocs[expandedJurisdiction];
            return newDocs;
          });
          await loadJurisdictionDocuments(jurisdiction.jurisdiction_id, expandedJurisdiction);
        }
      }
    } catch (err: any) {
      notifications.show({
        title: 'Error',
        message: err.message || 'Error al subir archivo',
        color: 'red',
      });
    } finally {
      setUploadingDocId(null);
    }
  };

  const triggerFileInput = (documentId: number) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.csv,.xlsx,.xls,.txt';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleFileUpload(documentId, file);
      }
    };
    input.click();
  };

  const handleProcessingComplete = async () => {
    // Recargar datos después de procesar
    await loadData();
    if (expandedJurisdiction) {
      const jurisdiction = overview?.jurisdictions.find((j) => j.jurisdiction_code === expandedJurisdiction);
      if (jurisdiction) {
        setJurisdictionDocuments((prev) => {
          const newDocs = { ...prev };
          delete newDocs[expandedJurisdiction];
          return newDocs;
        });
        await loadJurisdictionDocuments(jurisdiction.jurisdiction_id, expandedJurisdiction);
      }
    }
  };

  if (loading) {
    return (
      <Center style={{ height: '400px' }}>
        <Stack align="center">
          <Loader size="xl" />
          <Text>Cargando inventario de documentos...</Text>
        </Stack>
      </Center>
    );
  }

  if (error) {
    return (
      <Alert icon={<IconAlertCircle size="1rem" />} title="Error" color="red">
        {error}
      </Alert>
    );
  }

  if (!overview || overview.jurisdictions.length === 0) {
    return (
      <Paper p="xl" withBorder>
        <Stack align="center" gap="md">
          <IconFileText size={48} color="gray" />
          <Title order={3}>Inventario no inicializado</Title>
          <Text c="dimmed" ta="center" maw={600}>
            El inventario de documentos requeridos aún no está cargado. Haz click en "Sincronizar" para cargar la
            configuración desde required_documents.json.
          </Text>
          <Button onClick={handleSync} loading={syncing} leftSection={<IconRefresh size="1rem" />}>
            Sincronizar Inventario
          </Button>
        </Stack>
      </Paper>
    );
  }

  return (
    <>
      {editingDocument && (
        <DocumentUrlEditor
          opened={!!editingDocument}
          onClose={() => setEditingDocument(null)}
          documentId={editingDocument.id}
          documentName={editingDocument.name}
          currentUrl={editingDocument.url}
          onSave={handleSaveUrl}
        />
      )}

      {/* Debug panel - temporal */}
      {processingDocument && (
        <div style={{
          position: 'fixed',
          top: 10,
          right: 10,
          background: 'rgba(255, 255, 0, 0.9)',
          padding: '15px',
          borderRadius: '8px',
          zIndex: 99999,
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          fontFamily: 'monospace',
          fontSize: '12px',
          maxWidth: '300px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>🐛 DEBUG MODAL</div>
          <div>🟢 Doc ID: {processingDocument.id}</div>
          <div>📄 Name: {processingDocument.name.substring(0, 30)}...</div>
          <div>✅ Opened: YES</div>
          <div style={{ marginTop: '8px', fontSize: '10px', opacity: 0.8 }}>
            Si no ves el modal, revisa z-index y overlay
          </div>
        </div>
      )}

      <DocumentProcessingModal
        opened={!!processingDocument}
        onClose={() => {
          console.log('🔴 Cerrando modal de procesamiento');
          setProcessingDocument(null);
        }}
        documentId={processingDocument?.id || 0}
        documentName={processingDocument?.name || ''}
        onComplete={handleProcessingComplete}
      />

      <Stack gap="lg">
      {/* Header con botón de sincronización */}
      <Group justify="space-between">
        <div>
          <Title order={2}>Inventario de Documentos Obligatorios</Title>
          <Text c="dimmed" size="sm">
            Tracking de documentos que cada jurisdicción debe publicar según la ley
          </Text>
        </div>
        <Button onClick={handleSync} loading={syncing} leftSection={<IconRefresh size="1rem" />} variant="light">
          Sincronizar
        </Button>
      </Group>

      <Alert icon={<IconInfoCircle size="1rem" />} variant="light" color="blue">
        Este inventario te permite ver exactamente qué documentos tienes descargados y procesados vs cuáles faltan
        para cumplir con las obligaciones legales. Cada documento puede estar en 4 estados: Faltante, Descargado,
        Procesado, o Error.
      </Alert>

      {/* Overview Cards */}
      <Grid>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <Card padding="md" withBorder>
            <Stack gap="xs">
              <Group>
                <ThemeIcon variant="light" color="blue">
                  <IconFileText size="1.2rem" />
                </ThemeIcon>
                <Text size="sm" fw={500}>
                  Total Documentos
                </Text>
              </Group>
              <Text size="2rem" fw={700}>
                {overview.total_documents}
              </Text>
              <Text size="xs" c="dimmed">
                Requeridos por ley
              </Text>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 3 }}>
          <Card padding="md" withBorder>
            <Stack gap="xs">
              <Group>
                <ThemeIcon variant="light" color="red">
                  <IconX size="1.2rem" />
                </ThemeIcon>
                <Text size="sm" fw={500}>
                  Faltantes
                </Text>
              </Group>
              <Text size="2rem" fw={700} c="red">
                {overview.total_missing}
              </Text>
              <Text size="xs" c="dimmed">
                Por descargar
              </Text>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 3 }}>
          <Card padding="md" withBorder>
            <Stack gap="xs">
              <Group>
                <ThemeIcon variant="light" color="green">
                  <IconCheck size="1.2rem" />
                </ThemeIcon>
                <Text size="sm" fw={500}>
                  Procesados
                </Text>
              </Group>
              <Text size="2rem" fw={700} c="green">
                {overview.total_processed}
              </Text>
              <Text size="xs" c="dimmed">
                Con RAG indexado
              </Text>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 3 }}>
          <Card padding="md" withBorder>
            <Stack gap="xs">
              <Group>
                <ThemeIcon variant="light" color="blue">
                  <IconDatabase size="1.2rem" />
                </ThemeIcon>
                <Text size="sm" fw={500}>
                  Cobertura
                </Text>
              </Group>
              <Text size="2rem" fw={700} c="blue">
                {overview.overall_coverage.toFixed(0)}%
              </Text>
              <Progress value={overview.overall_coverage} color="blue" size="sm" />
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>

      {/* Documents by Jurisdiction */}
      <Paper p="md" withBorder>
        <Title order={3} mb="md">
          Documentos por Jurisdicción
        </Title>

        <Accordion variant="separated" value={expandedJurisdiction} onChange={handleAccordionChange}>
          {overview.jurisdictions.map((jurisdiction) => (
            <Accordion.Item key={jurisdiction.jurisdiction_code} value={jurisdiction.jurisdiction_code}>
              <Accordion.Control>
                <Group justify="space-between">
                  <div>
                    <Text fw={600}>{jurisdiction.jurisdiction_name}</Text>
                    <Text size="xs" c="dimmed">
                      {jurisdiction.applicable_laws.join(' • ')}
                    </Text>
                  </div>
                  <Group gap="xs">
                    <Badge color="blue">{jurisdiction.total_documents} docs</Badge>
                    <Badge color="red">{jurisdiction.missing} faltantes</Badge>
                    <Badge color="green">{jurisdiction.processed} procesados</Badge>
                    <Badge color="gray">{jurisdiction.coverage_percentage.toFixed(0)}% cobertura</Badge>
                  </Group>
                </Group>
              </Accordion.Control>
              <Accordion.Panel>
                <Stack gap="md">
                  {/* Progress bar */}
                  <div>
                    <Group justify="space-between" mb={5}>
                      <Text size="sm" fw={500}>
                        Estado de Cobertura
                      </Text>
                      <Text size="sm" fw={600}>
                        {jurisdiction.coverage_percentage.toFixed(1)}%
                      </Text>
                    </Group>
                    <Progress
                      value={jurisdiction.coverage_percentage}
                      color={
                        jurisdiction.coverage_percentage >= 75
                          ? 'green'
                          : jurisdiction.coverage_percentage >= 50
                          ? 'yellow'
                          : 'red'
                      }
                      size="lg"
                    />
                  </div>

                  {/* Documents by type */}
                  <div>
                    <Text size="sm" fw={600} mb="xs">
                      Desglose por Tipo de Documento:
                    </Text>
                    <Grid>
                      {Object.entries(jurisdiction.by_type).map(([type, stats]) => (
                        <Grid.Col key={type} span={{ base: 12, sm: 6, md: 4 }}>
                          <Card padding="sm" withBorder>
                            <Stack gap="xs">
                              <Text size="xs" fw={500} tt="uppercase" c="dimmed">
                                {type.replace(/_/g, ' ')}
                              </Text>
                              <Group justify="space-between">
                                <Group gap={5}>
                                  <ThemeIcon size="xs" variant="light" color="green">
                                    <IconCheck size="0.6rem" />
                                  </ThemeIcon>
                                  <Text size="sm">{stats.processed}</Text>
                                </Group>
                                <Group gap={5}>
                                  <ThemeIcon size="xs" variant="light" color="red">
                                    <IconX size="0.6rem" />
                                  </ThemeIcon>
                                  <Text size="sm">{stats.missing}</Text>
                                </Group>
                                <Text size="xs" c="dimmed">
                                  / {stats.total}
                                </Text>
                              </Group>
                            </Stack>
                          </Card>
                        </Grid.Col>
                      ))}
                    </Grid>
                  </div>

                  {/* Lista de documentos */}
                  {jurisdictionDocuments[jurisdiction.jurisdiction_code] && (
                    <div>
                      <Text size="sm" fw={600} mb="xs">
                        Documentos Individuales:
                      </Text>
                      <Table striped highlightOnHover>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>Documento</Table.Th>
                            <Table.Th>Período</Table.Th>
                            <Table.Th>Estado</Table.Th>
                            <Table.Th>URL</Table.Th>
                            <Table.Th>Acciones</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {jurisdictionDocuments[jurisdiction.jurisdiction_code].map((doc) => (
                            <Table.Tr key={doc.id}>
                              <Table.Td>
                                <Text size="sm" fw={500}>
                                  {doc.document_name}
                                </Text>
                                <Text size="xs" c="dimmed">
                                  {FORMAT_ICONS[doc.expected_format]} {doc.expected_format.toUpperCase()}
                                </Text>
                              </Table.Td>
                              <Table.Td>
                                <Badge variant="light" size="sm">
                                  {doc.period || '-'}
                                </Badge>
                              </Table.Td>
                              <Table.Td>
                                <Group gap={5}>
                                  <ThemeIcon
                                    size="sm"
                                    variant="light"
                                    color={STATUS_CONFIG[doc.status as keyof typeof STATUS_CONFIG]?.color || 'gray'}
                                  >
                                    {(() => {
                                      const Icon =
                                        STATUS_CONFIG[doc.status as keyof typeof STATUS_CONFIG]?.icon || IconClock;
                                      return <Icon size="0.8rem" />;
                                    })()}
                                  </ThemeIcon>
                                  <Text size="xs">
                                    {STATUS_CONFIG[doc.status as keyof typeof STATUS_CONFIG]?.label || doc.status}
                                  </Text>
                                </Group>
                              </Table.Td>
                              <Table.Td>
                                {doc.expected_url ? (
                                  <Tooltip label={doc.expected_url}>
                                    <Anchor href={doc.expected_url} target="_blank" size="xs">
                                      <Group gap={5}>
                                        <IconLink size="0.8rem" />
                                        URL configurada
                                      </Group>
                                    </Anchor>
                                  </Tooltip>
                                ) : (
                                  <Text size="xs" c="dimmed" fs="italic">
                                    Sin URL
                                  </Text>
                                )}
                              </Table.Td>
                              <Table.Td>
                                <Group gap="xs">
                                  <Button
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconEdit size="0.8rem" />}
                                    onClick={() =>
                                      setEditingDocument({
                                        id: doc.id,
                                        name: doc.document_name,
                                        url: doc.expected_url,
                                      })
                                    }
                                  >
                                    URL
                                  </Button>
                                  <Button
                                    size="xs"
                                    variant="light"
                                    color="green"
                                    leftSection={<IconUpload size="0.8rem" />}
                                    onClick={() => triggerFileInput(doc.id)}
                                    loading={uploadingDocId === doc.id}
                                    disabled={uploadingDocId !== null}
                                  >
                                    Subir
                                  </Button>
                                  {doc.status === 'downloaded' && (
                                    <Button
                                      size="xs"
                                      variant="light"
                                      color="blue"
                                      leftSection={<IconPlayerPlay size="0.8rem" />}
                                      onClick={() => {
                                        console.log('🔵 Click Procesar:', doc.id, doc.document_name);
                                        setProcessingDocument({
                                          id: doc.id,
                                          name: doc.document_name,
                                        });
                                      }}
                                    >
                                      Procesar
                                    </Button>
                                  )}
                                </Group>
                              </Table.Td>
                            </Table.Tr>
                          ))}
                        </Table.Tbody>
                      </Table>
                    </div>
                  )}
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion>
      </Paper>
      </Stack>
    </>
  );
}
