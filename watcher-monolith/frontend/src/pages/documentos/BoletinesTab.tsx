import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Group,
  Text,
  Badge,
  ActionIcon,
  Stack,
  Alert,
  Loader,
  Pagination,
  Tooltip
} from '@mantine/core';
import {
  IconFileText,
  IconAnalyze,
  IconAlertCircle,
  IconCheck,
  IconClock,
  IconX,
  IconEye
} from '@tabler/icons-react';
import { processBoletin } from '../../services/api';

const API_BASE_URL = 'http://localhost:8001';

interface BoletinDocument {
  id: number;
  filename: string;
  year: number;
  month: number;
  day: number;
  section: number;
  file_size_bytes: number;
  analysis_status: string;
  last_analyzed: string | null;
  created_at: string;
}

export function BoletinesTab() {
  const [documents, setDocuments] = useState<BoletinDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [processingDoc, setProcessingDoc] = useState<number | null>(null);
  const pageSize = 50;

  useEffect(() => {
    loadDocuments();
  }, [page]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError('');
      
      const skip = (page - 1) * pageSize;
      const response = await fetch(
        `${API_BASE_URL}/api/v1/dslab/documents?limit=${pageSize}&skip=${skip}&order=desc`
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar documentos');
      }
      
      const data = await response.json();
      setDocuments(data);
      
      // Obtener estadísticas para paginación
      const totalResponse = await fetch(`${API_BASE_URL}/api/v1/dslab/documents/stats`);
      if (totalResponse.ok) {
        const stats = await totalResponse.json();
        const total = stats.total_documents || data.length;
        setTotalDocuments(total);
        setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
      } else {
        setTotalDocuments(data.length);
        setTotalPages(1);
      }
    } catch (err) {
      setError('Error cargando documentos: ' + (err as Error).message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <IconCheck size={18} color="green" />;
      case 'processing':
        return <IconClock size={18} color="blue" />;
      case 'failed':
        return <IconX size={18} color="red" />;
      default:
        return <IconAlertCircle size={18} color="gray" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'green',
      processing: 'blue',
      failed: 'red',
      pending: 'gray',
    };
    return <Badge color={colors[status] || 'gray'}>{status}</Badge>;
  };

  const formatDate = (doc: BoletinDocument) => {
    return `${doc.day}/${doc.month}/${doc.year}`;
  };

  const formatSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const getSectionName = (section: number) => {
    const sections: Record<number, string> = {
      1: 'Compras y Contrataciones',
      2: 'Obras Públicas',
      3: 'Subsidios y Transferencias',
      4: 'Designaciones y Decretos',
      5: 'Notificaciones Judiciales'
    };
    return sections[section] || `Sección ${section}`;
  };

  const handleViewDocument = (doc: BoletinDocument) => {
    window.open(
      `${API_BASE_URL}/api/v1/boletines/documents/${doc.filename}/pdf`,
      '_blank',
      'noopener,noreferrer'
    );
  };

  const handleAnalyzeDocument = async (doc: BoletinDocument) => {
    try {
      setProcessingDoc(doc.id);
      await processBoletin(doc.filename);
      await loadDocuments();
    } catch (err) {
      setError(`Error analizando ${doc.filename}: ${(err as Error).message}`);
      console.error(err);
    } finally {
      setProcessingDoc(null);
    }
  };

  if (loading && documents.length === 0) {
    return (
      <Stack align="center" py="xl">
        <Loader size="lg" />
        <Text>Cargando boletines...</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          {documents.length > 0
            ? `Mostrando ${documents.length} de ${totalDocuments || '...'} documentos`
            : 'No hay documentos'}
        </Text>
        <Group>
          <Button
            onClick={loadDocuments}
            variant="light"
            loading={loading}
            leftSection={<IconFileText size={16} />}
          >
            Actualizar
          </Button>
        </Group>
      </Group>

      <Table striped highlightOnHover>
        <thead>
          <tr>
            <th>Estado</th>
            <th>Archivo</th>
            <th>Fecha</th>
            <th>Sección</th>
            <th>Tamaño</th>
            <th>Última Análisis</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr key={doc.id}>
              <td>
                <Group gap="xs">
                  {getStatusIcon(doc.analysis_status)}
                  {getStatusBadge(doc.analysis_status)}
                </Group>
              </td>
              <td>
                <Text size="sm" fw={500}>{doc.filename}</Text>
              </td>
              <td>
                <Text size="sm">{formatDate(doc)}</Text>
              </td>
              <td>
                <Badge variant="light" size="sm">{getSectionName(doc.section)}</Badge>
              </td>
              <td>
                <Text size="xs" c="dimmed">{formatSize(doc.file_size_bytes)}</Text>
              </td>
              <td>
                <Text size="xs" c="dimmed">
                  {doc.last_analyzed ? new Date(doc.last_analyzed).toLocaleDateString('es-AR') : 'Nunca'}
                </Text>
              </td>
              <td>
                <Group gap={4}>
                  <Tooltip label="Ver documento">
                    <ActionIcon
                      color="blue"
                      variant="light"
                      size="sm"
                      onClick={() => handleViewDocument(doc)}
                    >
                      <IconEye size={14} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Analizar con Agentes IA">
                    <ActionIcon
                      color="green"
                      variant="light"
                      size="sm"
                      disabled={doc.analysis_status === 'processing' || processingDoc === doc.id}
                      loading={processingDoc === doc.id}
                      onClick={() => handleAnalyzeDocument(doc)}
                    >
                      <IconAnalyze size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      {documents.length === 0 && (
        <Stack align="center" py="xl">
          <IconFileText size={48} style={{ opacity: 0.3 }} />
          <Text c="dimmed">No hay boletines descargados</Text>
          <Text size="sm" c="dimmed">Ve a "Configuración" → "Descarga de Boletines" para descargar</Text>
        </Stack>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Group justify="center" mt="md">
          <Pagination
            total={totalPages}
            value={page}
            onChange={setPage}
            size="sm"
          />
        </Group>
      )}
    </Stack>
  );
}
