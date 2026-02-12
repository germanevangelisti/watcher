import { useState, useEffect, useCallback } from 'react';
import { Container, Title, Text, Stack, Alert } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';
import DownloadManager from '../components/dslab/DownloadManager';
import DSLabDashboard from '../components/dslab/DSLabDashboard';

const API_BASE_URL = 'http://localhost:8001';

interface DSLabStats {
  total_files: number;
  total_size_mb: number;
  by_month: Record<string, number>;
  by_section: Record<number, number>;
}

export function DownloaderPage() {
  const [stats, setStats] = useState<DSLabStats | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/downloader/download/summary`);

      if (!response.ok) {
        throw new Error('Error cargando estadísticas');
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>📥 Descarga Manual</Title>
          <Text c="dimmed">
            Descarga boletines específicos por rango de fechas de forma manual
          </Text>
        </div>

        <Alert icon={<IconInfoCircle size={16} />} color="blue">
          Descarga manual de boletines específicos por rango de fechas
        </Alert>

        {stats && <DSLabDashboard stats={stats} onRefresh={loadStats} />}
        <DownloadManager />
      </Stack>
    </Container>
  );
}
