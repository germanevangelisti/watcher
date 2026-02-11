import { useState } from 'react';
import { Modal, TextInput, Button, Group, Stack, Text, Alert } from '@mantine/core';
import { IconExternalLink, IconAlertCircle, IconCheck } from '@tabler/icons-react';

interface DocumentUrlEditorProps {
  opened: boolean;
  onClose: () => void;
  documentId: number;
  documentName: string;
  currentUrl: string | null;
  onSave: (documentId: number, newUrl: string) => Promise<void>;
}

export function DocumentUrlEditor({
  opened,
  onClose,
  documentId,
  documentName,
  currentUrl,
  onSave,
}: DocumentUrlEditorProps) {
  const [url, setUrl] = useState(currentUrl || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(false);

      // Validar URL básica
      if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
        setError('La URL debe comenzar con http:// o https://');
        return;
      }

      await onSave(documentId, url);
      setSuccess(true);

      // Cerrar modal después de 1 segundo
      setTimeout(() => {
        onClose();
        setSuccess(false);
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Error al guardar URL');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setUrl(currentUrl || '');
    setError(null);
    setSuccess(false);
    onClose();
  };

  return (
    <Modal opened={opened} onClose={handleClose} title="Editar URL del Documento" size="lg">
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Especifica la URL donde se publica este documento en el portal oficial del gobierno.
        </Text>

        <TextInput
          label="Nombre del Documento"
          value={documentName}
          disabled
          styles={{ input: { fontWeight: 500 } }}
        />

        <TextInput
          label="URL del Documento"
          placeholder="https://www.cba.gov.ar/presupuesto/2025.pdf"
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
          leftSection={<IconExternalLink size="1rem" />}
          description="El agente verificará periódicamente si el documento está disponible en esta URL"
          error={error}
        />

        {success && (
          <Alert icon={<IconCheck size="1rem" />} title="¡Guardado!" color="green">
            La URL se actualizó correctamente. El documento será monitoreado automáticamente.
          </Alert>
        )}

        {error && (
          <Alert icon={<IconAlertCircle size="1rem" />} title="Error" color="red">
            {error}
          </Alert>
        )}

        <Group justify="flex-end" mt="md">
          <Button variant="subtle" onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={handleSave} loading={loading}>
            Guardar URL
          </Button>
        </Group>

        <Alert variant="light" color="blue" icon={<IconAlertCircle size="1rem" />}>
          <Text size="xs">
            <strong>Tip:</strong> Una vez que agregues la URL, el sistema podrá:
            <ul style={{ marginTop: 5, marginBottom: 0 }}>
              <li>Detectar automáticamente cuando el documento se publica</li>
              <li>Descargarlo y procesarlo con RAG</li>
              <li>Alertarte si falta o se actualiza</li>
            </ul>
          </Text>
        </Alert>
      </Stack>
    </Modal>
  );
}
