import { MetricPanel } from './metric/MetricPanel';

const VITALS = [
  'heart.rate',
  'rest.hr',
  'heart.hrv',
  'body.spo2',
  'body.resp_rate',
  'sleep.asleep',
];

export function VitalsSection() {
  return (
    <section className="card">
      <h2>Signes vitaux — tendances</h2>
      <div className="dash-grid">
        {VITALS.map((key) => (
          <MetricPanel key={key} metricKey={key} compact />
        ))}
      </div>
    </section>
  );
}
