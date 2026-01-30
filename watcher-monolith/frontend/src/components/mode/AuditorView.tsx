import { ReactNode } from 'react';
import { useUserMode } from '../../contexts/UserModeContext';

interface AuditorViewProps {
  children: ReactNode;
}

export function AuditorView({ children }: AuditorViewProps) {
  const { isAuditor } = useUserMode();
  
  if (!isAuditor) {
    return null;
  }

  return <>{children}</>;
}

