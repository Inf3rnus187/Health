import { useState } from 'react';

import type { IncompleteDay } from '../../api/workfile';
import { useDeleteSession } from '../../hooks/useWork';
import { useCompleteSession, useIncomplete } from '../../hooks/useWorkFile';
import { shortDate } from '../../utils/format';
import { usePaging } from '../Paging';
import { clockTime } from '../work/format';
import { DayHints, ProofBadge } from './DayHints';
import { Choice, Input } from './fields';

const SHOW: Record<string, string> = {
  all: 'Toutes',
  proof: 'Avec preuve',
  none: 'Sans preuve',
  start: 'Embauche manquante',
  end: 'Débauche manquante',
};

function keep(row: IncompleteDay, show: string): boolean {
  const c = row.context;
  if (show === 'proof' || show === 'none') {
    return c.has_proof === (show === 'proof');
  }
  return show === 'all' || c.missing === show;
}

function Known({ row }: { row: IncompleteDay }) {
  return (
    <strong>
      {row.context.usual.weekday} {shortDate(row.date_key)} —{' '}
      {row.start_at
        ? `embauche ${clockTime(row.start_at)}, débauche ?`
        : `embauche ?, débauche ${clockTime(row.end_at)}`}{' '}
    </strong>
  );
}

interface ActionProps {
  row: IncompleteDay;
  at: string;
  note: string;
}

function Actions({ row, at, note }: ActionProps) {
  const complete = useCompleteSession();
  const del = useDeleteSession();
  const field = row.context.missing === 'start' ? 'start_at' : 'end_at';
  const body = note ? { [field]: at, note } : { [field]: at };
  return (
    <>
      <button
        className="btn"
        disabled={!at}
        onClick={() => complete.mutate({ id: row.id, body })}
      >
        Compléter
      </button>
      <button className="btn ghost" onClick={() => del.mutate(row.id)}>
        Supprimer
      </button>
      {complete.error && (
        <span className="error">{complete.error.message}</span>
      )}
    </>
  );
}

function Fill({ row }: { row: IncompleteDay }) {
  const [at, setAt] = useState('');
  const [note, setNote] = useState('');
  const label = row.context.missing === 'start' ? 'Embauche' : 'Débauche';
  return (
    <li>
      <Known row={row} /> <ProofBadge row={row} />
      <DayHints row={row} pick={setAt} />
      <div className="quick">
        <Input
          label={label}
          type="datetime-local"
          value={at}
          onChange={setAt}
        />
        <Input
          label="D’où vient l’heure (note)"
          value={note}
          onChange={setNote}
        />
        <Actions row={row} at={at} note={note} />
      </div>
    </li>
  );
}

function Help() {
  return (
    <p className="muted">
      Embauche ou débauche non pointée (montre sans batterie, GPS muet). Cliquez
      un indice pour pré-remplir l’heure : trace ou preuve du jour (taxi,
      parking, ticket…), réveil, premiers / derniers pas, votre heure habituelle
      ce jour de la semaine. Ajustez, notez d’où vient l’heure, puis « Compléter
      » : la session est marquée corrigée à la main.
    </p>
  );
}

/** Every session with a missing half, with what helps to complete it. */
export function Incomplete() {
  const rows = useIncomplete().data ?? [];
  const [show, setShow] = useState('all');
  const { page, bar } = usePaging(rows.filter((r) => keep(r, show)));
  const proofs = rows.filter((r) => r.context.has_proof).length;
  return (
    <section className="card">
      <h2>
        Journées à compléter ({rows.length}, dont {proofs} avec preuve)
      </h2>
      <Help />
      <Choice options={SHOW} value={show} onChange={setShow} />
      {bar}
      <ul className="care-list">
        {page.map((row) => (
          <Fill key={row.id} row={row} />
        ))}
      </ul>
    </section>
  );
}
