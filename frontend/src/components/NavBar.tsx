import { NavLink } from 'react-router-dom';

const LINKS = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/dashboards', label: 'Tableaux de bord', end: false },
  { to: '/sante', label: 'Santé', end: false },
  { to: '/donnees', label: 'Données', end: false },
  { to: '/journal', label: 'Journal', end: false },
  { to: '/dossier', label: 'Dossier', end: false },
  { to: '/photos', label: 'Photos', end: false },
  { to: '/suivi', label: 'Suivi', end: false },
  { to: '/rapports', label: 'Rapports', end: false },
  { to: '/import', label: 'Import', end: false },
];

export function NavBar() {
  return (
    <nav className="nav">
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          className={({ isActive }) =>
            isActive ? 'nav-link active' : 'nav-link'
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
