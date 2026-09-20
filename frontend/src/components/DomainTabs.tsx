interface DomainTabsProps {
  domains: string[];
  active: string;
  onSelect: (domain: string) => void;
}

export function DomainTabs({ domains, active, onSelect }: DomainTabsProps) {
  return (
    <nav className="tabs">
      {domains.map((domain) => (
        <button
          key={domain}
          className={domain === active ? 'tab active' : 'tab'}
          onClick={() => onSelect(domain)}
        >
          {domain}
        </button>
      ))}
    </nav>
  );
}
