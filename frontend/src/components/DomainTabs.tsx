const DOMAINS = ['body', 'sleep', 'ppc', 'workout', 'walk', 'habit', 'state'];

interface DomainTabsProps {
  active: string;
  onSelect: (domain: string) => void;
}

export function DomainTabs({ active, onSelect }: DomainTabsProps) {
  return (
    <nav className="tabs">
      {DOMAINS.map((domain) => (
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
