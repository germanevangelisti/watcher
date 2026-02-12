import { Select, Stack } from '@mantine/core';
import { FilterPanel } from '../../../components/shared/FilterPanel';

interface ActosFiltersProps {
  filters: {
    tipo_acto?: string;
    organismo?: string;
    nivel_riesgo?: string;
  };
  onFilterChange: (key: string, value: string | undefined) => void;
  onReset: () => void;
  organismos: string[];
  tipos: string[];
}

export function ActosFilters({ 
  filters, 
  onFilterChange, 
  onReset,
  organismos,
  tipos
}: ActosFiltersProps) {
  return (
    <FilterPanel onReset={onReset} title="Filtrar Actos">
      <Stack gap="md">
        <Select
          label="Tipo de Acto"
          placeholder="Todos"
          value={filters.tipo_acto || ''}
          onChange={(value) => onFilterChange('tipo_acto', value || undefined)}
          data={[
            { value: '', label: 'Todos' },
            ...tipos.map(t => ({ value: t, label: t }))
          ]}
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
          label="Nivel de Riesgo"
          placeholder="Todos"
          value={filters.nivel_riesgo || ''}
          onChange={(value) => onFilterChange('nivel_riesgo', value || undefined)}
          data={[
            { value: '', label: 'Todos' },
            { value: 'ALTO', label: 'Alto' },
            { value: 'MEDIO', label: 'Medio' },
            { value: 'BAJO', label: 'Bajo' },
          ]}
          clearable
        />
      </Stack>
    </FilterPanel>
  );
}

