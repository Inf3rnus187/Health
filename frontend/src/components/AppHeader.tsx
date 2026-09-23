import { useState } from 'react';

import { useAuth } from '../auth/useAuth';
import { NavLinks } from './NavBar';
import { useHere } from './navLinks';
import { ThemeToggle } from './ThemeToggle';

/** On a phone: every page in a grid, then the account and sign-out. */
function PhoneMenu(props: { email?: string; onClose: () => void }) {
  const { signOut } = useAuth();
  return (
    <div className="phone-menu">
      <nav className="phone-links">
        <NavLinks onPick={props.onClose} />
      </nav>
      <div className="phone-account">
        <span className="muted">{props.email}</span>
        <button className="btn ghost" onClick={() => void signOut()}>
          Déconnexion
        </button>
      </div>
    </div>
  );
}

function MenuButton(props: { open: boolean; toggle: () => void }) {
  const here = useHere();
  return (
    <button
      className="btn ghost menu-button"
      aria-expanded={props.open}
      onClick={props.toggle}
    >
      {props.open ? '✕' : '☰'} {here}
    </button>
  );
}

export function AppHeader() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <header className="header">
      <h1 className="brand">
        Phoenix<span className="wide-only"> Health Hub</span>
      </h1>
      <div className="header-right">
        <span className="muted wide-only">{user?.email}</span>
        <ThemeToggle />
        <button className="btn ghost wide-only" onClick={() => void signOut()}>
          Déconnexion
        </button>
        <MenuButton open={open} toggle={() => setOpen(!open)} />
      </div>
      {open && <PhoneMenu email={user?.email} onClose={() => setOpen(false)} />}
    </header>
  );
}
