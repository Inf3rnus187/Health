import type { ReactNode } from 'react';

/** A link to an outside explanation page. */
export function RefLink(props: { href: string; children: ReactNode }) {
  return (
    <a
      className="ref-link"
      href={props.href}
      target="_blank"
      rel="noreferrer noopener"
    >
      {props.children}
    </a>
  );
}
