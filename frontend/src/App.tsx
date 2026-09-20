import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { useAuth } from './auth/useAuth';
import { Layout } from './components/Layout';
import { DashboardsPage } from './pages/DashboardsPage';
import { DataPage } from './pages/DataPage';
import { HealthPage } from './pages/HealthPage';
import { HomePage } from './pages/HomePage';
import { ImportPage } from './pages/ImportPage';
import { LoginPage } from './pages/LoginPage';
import { ReportsPage } from './pages/ReportsPage';

export function App() {
  const { user, ready } = useAuth();
  if (!ready) {
    return <p className="center muted">Chargement…</p>;
  }
  if (!user) {
    return <LoginPage />;
  }
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="dashboards" element={<DashboardsPage />} />
          <Route path="sante" element={<HealthPage />} />
          <Route path="donnees" element={<DataPage />} />
          <Route path="rapports" element={<ReportsPage />} />
          <Route path="import" element={<ImportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
