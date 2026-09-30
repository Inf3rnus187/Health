import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import { AuthProvider } from './auth/AuthProvider';
import { loadHubSettings } from './settings';
import { applyTheme, initialTheme } from './theme/mode';
import './styles.css';

applyTheme(initialTheme());
const client = new QueryClient();
const root = document.getElementById('root');
if (!root) {
  throw new Error('Missing #root element');
}

const draw = () =>
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={client}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
// The hub's timings and limits first (GET /system/settings), then the page.
void loadHubSettings().finally(draw);
