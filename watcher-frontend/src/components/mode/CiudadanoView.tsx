import { ReactNode } from 'react';
import { useUserMode } from '../../contexts/UserModeContext';

interface CiudadanoViewProps {
  children: ReactNode;
}

export function CiudadanoView({ children }: CiudadanoViewProps) {
  const { isCiudadano } = useUserMode();
  
  if (!isCiudadano) {
    return null;
  }

  return <>{children}</>;
}

