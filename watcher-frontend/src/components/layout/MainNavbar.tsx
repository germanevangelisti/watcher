import { Box, NavLink, Divider } from '@mantine/core';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  IconHome,
  IconRobot,
  IconHistory,
  IconAlertTriangle,
  IconFileText,
  IconCash,
  IconSettings,
  IconMapPin,
  IconWand,
  IconRefresh,
  IconDownload,
  IconCalendar,
  IconSearch,
  IconGraph,
  IconShieldCheck
} from '@tabler/icons-react';

export function MainNavbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const mainLinks = [
    { icon: IconHome, label: 'Dashboard', path: '/' },
    { icon: IconWand, label: 'Asistente', path: '/wizard', highlight: true },
    { icon: IconRobot, label: 'Agentes IA', path: '/agents' },
    { icon: IconSearch, label: 'Búsqueda', path: '/search' },
    { icon: IconGraph, label: 'Grafo', path: '/knowledge-graph' },
    { icon: IconHistory, label: 'Historial', path: '/history' },
  ];

  const dataLinks = [
    { icon: IconMapPin, label: 'Jurisdicciones', path: '/jurisdicciones' },
    { icon: IconShieldCheck, label: 'Compliance Fiscal', path: '/compliance' },
    { icon: IconAlertTriangle, label: 'Alertas', path: '/alertas' },
    { icon: IconFileText, label: 'Documentos', path: '/documentos' },
    { icon: IconCash, label: 'Presupuesto', path: '/presupuesto' },
  ];

  const gestionLinks = [
    { icon: IconRefresh, label: 'Sincronización', path: '/sync' },
    { icon: IconDownload, label: 'Descarga Manual', path: '/downloader' },
    { icon: IconCalendar, label: 'Calendario', path: '/calendar' },
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
          variant={(link as any).highlight ? 'filled' : undefined}
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

      {/* Gestión Links */}
      {gestionLinks.map((link) => (
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
