import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { useAuth } from './auth/useAuth';
import { Layout } from './components/Layout';
import { CarePage } from './pages/CarePage';
import { DashboardsPage } from './pages/DashboardsPage';
import { DataPage } from './pages/DataPage';
import { HealthPage } from './pages/HealthPage';
import { HomePage } from './pages/HomePage';
import { ImportPage } from './pages/ImportPage';
import { JournalPage } from './pages/JournalPage';
import { LoginPage } from './pages/LoginPage';
import { MedicalPage } from './pages/MedicalPage';
import { PhotosPage } from './pages/PhotosPage';
import { ReportsPage } from './pages/ReportsPage';
import { WorkPage } from './pages/WorkPage';

function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="dashboards" element={<DashboardsPage />} />
        <Route path="sante" element={<HealthPage />} />
        <Route path="donnees" element={<DataPage />} />
        <Route path="dossier" element={<MedicalPage />} />
        <Route path="journal" element={<JournalPage />} />
        <Route path="travail" element={<WorkPage />} />
        <Route path="photos" element={<PhotosPage />} />
        <Route path="suivi" element={<CarePage />} />
        <Route path="rapports" element={<ReportsPage />} />
        <Route path="import" element={<ImportPage />} />
      </Route>
    </Routes>
  );
}

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
      <AppRoutes />
    </BrowserRouter>
  );
}
