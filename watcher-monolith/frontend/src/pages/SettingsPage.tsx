import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Title,
  Tabs,
  Stack,
  Text,
  Paper,
  Group,
  TextInput,
  Button,
  Alert,
  Badge
} from '@mantine/core';
import {
  IconSettings,
  IconRobot,
  IconKey,
  IconDownload,
  IconCalendar,
  IconChartBar,
  IconInfoCircle
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import BoletinesCalendar from '../components/dslab/BoletinesCalendar';
import DownloadManager from '../components/dslab/DownloadManager';
import DSLabDashboard from '../components/dslab/DSLabDashboard';
import YearOverview from '../components/dslab/YearOverview';

interface CalendarData {
  year: number;
  month: number;
  days: any[];
  stats: {
    total_available: number;
    total_downloaded: number;
    total_size_mb: number;
    completion_percentage: number;
  };
}

interface DSLabStats {
  total_files: number;
  total_size_mb: number;
  by_month: Record<string, number>;
  by_section: Record<number, number>;
}

const API_BASE_URL = 'http://localhost:8001';

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<string | null>('downloader');
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [stats, setStats] = useState<DSLabStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [yearOverview, setYearOverview] = useState<any>(null);

  const loadCalendarData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/api/v1/downloader/calendar?year=${selectedYear}&month=${selectedMonth}`
      );

      if (!response.ok) {
        throw new Error('Error cargando calendario');
      }

      const data = await response.json();
      setCalendarData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
      console.error('Error loading calendar:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedYear, selectedMonth]);

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
  
  const loadYearOverview = useCallback(async () => {
    try {
      const monthsData = [];
      for (let month = 1; month <= 12; month++) {
        const response = await fetch(
          `${API_BASE_URL}/api/v1/downloader/calendar?year=${selectedYear}&month=${month}`
        );
        if (response.ok) {
          const data = await response.json();
          monthsData.push(data);
        }
      }
      setYearOverview({ months: monthsData, year: selectedYear });
    } catch (err) {
      console.error('Error loading year overview:', err);
    }
  }, [selectedYear]);

  useEffect(() => {
    if (activeTab === 'calendar') {
      loadCalendarData();
    } else if (activeTab === 'downloader') {
      loadStats();
    } else if (activeTab === 'overview') {
      loadYearOverview();
    }
  }, [activeTab, loadCalendarData, loadStats, loadYearOverview]);

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>⚙️ Configuración del Sistema</Title>
          <Text c="dimmed">Gestiona la configuración de agentes, descarga de boletines y API keys</Text>
        </div>

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="downloader" leftSection={<IconDownload size={16} />}>
              Descarga de Boletines
            </Tabs.Tab>
            <Tabs.Tab value="calendar" leftSection={<IconCalendar size={16} />}>
              Calendario
            </Tabs.Tab>
            <Tabs.Tab value="overview" leftSection={<IconChartBar size={16} />}>
              Vista Anual
            </Tabs.Tab>
            <Tabs.Tab value="agents" leftSection={<IconRobot size={16} />}>
              Agentes IA
            </Tabs.Tab>
            <Tabs.Tab value="api" leftSection={<IconKey size={16} />}>
              API Keys
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="downloader" pt="xl">
            <Stack gap="md">
              <Alert icon={<IconInfoCircle size={16} />} color="blue">
                Gestiona la descarga automática de boletines oficiales
              </Alert>
              {stats && <DSLabDashboard stats={stats} onRefresh={loadStats} />}
              <DownloadManager />
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="calendar" pt="xl">
            <Stack gap="md">
              <Group>
                <TextInput
                  label="Año"
                  type="number"
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(parseInt(e.target.value) || new Date().getFullYear())}
                  style={{ width: 120 }}
                />
                <TextInput
                  label="Mes"
                  type="number"
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(parseInt(e.target.value) || 1)}
                  min={1}
                  max={12}
                  style={{ width: 100 }}
                />
                <Button
                  onClick={loadCalendarData}
                  loading={loading}
                  style={{ marginTop: 25 }}
                >
                  Cargar
                </Button>
              </Group>

              {calendarData && (
                <BoletinesCalendar
                  calendarData={calendarData}
                  onRefresh={loadCalendarData}
                />
              )}
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="overview" pt="xl">
            {yearOverview ? (
              <YearOverview
                year={yearOverview.year}
                months={yearOverview.months || []}
                onMonthClick={(year, month) => {
                  setSelectedYear(year);
                  setSelectedMonth(month);
                  setActiveTab('calendar');
                }}
              />
            ) : (
              <Stack align="center" py="xl">
                <Text c="dimmed">Cargando vista anual...</Text>
              </Stack>
            )}
          </Tabs.Panel>

          <Tabs.Panel value="agents" pt="xl">
            <Stack gap="md">
              <Alert icon={<IconInfoCircle size={16} />} color="blue">
                Configuración de agentes IA (próximamente)
              </Alert>
              
              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text fw={500}>🤖 Document Intelligence Agent</Text>
                    <Badge color="green">Activo</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    Extracción inteligente de información de documentos
                  </Text>
                </Stack>
              </Paper>

              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text fw={500}>🔍 Anomaly Detection Agent</Text>
                    <Badge color="green">Activo</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    Detección de anomalías y red flags
                  </Text>
                </Stack>
              </Paper>

              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Text fw={500}>💡 Insight & Reporting Agent</Text>
                    <Badge color="green">Activo</Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    Generación de insights y reportes inteligentes
                  </Text>
                </Stack>
              </Paper>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="api" pt="xl">
            <Stack gap="md">
              <Alert icon={<IconInfoCircle size={16} />} color="blue">
                Gestiona las API keys para servicios externos
              </Alert>

              <Paper p="md" withBorder>
                <Stack gap="sm">
                  <Text fw={500}>OpenAI API Key</Text>
                  <TextInput
                    placeholder="sk-..."
                    type="password"
                    description="Necesaria para funciones de IA avanzadas"
                  />
                  <Text size="xs" c="dimmed">
                    ℹ️ Esta key se configura en el archivo .env del backend
                  </Text>
                </Stack>
              </Paper>
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}

