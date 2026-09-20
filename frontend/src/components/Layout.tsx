import { Outlet } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { NavBar } from './NavBar';

export function Layout() {
  return (
    <div>
      <AppHeader />
      <NavBar />
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
