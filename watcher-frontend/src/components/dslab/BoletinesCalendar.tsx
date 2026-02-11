import React from 'react';
import {
  Card,
  Group,
  Text,
  Badge,
  Stack,
  Grid,
  Tooltip,
  Box,
  RingProgress,
  Center,
  ActionIcon,
  Select
} from '@mantine/core';
import {
  IconCheck,
  IconDownload,
  IconAnalyze,
  IconCalendarEvent,
  IconChevronLeft,
  IconChevronRight
} from '@tabler/icons-react';

interface CalendarDay {
  date: string;
  is_weekend: boolean;
  sections_available: number[];
  sections_downloaded: number[];
  sections_analyzed: number[];
  total_size_mb: number;
}

interface CalendarStats {
  total_available: number;
  total_downloaded: number;
  total_size_mb: number;
  completion_percentage: number;
}

interface BoletinesCalendarProps {
  year: number;
  month: number;
  days: CalendarDay[];
  stats: CalendarStats;
  onDayClick?: (date: string) => void;
  onMonthChange?: (year: number, month: number) => void;
}

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

const BoletinesCalendar: React.FC<BoletinesCalendarProps> = ({
  year,
  month,
  days,
  stats,
  onDayClick,
  onMonthChange
}) => {
  
  const handlePreviousMonth = () => {
    if (month === 1) {
      onMonthChange?.(year - 1, 12);
    } else {
      onMonthChange?.(year, month - 1);
    }
  };
  
  const handleNextMonth = () => {
    if (month === 12) {
      onMonthChange?.(year + 1, 1);
    } else {
      onMonthChange?.(year, month + 1);
    }
  };
  
  const handleYearChange = (newYear: string | null) => {
    if (newYear) {
      onMonthChange?.(parseInt(newYear), month);
    }
  };
  
  const handleMonthSelect = (newMonth: string | null) => {
    if (newMonth) {
      onMonthChange?.(year, parseInt(newMonth));
    }
  };
  
  const getDayColor = (day: CalendarDay) => {
    if (day.is_weekend) return '#f8f9fa';
    
    const downloaded = day.sections_downloaded.length;
    const available = day.sections_available.length;
    
    if (downloaded === 0) return '#fff5f5'; // No descargado - rojo claro
    if (downloaded === available) return '#f0fdf4'; // Completo - verde claro
    return '#fff9db'; // Parcial - amarillo claro
  };
  
  const getDayBorderColor = (day: CalendarDay) => {
    if (day.is_weekend) return '#dee2e6';
    
    const downloaded = day.sections_downloaded.length;
    const available = day.sections_available.length;
    
    if (downloaded === 0) return '#ffc9c9';
    if (downloaded === available) return '#8ce99a';
    return '#ffe066';
  };
  
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.getDate();
  };
  
  const getDayStatus = (day: CalendarDay) => {
    if (day.is_weekend) return 'Fin de semana';
    
    const downloaded = day.sections_downloaded.length;
    const available = day.sections_available.length;
    const analyzed = day.sections_analyzed.length;
    
    if (downloaded === 0) return 'No descargado';
    if (analyzed === available) return 'Analizado completo';
    if (downloaded === available) return 'Descarga completa';
    return `${downloaded}/${available} secciones`;
  };
  
  return (
    <Stack gap="md">
      {/* Header con estadísticas y controles de navegación */}
      <Card withBorder p="md">
        <Group justify="space-between" align="center" mb="md">
          <Group gap="xs">
            <IconCalendarEvent size={24} />
            <Text size="xl" fw={600}>
              Calendario de Boletines
            </Text>
          </Group>
          
          <Group gap="xs">
            <ActionIcon 
              variant="light" 
              size="lg"
              onClick={handlePreviousMonth}
            >
              <IconChevronLeft size={20} />
            </ActionIcon>
            
            <Select
              value={month.toString()}
              onChange={handleMonthSelect}
              data={MONTH_NAMES.map((name, idx) => ({
                value: (idx + 1).toString(),
                label: name
              }))}
              w={150}
            />
            
            <Select
              value={year.toString()}
              onChange={handleYearChange}
              data={[
                { value: '2024', label: '2024' },
                { value: '2025', label: '2025' },
                { value: '2026', label: '2026' }
              ]}
              w={100}
            />
            
            <ActionIcon 
              variant="light" 
              size="lg"
              onClick={handleNextMonth}
            >
              <IconChevronRight size={20} />
            </ActionIcon>
          </Group>
        </Group>
        
        <Group justify="space-between" align="center">
          <Text size="lg" fw={500} c="dimmed">
            {MONTH_NAMES[month - 1]} {year}
          </Text>
          
          <Group gap="lg">
            <div>
              <Text size="xs" c="dimmed" ta="center">Completado</Text>
              <Center>
                <RingProgress
                  size={60}
                  thickness={6}
                  sections={[
                    { value: stats.completion_percentage, color: 'teal' }
                  ]}
                  label={
                    <Text size="xs" ta="center" fw={700}>
                      {stats.completion_percentage}%
                    </Text>
                  }
                />
              </Center>
            </div>
            
            <div>
              <Text size="xs" c="dimmed">Disponibles</Text>
              <Text size="lg" fw={600}>{stats.total_available}</Text>
            </div>
            
            <div>
              <Text size="xs" c="dimmed">Descargados</Text>
              <Text size="lg" fw={600} c="teal">{stats.total_downloaded}</Text>
            </div>
            
            <div>
              <Text size="xs" c="dimmed">Tamaño Total</Text>
              <Text size="lg" fw={600}>{stats.total_size_mb} MB</Text>
            </div>
          </Group>
        </Group>
      </Card>
      
      {/* Leyenda */}
      <Card withBorder p="sm">
        <Group gap="lg" justify="center">
          <Group gap="xs">
            <Box 
              w={16} 
              h={16} 
              style={{ 
                backgroundColor: '#f0fdf4', 
                border: '2px solid #8ce99a', 
                borderRadius: 4 
              }} 
            />
            <Text size="sm">Completo</Text>
          </Group>
          
          <Group gap="xs">
            <Box 
              w={16} 
              h={16} 
              style={{ 
                backgroundColor: '#fff9db', 
                border: '2px solid #ffe066', 
                borderRadius: 4 
              }} 
            />
            <Text size="sm">Parcial</Text>
          </Group>
          
          <Group gap="xs">
            <Box 
              w={16} 
              h={16} 
              style={{ 
                backgroundColor: '#fff5f5', 
                border: '2px solid #ffc9c9', 
                borderRadius: 4 
              }} 
            />
            <Text size="sm">No descargado</Text>
          </Group>
          
          <Group gap="xs">
            <Box 
              w={16} 
              h={16} 
              style={{ 
                backgroundColor: '#f8f9fa', 
                border: '2px solid #dee2e6', 
                borderRadius: 4 
              }} 
            />
            <Text size="sm">Fin de semana</Text>
          </Group>
        </Group>
      </Card>
      
      {/* Calendario */}
      <Card withBorder p="md">
        <Grid gutter="xs" columns={7}>
          {/* Headers de días */}
          {['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map((day) => (
            <Grid.Col span={1} key={day}>
              <Text size="sm" fw={600} ta="center" c="dimmed">
                {day}
              </Text>
            </Grid.Col>
          ))}
          
          {/* Días del mes */}
          {days.map((day, index) => {
            const date = new Date(day.date);
            const dayOfWeek = date.getDay();
            
            // Agregar espacios vacíos al inicio si es necesario
            if (index === 0 && dayOfWeek > 0) {
              return (
                <React.Fragment key={`empty-${index}`}>
                  {Array.from({ length: dayOfWeek }).map((_, i) => (
                    <Grid.Col span={1} key={`empty-${i}`} />
                  ))}
                  <Grid.Col span={1}>
                    <DayCell 
                      day={day} 
                      onClick={() => onDayClick?.(day.date)}
                    />
                  </Grid.Col>
                </React.Fragment>
              );
            }
            
            return (
              <Grid.Col span={1} key={day.date}>
                <DayCell 
                  day={day} 
                  onClick={() => onDayClick?.(day.date)}
                />
              </Grid.Col>
            );
          })}
        </Grid>
      </Card>
    </Stack>
  );
};

