import { Box, NavLink, Divider } from '@mantine/core';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  IconHome,
  IconRobot,
  IconHistory,
  IconAlertTriangle,
  IconFileText,
  IconCash,
  IconSettings
} from '@tabler/icons-react';

export function MainNavbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const mainLinks = [
    { icon: IconHome, label: 'Dashboard', path: '/' },
    { icon: IconRobot, label: 'Agentes IA', path: '/agents' },
    { icon: IconHistory, label: 'Historial', path: '/history' },
  ];

  const dataLinks = [
    { icon: IconAlertTriangle, label: 'Alertas', path: '/alertas' },
    { icon: IconFileText, label: 'Documentos', path: '/documentos' },
    { icon: IconCash, label: 'Presupuesto', path: '/presupuesto' },
  ];

  const configLinks = [
    { icon: IconSettings, label: 'Configuración', path: '/settings' },
  ];

  return (
    <Box p="xs">
      {/* Main Links */}
      {mainLinks.map((link) => (
        <NavLink
          key={link.path}
          label={link.label}
          leftSection={<link.icon size="1.2rem" />}
          active={location.pathname === link.path || location.pathname.startsWith(link.path + '/')}
          onClick={() => navigate(link.path)}
        />
      ))}

      <Divider my="sm" />

      {/* Data Links */}
      {dataLinks.map((link) => (
        <NavLink
          key={link.path}
          label={link.label}
          leftSection={<link.icon size="1.2rem" />}
          active={location.pathname === link.path || location.pathname.startsWith(link.path + '/')}
          onClick={() => navigate(link.path)}
        />
      ))}

      <Divider my="sm" />

      {/* Config Links */}
      {configLinks.map((link) => (
        <NavLink
          key={link.path}
          label={link.label}
          leftSection={<link.icon size="1.2rem" />}
          active={location.pathname === link.path || location.pathname.startsWith(link.path + '/')}
          onClick={() => navigate(link.path)}
        />
      ))}
    </Box>
  );
}
