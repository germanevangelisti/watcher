import { Select, Stack, NumberInput } from '@mantine/core';
import { FilterPanel } from '../../../components/shared/FilterPanel';

interface PresupuestoFiltersProps {
  filters: {
    ejercicio?: number;
    organismo?: string;
  };
  onFilterChange: (key: string, value: number | string | undefined) => void;
  onReset: () => void;
  organismos: string[];
}

export function PresupuestoFilters({ 
  filters, 
  onFilterChange, 
  onReset,
  organismos
}: PresupuestoFiltersProps) {
  return (
    <FilterPanel onReset={onReset} title="Filtrar Programas">
      <Stack gap="md">
        <NumberInput
          label="Ejercicio"
          placeholder="2025"
          value={filters.ejercicio || ''}
          onChange={(value) => onFilterChange('ejercicio', value as number | undefined)}
          min={2020}
          max={2030}
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
      </Stack>
    </FilterPanel>
  );
}

