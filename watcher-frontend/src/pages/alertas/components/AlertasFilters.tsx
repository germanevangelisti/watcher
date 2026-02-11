import { Select, Stack, TextInput } from '@mantine/core';
import { FilterPanel } from '../../../components/shared/FilterPanel';

interface AlertasFiltersProps {
  filters: {
    nivel_severidad?: string;
    tipo_alerta?: string;
    organismo?: string;
    estado?: string;
  };
  onFilterChange: (key: string, value: string | undefined) => void;
  onReset: () => void;
  organismos: string[];
  tipos: string[];
}

export function AlertasFilters({ 
  filters, 
  onFilterChange, 
  onReset,
  organismos,
  tipos
}: AlertasFiltersProps) {
  return (
    <FilterPanel onReset={onReset} title="Filtrar Alertas">
      <Stack gap="md">
        <Select
          label="Severidad"
          placeholder="Todas"
          value={filters.nivel_severidad || ''}
          onChange={(value) => onFilterChange('nivel_severidad', value || undefined)}
          data={[
            { value: '', label: 'Todas' },
            { value: 'CRITICA', label: 'Crítica' },
            { value: 'ALTA', label: 'Alta' },
            { value: 'MEDIA', label: 'Media' },
            { value: 'BAJA', label: 'Baja' },
          ]}
          clearable
        />

        <Select
          label="Tipo de Alerta"
          placeholder="Todos"
          value={filters.tipo_alerta || ''}
          onChange={(value) => onFilterChange('tipo_alerta', value || undefined)}
          data={[
            { value: '', label: 'Todos' },
            ...tipos.map(t => ({ value: t, label: t }))
          ]}
          searchable
          clearable
        />

        <Select
          label="Organismo"
          placeholder="Todos"
          value={filters.organismo || ''}
          onChange={(value) => onFilterChange('organismo', value || undefined)}
          data={[
            { value: '', label: 'Todos' },
            ...organismos.map(o => ({ value: o, label: o }))
          ]}
          searchable
          clearable
        />

        <Select
          label="Estado"
          placeholder="Todos"
          value={filters.estado || ''}
          onChange={(value) => onFilterChange('estado', value || undefined)}
          data={[
            { value: '', label: 'Todos' },
            { value: 'activa', label: 'Activa' },
            { value: 'revisada', label: 'Revisada' },
            { value: 'resuelta', label: 'Resuelta' },
            { value: 'falsa', label: 'Falsa' },
          ]}
          clearable
        />
      </Stack>
    </FilterPanel>
  );
}

