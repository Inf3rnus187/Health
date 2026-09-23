import { Outlet } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { NavBar } from './NavBar';
import { UpdateBanner } from './UpdateBanner';

export function Layout() {
  return (
    <div>
      <AppHeader />
      <NavBar />
      <main className="content">
        <UpdateBanner />
        <Outlet />
      </main>
    </div>
  );
}
