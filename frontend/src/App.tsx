import { useAuth } from './auth/useAuth';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';

export function App() {
  const { user, ready } = useAuth();
  if (!ready) {
    return <p className="center muted">Chargement…</p>;
  }
  return user ? <DashboardPage /> : <LoginPage />;
}
