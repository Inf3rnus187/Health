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
    return <p className="muted">Aucun pipi noté aujourd’hui.</p>;
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

/** A pee noted at another time today (the tile's +1 is « now »). */
function AtTime({ today }: { today: string }) {
  const log = useLogUrination();
  const [time, setTime] = useState('');
  const at = time ? new Date(`${today}T${time}`).toISOString() : undefined;
  return (
    <div className="quick">
      <label className="muted">
        Pipi à une autre heure
        <input
          className="input"
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
        />
      </label>
      <button
        className="btn ghost"
        disabled={!time || log.isPending}
        onClick={() => log.mutate(at, { onSuccess: () => setTime('') })}
      >
        Noter
      </button>
    </div>
  );
}

/** Today's pees, each with its time (× removes one), and another time. */
export function PeeTimes() {
  const today = localToday();
  return (
    <div className="pee-times">
      <Times day={today} />
      <AtTime today={today} />
    </div>
  );
}
