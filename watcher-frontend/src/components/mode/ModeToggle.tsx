import { Switch, Group, Text } from '@mantine/core';
import { IconUser, IconShield } from '@tabler/icons-react';
import { useUserMode } from '../../contexts/UserModeContext';

export function ModeToggle() {
  const { mode, toggleMode } = useUserMode();

  return (
    <Group gap="xs">
      <IconUser size="1.2rem" />
      <Switch
        checked={mode === 'auditor'}
        onChange={toggleMode}
        onLabel="Auditor"
        offLabel="Ciudadano"
        size="md"
      />
      <IconShield size="1.2rem" />
    </Group>
  );
}

