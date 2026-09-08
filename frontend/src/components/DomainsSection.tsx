import { useState } from 'react';

import { DomainDashboard } from './DomainDashboard';
import { DomainTabs } from './DomainTabs';

export function DomainsSection() {
  const [domain, setDomain] = useState('body');
  return (
    <section className="card">
      <h2>Tableaux de bord par domaine</h2>
      <DomainTabs active={domain} onSelect={setDomain} />
      <DomainDashboard domain={domain} />
    </section>
  );
}