interface DayCellProps {
  day: CalendarDay;
  onClick?: () => void;
}

const DayCell: React.FC<DayCellProps> = ({ day, onClick }) => {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.getDate();
  };
  
  const getDayColor = (day: CalendarDay) => {
    if (day.is_weekend) return '#f8f9fa';
    
    const downloaded = day.sections_downloaded.length;
    const available = day.sections_available.length;
    
    if (downloaded === 0) return '#fff5f5';
    if (downloaded === available) return '#f0fdf4';
    return '#fff9db';
  };
  
  const getDayBorderColor = (day: CalendarDay) => {
    if (day.is_weekend) return '#dee2e6';
    
    const downloaded = day.sections_downloaded.length;
    const available = day.sections_available.length;
    
    if (downloaded === 0) return '#ffc9c9';
    if (downloaded === available) return '#8ce99a';
    return '#ffe066';
  };
  
  const getDayStatus = (day: CalendarDay) => {
    if (day.is_weekend) return 'Fin de semana';
    
    const downloaded = day.sections_downloaded.length;
    const available = day.sections_available.length;
    const analyzed = day.sections_analyzed.length;
    
    if (downloaded === 0) return 'No descargado';
    if (analyzed === available) return 'Analizado completo';
    if (downloaded === available) return 'Descarga completa';
    return `${downloaded}/${available} secciones`;
  };
  
  const tooltipContent = (
    <Stack gap={4}>
      <Text size="sm" fw={600}>{new Date(day.date).toLocaleDateString('es-AR')}</Text>
      <Text size="xs">{getDayStatus(day)}</Text>
      {day.sections_downloaded.length > 0 && (
        <>
          <Text size="xs">Secciones: {day.sections_downloaded.join(', ')}</Text>
          <Text size="xs">Tamaño: {day.total_size_mb.toFixed(2)} MB</Text>
        </>
      )}
    </Stack>
  );
  
  return (
    <Tooltip label={tooltipContent} withArrow position="top">
      <Box
        style={{
          backgroundColor: getDayColor(day),
          border: `2px solid ${getDayBorderColor(day)}`,
          borderRadius: 8,
          padding: '8px',
          minHeight: '60px',
          cursor: day.is_weekend ? 'default' : 'pointer',
          transition: 'all 0.2s ease'
        }}
        onClick={day.is_weekend ? undefined : onClick}
      >
        <Stack gap={2}>
          <Text size="sm" fw={600} ta="center">
            {formatDate(day.date)}
          </Text>
          
          {!day.is_weekend && (
            <Group gap={2} justify="center">
              {day.sections_analyzed.length > 0 && (
                <IconAnalyze size={12} color="#12b886" />
              )}
              {day.sections_downloaded.length > 0 && day.sections_analyzed.length === 0 && (
                <IconCheck size={12} color="#51cf66" />
              )}
              {day.sections_downloaded.length === 0 && (
                <IconDownload size={12} color="#fa5252" />
              )}
            </Group>
          )}
          
          {!day.is_weekend && day.sections_downloaded.length > 0 && (
            <Text size="10px" ta="center" c="dimmed">
              {day.sections_downloaded.length}/{day.sections_available.length}
            </Text>
          )}
        </Stack>
      </Box>
    </Tooltip>
  );
};

export default BoletinesCalendar;

