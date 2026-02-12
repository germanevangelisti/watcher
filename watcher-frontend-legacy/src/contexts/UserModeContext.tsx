import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type UserMode = 'ciudadano' | 'auditor';

interface UserModeContextType {
  mode: UserMode;
  setMode: (mode: UserMode) => void;
  toggleMode: () => void;
  isCiudadano: boolean;
  isAuditor: boolean;
}

const UserModeContext = createContext<UserModeContextType | undefined>(undefined);

export function UserModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<UserMode>(() => {
    const saved = localStorage.getItem('watcher-user-mode');
    return (saved === 'auditor' ? 'auditor' : 'ciudadano') as UserMode;
  });

  useEffect(() => {
    localStorage.setItem('watcher-user-mode', mode);
  }, [mode]);

  const setMode = (newMode: UserMode) => {
    setModeState(newMode);
  };

  const toggleMode = () => {
    setModeState(prev => prev === 'ciudadano' ? 'auditor' : 'ciudadano');
  };

  const value: UserModeContextType = {
    mode,
    setMode,
    toggleMode,
    isCiudadano: mode === 'ciudadano',
    isAuditor: mode === 'auditor',
  };

  return (
    <UserModeContext.Provider value={value}>
      {children}
    </UserModeContext.Provider>
  );
}

export function useUserMode() {
  const context = useContext(UserModeContext);
  if (context === undefined) {
    throw new Error('useUserMode must be used within a UserModeProvider');
  }
  return context;
}

