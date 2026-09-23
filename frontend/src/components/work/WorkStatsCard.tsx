import { useState } from 'react';

import { useWorkStats } from '../../hooks/useWork';
import { localToday } from '../../utils/format';
import { daysAgo, rememberContract, storedContract } from './format';
import { PeriodsTable, StatsTiles } from './StatsTiles';
import { WeeksChart } from './WeeksChart';
import { WorkExport } from './WorkExport';

const PERIODS = [
  { days: 7, label: '7 jours' },
  { days: 30, label: '30 jours' },
  { days: 90, label: '3 mois' },
  { days: 365, label: '1 an' },
  { days: 3650, label: 'Tout' },
];

function Tabs(props: { days: number; onDays: (days: number) => void }) {
  return (
    <div className="tabs">
      {PERIODS.map((p) => (
        <button
          key={p.days}
          className={p.days === props.days ? 'tab active' : 'tab'}
          onClick={() => props.onDays(p.days)}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

function Contract(props: { hours: number; onHours: (h: number) => void }) {
  return (
    <label className="muted">
      Contrat (heures par semaine){' '}
      <input
        className="input"
        style={{ width: '6rem' }}
        type="number"
        min={1}
        max={80}
        value={props.hours}
        onChange={(e) => props.onHours(Number(e.target.value) || 35)}
      />
    </label>
  );
}

function useContract(): [number, (hours: number) => void] {
  const [hours, setHours] = useState(storedContract);
  const save = (value: number) => {
    rememberContract(value);
    setHours(value);
  };
  return [hours, save];
}

/** Hours worked over a period: numbers, weeks, periods, export. */
export function WorkStatsCard() {
  const [days, setDays] = useState(30);
  const [contract, setContract] = useContract();
  const [start, end] = [daysAgo(days - 1), localToday()];
  const stats = useWorkStats(start, end, contract).data;
  return (
    <section className="card">
      <h2>Heures travaillées</h2>
      <Tabs days={days} onDays={setDays} />
      <Contract hours={contract} onHours={setContract} />
      {stats && <StatsTiles stats={stats} />}
      {stats && <WeeksChart weeks={stats.weeks} contract={contract} />}
      <p className="muted">
        Vert : contrat. Rouge : 48 h, le maximum légal par semaine (10 h par
        jour).
      </p>
      {stats && <PeriodsTable stats={stats} />}
      <WorkExport start={start} end={end} contract={contract} />
    </section>
  );
}
