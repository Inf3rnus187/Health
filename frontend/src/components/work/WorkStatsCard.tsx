import { useState } from 'react';

import { useWorkStats } from '../../hooks/useWork';
import { useRange } from '../../utils/range';
import { DateRange } from '../DateRange';
import { rememberContract, storedContract } from './format';
import { PeriodsTable, StatsTiles } from './StatsTiles';
import { WeeksChart } from './WeeksChart';
import { WorkExport } from './WorkExport';

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
  const [range, setRange] = useRange(30, 'work.stats');
  const [contract, setContract] = useContract();
  const stats = useWorkStats(range, contract).data;
  return (
    <section className="card">
      <h2>Heures travaillées</h2>
      <DateRange value={range} onChange={setRange} />
      <Contract hours={contract} onHours={setContract} />
      {stats && <StatsTiles stats={stats} />}
      {stats && <WeeksChart weeks={stats.weeks} contract={contract} />}
      <p className="muted">
        Vert : contrat ; pointillés : objectif de la semaine, jours d’absence et
        fériés déduits. Orange : semaine avec arrêt ; gris : congés, repos,
        férié ; violet, empilé : heures à distance. Rouge : 48 h, le maximum
        légal par semaine (10 h par jour). La moyenne par semaine ne compte que
        les semaines complètes ; les « Heures sup » suivent la règle légale
        (heures faites au-delà du contrat).
      </p>
      {stats && <PeriodsTable stats={stats} />}
      <WorkExport range={range} contract={contract} />
    </section>
  );
}
