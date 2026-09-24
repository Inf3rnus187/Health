import { useState } from 'react';

import type { TodayDoses } from '../../api/medications';
import {
  useDeleteDose,
  useTakeDose,
  useTodayDoses,
} from '../../hooks/useMedications';
import { clock, nowLocal } from './time';

function count(t: TodayDoses): string {
  const planned = t.doses_per_day ? `/${t.doses_per_day}` : '';
  const not = t.skipped ? ` · ${t.skipped} non pris` : '';
  const last = t.last_at ? ` · dernier à ${clock(t.last_at)}` : '';
  return `${t.taken}${planned} aujourd’hui${not}${last}`;
}

/** « Pris à une autre heure »: a time, then « Noter ». */
function AtTime(props: { onTake: (at: string) => void }) {
  const [at, setAt] = useState<string | null>(null);
  if (at === null) {
    return (
      <button className="btn ghost" onClick={() => setAt(nowLocal())}>
        Pris à…
      </button>
    );
  }
  return (
    <span className="quick">
      <input
        className="input"
        type="datetime-local"
        value={at}
        onChange={(e) => setAt(e.target.value)}
      />
      <button className="btn ghost" onClick={() => props.onTake(at)}>
        Noter
      </button>
    </span>
  );
}

function Undo({ onClick }: { onClick: () => void }) {
  return (
    <button
      className="btn ghost"
      title="Retirer la dernière prise notée aujourd’hui"
      onClick={onClick}
    >
      ↶ Annuler
    </button>
  );
}

function Buttons({ t }: { t: TodayDoses }) {
  const take = useTakeDose();
  const undo = useDeleteDose();
  const dose = (status: 'taken' | 'skipped', taken_at?: string) =>
    take.mutate({ id: t.treatment_id, dose: { status, taken_at } });
  const last = t.last_id;
  return (
    <div className="row-actions">
      <button className="btn" onClick={() => dose('taken')}>
        ✔ Pris
      </button>
      <AtTime onTake={(at) => dose('taken', at)} />
      <button className="btn ghost" onClick={() => dose('skipped')}>
        ✗ Non pris
      </button>
      {last && <Undo onClick={() => undo.mutate(last)} />}
    </div>
  );
}

function Row({ t }: { t: TodayDoses }) {
  return (
    <li className="med-row">
      <div>
        <strong>{t.name}</strong>{' '}
        {t.dose && <span className="muted">{t.dose}</span>}
        <div className="muted small">{count(t)}</div>
      </div>
      <Buttons t={t} />
    </li>
  );
}

/** Today's doses of each active treatment, one tap each. */
export function MedsToday() {
  const items = useTodayDoses().data ?? [];
  return (
    <section className="card">
      <h2>💊 Médicaments du jour</h2>
      {items.length === 0 ? (
        <p className="muted">
          Aucun traitement actif : ajoutez-les dans Suivi › Traitements (avec le
          nombre de prises par jour).
        </p>
      ) : (
        <ul className="med-list">
          {items.map((t) => (
            <Row key={t.treatment_id} t={t} />
          ))}
        </ul>
      )}
    </section>
  );
}
