import { useState, useEffect } from 'react';
import {
  Stack,
  Timeline,
  Text,
  Group,
  Badge,
  Paper,
  Code,
  Anchor,
  ThemeIcon,
  Loader,
  Alert,
  Button,
  Collapse,
} from '@mantine/core';
import {
  IconExternalLink,
  IconDatabase,
  IconCheck,
  IconX,
  IconAlertTriangle,
  IconFileText,
  IconChevronDown,
  IconChevronUp,
  IconScale,
} from '@tabler/icons-react';
import { getCheckEvidence, getCheckResultById } from '../../services/api';

interface Evidence {
  id: number;
  source_url: string;
  source_type: string;
  snapshot_hash: string | null;
  captured_at: string;
  relevant_fragment: string | null;
  extracted_data: any;
  artifact_metadata: any;
  is_valid: boolean;
  validation_notes: string | null;
}

interface CheckResult {
  id: number;
  check_id: number;
  status: string;
  score: number | null;
  evaluation_date: string;
  summary: string;
  reason: string | null;
  remediation: string | null;
  check: {
    check_code: string;
    check_name: string;
    legal_basis: string;
  };
}

interface EvidenceTrailProps {
  resultId: number;
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  pdf: 'Documento PDF',
  html_table: 'Tabla HTML',
  api_response: 'Respuesta API',
  download: 'Archivo Descargado',
  manual: 'Carga Manual',
};

const STATUS_ICONS = {
  pass: IconCheck,
  warn: IconAlertTriangle,
  fail: IconX,
  unknown: IconX,
};

const STATUS_COLORS = {
  pass: 'green',
  warn: 'yellow',
  fail: 'red',
  unknown: 'gray',
};

