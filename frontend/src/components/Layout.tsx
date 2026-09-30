import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { NavBar } from './NavBar';
import { PageError } from './PageError';
import { UpdateBanner } from './UpdateBanner';

export function Layout() {
  // a new page starts without the previous one's loading error
  const { pathname } = useLocation();
  return (
    <div>
      <AppHeader />
      <NavBar />
      <main className="content">
        <UpdateBanner />
        <PageError key={pathname}>
          <Suspense fallback={<p className="center muted">Chargement…</p>}>
            <Outlet />
          </Suspense>
        </PageError>
      </main>
    </div>
  );
}
