import { lazy, type ComponentType } from 'react';

const RELOADED_AT = 'pages.reloadedAt';
const ONCE_A_MINUTE = 60_000;

// A page's code left behind by an update (the hub was updated while the
// page stayed open): load the new version, at most once a minute, then
// let PageError say it failed rather than reload again and again.
function reloadOnce(error: unknown): Promise<never> {
  try {
    const last = Number(sessionStorage.getItem(RELOADED_AT) ?? 0);
    if (Date.now() - last > ONCE_A_MINUTE) {
      sessionStorage.setItem(RELOADED_AT, String(Date.now()));
      window.location.reload();
      return new Promise<never>(() => undefined);
    }
  } catch {
    // no session storage: show the error rather than reload in a loop
  }
  return Promise.reject(error);
}

// Each page is fetched the first time it is opened, not with the whole
// application: the phone downloads and reads less before the home page.
function page<K extends string>(
  load: () => Promise<Record<K, ComponentType>>,
  name: K,
) {
  return lazy(() =>
    load().then((module) => ({ default: module[name] }), reloadOnce),
  );
}

// The home page is the first one shown: its code is fetched at once,
// while the session is restored or the login page is on screen.
const home = import('./HomePage');
home.catch(() => undefined); // handled when the page is shown
export const HomePage = page(() => home, 'HomePage');
export const DashboardsPage = page(
  () => import('./DashboardsPage'),
  'DashboardsPage',
);
export const HealthPage = page(() => import('./HealthPage'), 'HealthPage');
export const DataPage = page(() => import('./DataPage'), 'DataPage');
export const MedicalPage = page(() => import('./MedicalPage'), 'MedicalPage');
export const JournalPage = page(() => import('./JournalPage'), 'JournalPage');
export const WorkPage = page(() => import('./WorkPage'), 'WorkPage');
export const PhotosPage = page(() => import('./PhotosPage'), 'PhotosPage');
export const CarePage = page(() => import('./CarePage'), 'CarePage');
export const ReportsPage = page(() => import('./ReportsPage'), 'ReportsPage');
export const ImportPage = page(() => import('./ImportPage'), 'ImportPage');
