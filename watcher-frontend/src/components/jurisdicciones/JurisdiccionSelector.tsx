/**
 * JurisdiccionSelector - Selector de Jurisdicciones con Jerarquía
 * 
 * Permite filtrar contenido por:
 * - Provincia de Córdoba (todas las fuentes)
 * - Ciudad de Córdoba (capital)
 * - Municipalidades específicas
 * - Comunas
 */

import React, { useState, useEffect } from 'react';
import {
  Select,
  Group,
  Badge,
  Text,
  Stack,
  Loader,
  Box,
  Paper,
  Divider
} from '@mantine/core';
import {
  IconMapPin,
  IconBuilding,
  IconHome,
  IconUsers
} from '@tabler/icons-react';

interface Jurisdiccion {
  id: number;
  nombre: string;
  tipo: string;
  poblacion?: number;
  departamento?: string;
}

interface JurisdiccionStats {
  jurisdiccion_id: number;
  nombre: string;
  tipo: string;
  total_boletines: number;
  total_menciones: number;
}

interface JurisdiccionSelectorProps {
  value?: number | null;
  onChange: (jurisdiccionId: number | null) => void;
  showStats?: boolean;
  placeholder?: string;
}

export const JurisdiccionSelector: React.FC<JurisdiccionSelectorProps> = ({
  value,
  onChange,
  showStats = false,
  placeholder = "Todas las jurisdicciones"
}) => {
  const [jurisdicciones, setJurisdicciones] = useState<Jurisdiccion[]>([]);
  const [stats, setStats] = useState<JurisdiccionStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch jurisdicciones
      const jurisdiccionesRes = await fetch('/api/v1/jurisdicciones/');
      if (!jurisdiccionesRes.ok) throw new Error('Error cargando jurisdicciones');
      const jurisdiccionesData = await jurisdiccionesRes.json();
      setJurisdicciones(jurisdiccionesData);
      
      // Fetch stats si se requieren
      if (showStats) {
        const statsRes = await fetch('/api/v1/jurisdicciones/stats?limite=100');
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        }
      }
      
      setError(null);
    } catch (err) {
      console.error('Error fetching jurisdicciones:', err);
      setError('Error cargando jurisdicciones');
    } finally {
      setLoading(false);
    }
  };

  const getIconByTipo = (tipo: string) => {
    switch (tipo) {
      case 'provincia':
        return <IconMapPin size={16} />;
      case 'capital':
        return <IconBuilding size={16} />;
      case 'municipalidad':
        return <IconHome size={16} />;
      case 'comuna':
        return <IconUsers size={16} />;
      default:
        return <IconMapPin size={16} />;
    }
  };

  const getColorByTipo = (tipo: string): string => {
    switch (tipo) {
      case 'provincia':
        return 'blue';
      case 'capital':
        return 'red';
      case 'municipalidad':
        return 'green';
      case 'comuna':
        return 'yellow';
      default:
        return 'gray';
    }
  };

  const getStatsByJurisdiccion = (jurisdiccionId: number): JurisdiccionStats | undefined => {
    return stats.find(s => s.jurisdiccion_id === jurisdiccionId);
  };

  // Early returns for loading/error states BEFORE processing data
  if (loading) {
    return (
      <Group>
        <Loader size="sm" />
        <Text size="sm" c="dimmed">Cargando jurisdicciones...</Text>
      </Group>
    );
  }

  if (error) {
    return (
      <Text size="sm" c="red">{error}</Text>
    );
  }

  // Safety check: ensure we have valid jurisdicciones array
  if (!Array.isArray(jurisdicciones) || jurisdicciones.length === 0) {
    return (
      <Select
        data={[{ value: '', label: placeholder }]}
        value=""
        disabled
        placeholder={placeholder}
      />
    );
  }

  // Agrupar jurisdicciones por tipo
  const jurisdiccionesPorTipo = jurisdicciones.reduce((acc, j) => {
    if (!acc[j.tipo]) acc[j.tipo] = [];
    acc[j.tipo].push(j);
    return acc;
  }, {} as Record<string, Jurisdiccion[]>);

  // Ordenar los tipos en un orden específico
  const tiposOrdenados = ['provincia', 'capital', 'municipalidad', 'comuna'];
  
  const labelsPorTipo: Record<string, string> = {
    'provincia': 'Provincia',
    'capital': 'Ciudad Capital',
    'municipalidad': 'Municipalidades',
    'comuna': 'Comunas'
  };

  // Preparar datos para el Select - Simple structure without groups for now
  const selectData: any[] = [];
  
  // Add the "all" option
  selectData.push({ 
    value: '', 
    label: placeholder 
  });
  
  // Add all jurisdictions without grouping to avoid the parsing issue
  jurisdicciones.forEach(j => {
    if (j && j.id && j.nombre) {
      selectData.push({
        value: j.id.toString(),
        label: j.nombre
      });
    }
  });

  return (
    <Select
      data={selectData}
      value={value?.toString() || ''}
      onChange={(val) => onChange(val ? parseInt(val) : null)}
      placeholder={placeholder}
      searchable
      clearable
      styles={{
        dropdown: {
          maxHeight: '400px',
          overflowY: 'auto'
        }
      }}
    />
  );
};