export function EvidenceTrail({ resultId }: EvidenceTrailProps) {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [expandedEvidence, setExpandedEvidence] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [resultId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [resultData, evidenceData] = await Promise.all([
        getCheckResultById(resultId),
        getCheckEvidence(resultId),
      ]);

      setResult(resultData);
      setEvidences(evidenceData);
    } catch (err: any) {
      setError(err.message || 'Error al cargar evidencia');
      console.error('Error loading evidence:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loader />;
  }

  if (error) {
    return (
      <Alert icon={<IconAlertTriangle size="1rem" />} title="Error" color="red">
        {error}
      </Alert>
    );
  }

  if (!result) {
    return (
      <Alert icon={<IconAlertTriangle size="1rem" />} title="Sin datos">
        No se encontró información de este resultado
      </Alert>
    );
  }

  const StatusIcon = STATUS_ICONS[result.status as keyof typeof STATUS_ICONS];
  const statusColor = STATUS_COLORS[result.status as keyof typeof STATUS_COLORS];

  return (
    <Stack gap="md">
      {/* Header */}
      <Paper p="md" withBorder>
        <Stack gap="sm">
          <Group>
            <ThemeIcon size="lg" color={statusColor} variant="light">
              <StatusIcon size="1.2rem" />
            </ThemeIcon>
            <div style={{ flex: 1 }}>
              <Text fw={600}>{result.check.check_name}</Text>
              <Text size="sm" c="dimmed">
                {result.check.legal_basis}
              </Text>
            </div>
            <Badge size="lg" color={statusColor}>
              {result.status.toUpperCase()}
            </Badge>
          </Group>

          <Text size="sm">{result.summary}</Text>

          {result.reason && (
            <Text size="sm" c="dimmed">
              <strong>Razón:</strong> {result.reason}
            </Text>
          )}

          {result.remediation && (
            <Text size="sm" c="orange.7">
              <strong>Recomendación:</strong> {result.remediation}
            </Text>
          )}
        </Stack>
      </Paper>

      {/* Evidence Timeline */}
      <Paper p="md" withBorder>
        <Text fw={600} size="lg" mb="md">
          Trail de Evidencia
        </Text>

        {evidences.length === 0 ? (
          <Alert icon={<IconAlertTriangle size="1rem" />} variant="light">
            No hay evidencia registrada para esta evaluación. Esto puede indicar que el check fue ejecutado sin
            validadores específicos o que aún no se implementó la lógica de discovery.
          </Alert>
        ) : (
          <Timeline active={evidences.length} bulletSize={24}>
            {/* Step 1: Legal Obligation */}
            <Timeline.Item
              bullet={<IconScale size={12} />}
              title="Obligación Legal"
              bulletSize={30}
              color="blue"
            >
              <Text size="sm" c="dimmed" mb="xs">
                Base legal que establece la obligación
              </Text>
              <Badge variant="light">{result.check.legal_basis}</Badge>
            </Timeline.Item>

            {/* Step 2: Evidence Collection */}
            {evidences.map((evidence, index) => (
              <Timeline.Item
                key={evidence.id}
                bullet={<IconDatabase size={12} />}
                title={`Evidencia ${index + 1}: ${SOURCE_TYPE_LABELS[evidence.source_type] || evidence.source_type}`}
                bulletSize={30}
                color={evidence.is_valid ? 'teal' : 'red'}
              >
                <Stack gap="xs">
                  <Group gap="xs">
                    <Text size="sm" c="dimmed">
                      Capturada el {new Date(evidence.captured_at).toLocaleString()}
                    </Text>
                    {evidence.is_valid ? (
                      <Badge size="xs" color="green">
                        Válida
                      </Badge>
                    ) : (
                      <Badge size="xs" color="red">
                        Inválida
                      </Badge>
                    )}
                  </Group>

                  <Anchor href={evidence.source_url} target="_blank" size="sm">
                    <Group gap={5}>
                      <IconExternalLink size="0.9rem" />
                      {evidence.source_url}
                    </Group>
                  </Anchor>

                  {evidence.snapshot_hash && (
                    <Code block style={{ fontSize: '0.7rem' }}>
                      Hash: {evidence.snapshot_hash.substring(0, 16)}...
                    </Code>
                  )}

                  {evidence.relevant_fragment && (
                    <>
                      <Button
                        variant="subtle"
                        size="xs"
                        onClick={() => setExpandedEvidence(expandedEvidence === evidence.id ? null : evidence.id)}
                        rightSection={expandedEvidence === evidence.id ? <IconChevronUp size="1rem" /> : <IconChevronDown size="1rem" />}
                      >
                        Ver fragmento relevante
                      </Button>
                      <Collapse in={expandedEvidence === evidence.id}>
                        <Paper p="sm" withBorder bg="gray.0">
                          <Text size="xs" style={{ whiteSpace: 'pre-wrap' }}>
                            {evidence.relevant_fragment}
                          </Text>
                        </Paper>
                      </Collapse>
                    </>
                  )}

                  {evidence.extracted_data && (
                    <>
                      <Button
                        variant="subtle"
                        size="xs"
                        onClick={() => setExpandedEvidence(expandedEvidence === evidence.id * -1 ? null : evidence.id * -1)}
                        rightSection={expandedEvidence === evidence.id * -1 ? <IconChevronUp size="1rem" /> : <IconChevronDown size="1rem" />}
                      >
                        Ver datos extraídos
                      </Button>
                      <Collapse in={expandedEvidence === evidence.id * -1}>
                        <Code block style={{ fontSize: '0.7rem' }}>
                          {JSON.stringify(evidence.extracted_data, null, 2)}
                        </Code>
                      </Collapse>
                    </>
                  )}

                  {!evidence.is_valid && evidence.validation_notes && (
                    <Alert icon={<IconAlertTriangle size="1rem" />} color="red" size="sm">
                      {evidence.validation_notes}
                    </Alert>
                  )}
                </Stack>
              </Timeline.Item>
            ))}

            {/* Step 3: Validation Result */}
            <Timeline.Item
              bullet={<IconFileText size={12} />}
              title="Resultado de Validación"
              bulletSize={30}
              color={statusColor}
            >
              <Stack gap="xs">
                <Group>
                  <Badge color={statusColor}>{result.status.toUpperCase()}</Badge>
                  {result.score !== null && (
                    <Badge variant="light">Score: {result.score.toFixed(2)}</Badge>
                  )}
                </Group>
                <Text size="sm">{result.summary}</Text>
                <Text size="xs" c="dimmed">
                  Evaluado el {new Date(result.evaluation_date).toLocaleDateString()}
                </Text>
              </Stack>
            </Timeline.Item>
          </Timeline>
        )}
      </Paper>
    </Stack>
  );
}
