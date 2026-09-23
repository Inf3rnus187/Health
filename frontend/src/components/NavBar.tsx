import { NavLink } from 'react-router-dom';

import { LINKS } from './navLinks';

/** Every page; ``onPick`` closes the phone menu once one is chosen. */
export function NavLinks({ onPick }: { onPick?: () => void }) {
  return (
    <>
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          onClick={onPick}
          className={({ isActive }) =>
            isActive ? 'nav-link active' : 'nav-link'
          }
        >
          {link.label}
        </NavLink>
      ))}
    </>
  );
}

/** The menu row under the header (a wide screen; hidden on a phone). */
export function NavBar() {
  return (
    <nav className="nav">
      <NavLinks />
    </nav>
  );
}
