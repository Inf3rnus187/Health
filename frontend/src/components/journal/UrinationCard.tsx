import { useState } from 'react';

import {
  useDeleteUrination,
  useLogUrination,
  useUrinations,
} from '../../hooks/useJournal';
import { localToday } from '../../utils/format';
import { clock } from './time';

function Times({ day }: { day: string }) {
  const items = useUrinations(day).data?.items ?? [];
  const del = useDeleteUrination();
  if (items.length === 0) {
    return <p className="muted">Aucun pour l’instant aujourd’hui.</p>;
  }
  return (
    <ul className="chips">
      {items.map((item) => (
        <li key={item.id} className="chip">
          {clock(item.at)}
          <button
            className="chip-x"
            title="Supprimer"
            onClick={() => del.mutate(item.id)}
          >
            ×
          </button>
        </li>
      ))}
    </ul>
  );
}

function Tap({ today }: { today: string }) {
  const log = useLogUrination();
  const [time, setTime] = useState('');
  const at = time ? new Date(`${today}T${time}`).toISOString() : undefined;
  return (
    <div className="quick">
      <button
        className="btn"
        disabled={log.isPending}
        onClick={() => log.mutate(at, { onSuccess: () => setTime('') })}
      >
        {time ? `Noter à ${time}` : 'Pipi maintenant'}
      </button>
      <input
        className="input"
        type="time"
        aria-label="Autre heure"
        value={time}
        onChange={(e) => setTime(e.target.value)}
      />
    </div>
  );
}

/** One tap = one urination, now or at a chosen time today. */
export function UrinationCard() {
  const today = localToday();
  const count = useUrinations(today).data?.count ?? 0;
  return (
    <section className="card">
      <h2>Pipi — aujourd’hui : {count}</h2>
      <Tap today={today} />
      <Times day={today} />
    </section>
  );
}
