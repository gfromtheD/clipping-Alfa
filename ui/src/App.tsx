import React from 'react';
import { AppShell } from './components/AppShell';

export const App: React.FC = () => {
  return (
    <main className="w-full flex items-center justify-center">
      <AppShell />
    </main>
  );
};

export default App;
