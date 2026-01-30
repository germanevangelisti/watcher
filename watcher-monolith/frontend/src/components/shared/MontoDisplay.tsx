import { Text } from '@mantine/core';

interface MontoDisplayProps {
  monto: number | null | undefined;
  currency?: string;
  size?: string;
  fw?: number;
  c?: string;
}

export function MontoDisplay({ monto, currency = '$', size, fw, c }: MontoDisplayProps) {
  if (monto === null || monto === undefined) {
    return <Text c="dimmed" size={size} fw={fw}>No especificado</Text>;
  }

  const formatted = new Intl.NumberFormat('es-AR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(monto);

  return (
    <Text fw={fw || 600} size={size} c={c}>
      {currency}{formatted}
    </Text>
  );
}

