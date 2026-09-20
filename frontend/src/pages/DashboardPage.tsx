import { AppHeader } from '../components/AppHeader';
import { DomainsSection } from '../components/DomainsSection';
import { ImportPanel } from '../components/ImportPanel';
import { MetricCatalog } from '../components/MetricCatalog';
import { QuickWeight } from '../components/QuickWeight';
import { SamplesBrowser } from '../components/SamplesBrowser';
import { TrendChart } from '../components/TrendChart';

export function DashboardPage() {
  return (
    <div>
      <AppHeader />
      <main className="content">
        <section className="card">
          <h2>Poids — tendance</h2>
          <TrendChart metricKey="body.weight" label="Poids (kg)" />
          <QuickWeight />
        </section>
        <ImportPanel />
        <DomainsSection />
        <SamplesBrowser />
        <section className="card">
          <MetricCatalog />
        </section>
      </main>
    </div>
  );
}
