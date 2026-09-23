import { useDomains } from '../hooks/useDomains';
import { useStored } from '../utils/stored';
import { DomainDashboard } from './DomainDashboard';
import { DomainTabs } from './DomainTabs';

export function DomainsSection() {
  const domains = useDomains();
  const [domain, setDomain] = useStored('dashboards.domain', 'body');
  return (
    <section className="card">
      <h2>Tableaux de bord par domaine</h2>
      <DomainTabs domains={domains} active={domain} onSelect={setDomain} />
      <DomainDashboard domain={domain} />
    </section>
  );
}
