import { useState } from 'react';

import {
  type Correlation,
  createFileReport,
  type WorkHealth,
} from '../../api/workfile';
import { useWorkHealth } from '../../hooks/useWorkFile';
import { localToday } from '../../utils/format';
import { daysAgo } from '../work/format';

const PERIODS = [
  { days: 90, label: '3 mois' },
  { days: 365, label: '1 an' },
  { days: 3650, label: 'Tout' },
];
const STRENGTH: [number, string][] = [
  [0.1, 'négligeable'],
  [0.3, 'faible'],
  [0.5, 'modérée'],
];
const READINGS: Record<string, string> = {
  hours_vs_sleep: 'Heures travaillées / sommeil la nuit suivante',
  hours_vs_awakenings: 'Heures travaillées / réveils la nuit suivante',
  end_vs_sleep: 'Heure de débauche / sommeil la nuit suivante',
};

function reading(corr: Correlation | null): string {
  if (!corr) return 'pas assez de nuits appariées';
  const size = Math.abs(corr.r);
  const word = STRENGTH.find(([limit]) => size < limit)?.[1] ?? 'forte';
  return `r = ${corr.r.toFixed(2)} sur ${corr.n} jours (${word})`;
}

function Report(props: { start: string; end: string }) {
  const [done, setDone] = useState('');
  const make = () =>
    createFileReport(props.start, props.end).then(
      () => setDone('Rapport créé : page Rapports.'),
      (e: Error) => setDone(e.message),
    );
  return (
    <p>
      <button className="btn" onClick={() => void make()}>
        Générer le rapport PDF complet
      </button>{' '}
      <span className="muted">{done}</span>
    </p>
  );
}

function Landmarks({ legal }: { legal: WorkHealth['legal'] }) {
  const parts = [
    `repos < 11 h : ${legal.short_rests.length}`,
    `amplitude > 13 h : ${legal.spread_over_13h.length}`,
    `sessions ≥ 12 h : ${legal.long_sessions.length}`,
    `dimanches : ${legal.sundays.length}`,
    `fériés : ${legal.holidays.length}`,
    `heures de nuit : ${legal.night_hours}`,
  ];
  return <li>{parts.join(' · ')}</li>;
}

function Numbers({ start, end }: { start: string; end: string }) {
  const data = useWorkHealth(start, end).data;
  if (!data) return <p className="muted">Chargement…</p>;
  const src = data.sources;
  const incomplete = src.missing_start + src.missing_end;
  return (
    <ul className="muted">
      <li>
        {`${src.sessions} sessions dont ${incomplete} incomplètes ; ` +
          `${src.nights} nuits connues.`}
      </li>
      <Landmarks legal={data.legal} />
      {Object.entries(data.sleep.correlations).map(([key, corr]) => (
        <li key={key}>
          {READINGS[key]} : {reading(corr)}
        </li>
      ))}
    </ul>
  );
}

/** The work ↔ health file at a glance, and its full PDF report. */
export function FileSummary() {
  const [days, setDays] = useState(365);
  const [start, end] = [daysAgo(days - 1), localToday()];
  return (
    <section className="card">
      <h2>Dossier travail et santé</h2>
      <div className="tabs">
        {PERIODS.map((p) => (
          <button
            key={p.days}
            className={p.days === days ? 'tab active' : 'tab'}
            onClick={() => setDays(p.days)}
          >
            {p.label}
          </button>
        ))}
      </div>
      <Numbers start={start} end={end} />
      <Report start={start} end={end} />
    </section>
  );
}
