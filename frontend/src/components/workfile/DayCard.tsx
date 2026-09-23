import { useState } from 'react';

import type { IncompleteDay } from '../../api/workfile';
import { useDeleteSession } from '../../hooks/useWork';
import { useCompleteSession } from '../../hooks/useWorkFile';
import { shortDate } from '../../utils/format';
import { clockTime } from '../work/format';
import { Landmarks, ProofBadge, ProofTable } from './DayHints';
import { DayOthers } from './DayOthers';
import { Input } from './fields';
import { AddProof } from './ProofForm';

function Missing() {
  return <span className="day-missing">? à compléter</span>;
}

function Head({ row }: { row: IncompleteDay }) {
  const start = row.start_at ? clockTime(row.start_at) : <Missing />;
  const end = row.end_at ? clockTime(row.end_at) : <Missing />;
  return (
    <div className="day-head">
      <strong>
        {row.context.usual.weekday} {shortDate(row.date_key)}
      </strong>
      <span>
        Embauche {start} · Débauche {end}
        {row.place === 'remote' && ' (à distance)'}
      </span>
      <ProofBadge row={row} />
    </div>
  );
}

function useSave(row: IncompleteDay) {
  const complete = useCompleteSession();
  const field = row.context.missing === 'start' ? 'start_at' : 'end_at';
  const save = (at: string, note: string) =>
    complete.mutate({
      id: row.id,
      body: note ? { [field]: at, note } : { [field]: at },
    });
  return { save, error: complete.error };
}

function Save(props: { row: IncompleteDay; at: string; note: string }) {
  const { save, error } = useSave(props.row);
  const del = useDeleteSession();
  const drop = () =>
    window.confirm('Supprimer cette session ?') && del.mutate(props.row.id);
  return (
    <>
      <button
        className="btn"
        disabled={!props.at}
        onClick={() => save(props.at, props.note)}
      >
        Compléter
      </button>
      <button className="btn ghost" onClick={drop}>
        Supprimer la session
      </button>
      {error && <span className="error">{error.message}</span>}
    </>
  );
}

function Kept(props: {
  row: IncompleteDay;
  at: string;
  setAt: (at: string) => void;
}) {
  const [note, setNote] = useState('');
  const label = props.row.context.missing === 'start' ? 'Embauche' : 'Débauche';
  return (
    <>
      <h4>{label} retenue</h4>
      <div className="quick">
        <Input
          label={label}
          type="datetime-local"
          value={props.at}
          onChange={props.setAt}
        />
        <Input label="D’où vient l’heure" value={note} onChange={setNote} />
        <Save row={props.row} at={props.at} note={note} />
      </div>
    </>
  );
}

/** One day to complete: what is known, the proofs, the landmarks. */
export function DayCard({ row }: { row: IncompleteDay }) {
  const [at, setAt] = useState('');
  return (
    <li className="day-card">
      <Head row={row} />
      <DayOthers row={row} pick={setAt} />
      <h4>Preuves et traces (le lendemain matin compris)</h4>
      <ProofTable row={row} pick={setAt} />
      <AddProof when={`${row.date_key}T12:00`} label=" pour ce jour" />
      <h4>Repères</h4>
      <Landmarks row={row} pick={setAt} />
      <Kept row={row} at={at} setAt={setAt} />
    </li>
  );
}
