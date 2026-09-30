import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { useAuth } from './auth/useAuth';
import { Layout } from './components/Layout';
import {
  CarePage,
  DashboardsPage,
  DataPage,
  HealthPage,
  HomePage,
  ImportPage,
  JournalPage,
  MedicalPage,
  PhotosPage,
  ReportsPage,
  WorkPage,
} from './pages/lazyPages';
import { LoginPage } from './pages/LoginPage';

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

const UNREACHABLE =
  'Le hub ne répond pas (redémarrage après une mise à jour ?) — ' +
  'nouvel essai toutes les 5 s…';

export function App() {
  const { user, ready, waiting } = useAuth();
  if (!ready) {
    return (
      <p className="center muted">{waiting ? UNREACHABLE : 'Chargement…'}</p>
    );
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
