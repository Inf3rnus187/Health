import { TrendChart } from './TrendChart';

const VITALS: { key: string; label: string }[] = [
  { key: 'heart.rate', label: 'Fréquence cardiaque (bpm)' },
  { key: 'rest.hr', label: 'FC de repos (bpm)' },
  { key: 'heart.hrv', label: 'VFC — SDNN (ms)' },
  { key: 'body.spo2', label: 'SpO2 (%)' },
  { key: 'body.resp_rate', label: 'Fréquence respiratoire' },
  { key: 'sleep.asleep', label: 'Sommeil (min)' },
];

export function VitalsSection() {
  return (
    <section className="card">
      <h2>Signes vitaux — tendances</h2>
      <div className="dash-grid">
        {VITALS.map((vital) => (
          <div className="dash-card" key={vital.key}>
            <h3 className="dash-title">{vital.label}</h3>
            <TrendChart metricKey={vital.key} label={vital.label} />
          </div>
        ))}
      </div>
    </section>
  );
}