/**
 * JurisdiccionBadge - Badge para mostrar información de jurisdicción
 */
interface JurisdiccionBadgeProps {
  tipo: string;
  nombre: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  withIcon?: boolean;
}

export const JurisdiccionBadge: React.FC<JurisdiccionBadgeProps> = ({
  tipo,
  nombre,
  size = 'sm',
  withIcon = true
}) => {
  const getIconByTipo = (tipo: string) => {
    const iconSize = size === 'xs' ? 12 : size === 'sm' ? 14 : 16;
    switch (tipo) {
      case 'provincia':
        return <IconMapPin size={iconSize} />;
      case 'capital':
        return <IconBuilding size={iconSize} />;
      case 'municipalidad':
        return <IconHome size={iconSize} />;
      case 'comuna':
        return <IconUsers size={iconSize} />;
      default:
        return <IconMapPin size={iconSize} />;
    }
  };

  const getColorByTipo = (tipo: string): string => {
    switch (tipo) {
      case 'provincia':
        return 'blue';
      case 'capital':
        return 'red';
      case 'municipalidad':
        return 'green';
      case 'comuna':
        return 'yellow';
      default:
        return 'gray';
    }
  };

  return (
    <Badge
      size={size}
      color={getColorByTipo(tipo)}
      variant="light"
      leftSection={withIcon ? getIconByTipo(tipo) : undefined}
    >
      {nombre}
    </Badge>
  );
};

/**
 * JurisdiccionStatsCard - Tarjeta con estadísticas de jurisdicción
 */
interface JurisdiccionStatsCardProps {
  jurisdiccionId: number;
  onClick?: () => void;
}

export const JurisdiccionStatsCard: React.FC<JurisdiccionStatsCardProps> = ({
  jurisdiccionId,
  onClick
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [jurisdiccionId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/jurisdicciones/${jurisdiccionId}`);
      if (!res.ok) throw new Error('Error cargando datos');
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Paper p="md" withBorder>
        <Loader size="sm" />
      </Paper>
    );
  }

  if (!data) return null;

  const getIconByTipo = (tipo: string) => {
    switch (tipo) {
      case 'provincia':
        return <IconMapPin size={24} />;
      case 'capital':
        return <IconBuilding size={24} />;
      case 'municipalidad':
        return <IconHome size={24} />;
      case 'comuna':
        return <IconUsers size={24} />;
      default:
        return <IconMapPin size={24} />;
    }
  };

  return (
    <Paper
      p="md"
      withBorder
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      onClick={onClick}
    >
      <Stack gap="sm">
        <Group justify="space-between">
          <Group>
            {getIconByTipo(data.tipo)}
            <div>
              <Text fw={600} size="lg">{data.nombre}</Text>
              {data.departamento && (
                <Text size="sm" c="dimmed">
                  Departamento {data.departamento}
                </Text>
              )}
            </div>
          </Group>
          <JurisdiccionBadge tipo={data.tipo} nombre={data.tipo} withIcon={false} />
        </Group>

        <Divider />

        <Group grow>
          <Box>
            <Text size="xs" c="dimmed">Boletines</Text>
            <Text size="xl" fw={700} c="blue">
              {data.total_boletines || 0}
            </Text>
          </Box>
          
          <Box>
            <Text size="xs" c="dimmed">Menciones</Text>
            <Text size="xl" fw={700} c="green">
              {data.total_menciones || 0}
            </Text>
          </Box>
          
          {data.poblacion && (
            <Box>
              <Text size="xs" c="dimmed">Población</Text>
              <Text size="lg" fw={600}>
                {data.poblacion.toLocaleString()}
              </Text>
            </Box>
          )}
        </Group>

        {data.ultima_actividad && (
          <>
            <Divider />
            <Text size="xs" c="dimmed">
              Última actividad: {new Date(data.ultima_actividad).toLocaleDateString()}
            </Text>
          </>
        )}
      </Stack>
    </Paper>
  );
};

export default JurisdiccionSelector;
