import { useDomainLabel } from '../hooks/useDomains';

interface DomainTabsProps {
  domains: string[];
  active: string;
  onSelect: (domain: string) => void;
}

export function DomainTabs({ domains, active, onSelect }: DomainTabsProps) {
  const label = useDomainLabel();
  return (
    <nav className="tabs">
      {domains.map((domain) => (
        <button
          key={domain}
          className={domain === active ? 'tab active' : 'tab'}
          onClick={() => onSelect(domain)}
        >
          {label(domain)}
        </button>
      ))}
    </nav>
  );
}
