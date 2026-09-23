// The app's pages, for the menu row and the phone menu.
import { useLocation } from 'react-router-dom';

export const LINKS = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/dashboards', label: 'Tableaux de bord', end: false },
  { to: '/sante', label: 'Santé', end: false },
  { to: '/donnees', label: 'Données', end: false },
  { to: '/journal', label: 'Journal', end: false },
  { to: '/travail', label: 'Travail', end: false },
  { to: '/dossier', label: 'Dossier', end: false },
  { to: '/photos', label: 'Photos', end: false },
  { to: '/suivi', label: 'Suivi', end: false },
  { to: '/rapports', label: 'Rapports', end: false },
  { to: '/import', label: 'Import', end: false },
];

/** The page open, by its menu label (« Accueil » at the root). */
export function useHere(): string {
  const { pathname } = useLocation();
  const found = LINKS.find((link) =>
    link.end ? pathname === link.to : pathname.startsWith(link.to),
  );
  return found?.label ?? 'Menu';
}
