import { useState, useEffect, useCallback } from 'react';
import { Container, Title, Text, Stack, Group, TextInput, Button } from '@mantine/core';
import BoletinesCalendar from '../components/dslab/BoletinesCalendar';

const API_BASE_URL = 'http://localhost:8001';

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

export function CalendarPage() {
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

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

  useEffect(() => {
    loadCalendarData();
  }, [loadCalendarData]);

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>📅 Calendario de Boletines</Title>
          <Text c="dimmed">
            Vista mensual de boletines disponibles y descargados
          </Text>
        </div>

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
            year={calendarData.year}
            month={calendarData.month}
            days={calendarData.days}
            stats={calendarData.stats}
            onMonthChange={(year, month) => {
              setSelectedYear(year);
              setSelectedMonth(month);
            }}
          />
        )}
      </Stack>
    </Container>
  );
}
