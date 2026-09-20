import { AppHeader } from '../components/AppHeader';
import { DataManager } from '../components/DataManager';
import { DomainsSection } from '../components/DomainsSection';
import { MetricCatalog } from '../components/MetricCatalog';
import { MetricChart } from '../components/MetricChart';
import { QuickWeight } from '../components/QuickWeight';
import type { SeriesSpec } from '../api/types';

const WEIGHT_SPEC: SeriesSpec = {
  metricKey: 'body.weight',
  agg: 'avg',
  window: 7,
  label: 'Poids (moyenne 7 j)',
};

export function DashboardPage() {
  return (
    <div>
      <AppHeader />
      <main className="content">
        <section className="card">
          <h2>Poids — tendance</h2>
          <MetricChart spec={WEIGHT_SPEC} />
          <QuickWeight />
        </section>
        <DomainsSection />
        <DataManager />
        <section className="card">
          <MetricCatalog />
        </section>
      </main>
    </div>
  );
}
