import { QuickWeight } from '../components/QuickWeight';
import { SummaryTiles } from '../components/SummaryTiles';
import { TrendChart } from '../components/TrendChart';

export function HomePage() {
  return (
    <>
      <section className="card">
        <h2>Récap du jour</h2>
        <SummaryTiles />
      </section>
      <section className="card">
        <h2>Poids — tendance</h2>
        <TrendChart metricKey="body.weight" label="Poids (kg)" />
        <QuickWeight />
      </section>
    </>
  );
}
