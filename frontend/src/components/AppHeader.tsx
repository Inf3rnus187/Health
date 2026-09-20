import { useAuth } from '../auth/useAuth';
import { ThemeToggle } from './ThemeToggle';

export function AppHeader() {
  const { user, signOut } = useAuth();
  return (
    <header className="header">
      <h1 className="brand">Phoenix Health Hub</h1>
      <div className="header-right">
        <span className="muted">{user?.email}</span>
        <ThemeToggle />
        <button className="btn ghost" onClick={() => void signOut()}>
          Déconnexion
        </button>
      </div>
    </header>
  );
}
