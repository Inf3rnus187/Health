import type { IncompleteDay, OtherSession } from '../../api/workfile';
import { useMergeSession } from '../../hooks/useWorkFile';

type Pick = (at: string) => void;

function times(o: OtherSession): string {
  const place = o.place === 'remote' ? ' (à distance)' : '';
  const alone = !o.start
    ? ' — débauche seule'
    : !o.end
      ? ' — embauche seule'
      : '';
  return `${o.start ?? '?'} → ${o.end ?? '?'}${place}${alone}`;
}

function Merge(props: { row: IncompleteDay; o: OtherSession }) {
  const merge = useMergeSession();
  const { o } = props;
  if (!o.merged) return null;
  const run = () =>
    window.confirm(
      `Réunir les deux en une seule session ${o.merged} ? ` +
        'L’autre session est supprimée (la note le garde).',
    ) && merge.mutate({ id: props.row.id, other: o.id });
  return (
    <>
      <button className="btn" onClick={run}>
        Réunir : {o.merged}
      </button>
      {merge.error && <span className="error">{merge.error.message}</span>}
    </>
  );
}

function Free(props: { row: IncompleteDay; o: OtherSession; pick: Pick }) {
  const { free } = props.o;
  if (!free) return null;
  const start = props.row.context.missing === 'start';
  const label = start ? 'Embauche après elle' : 'Débauche avant elle';
  return (
    <button className="btn ghost" onClick={() => props.pick(free.slice(0, 16))}>
      {label} : {free.slice(11, 16)}
    </button>
  );
}

/** The day's other sessions: merge a lone half, or clock around them. */
export function DayOthers(props: { row: IncompleteDay; pick: Pick }) {
  const others = props.row.context.others;
  if (others.length === 0) return null;
  return (
    <>
      <h4>Autres sessions ce jour-là (une heure ne peut pas les chevaucher)</h4>
      <ul className="care-list">
        {others.map((o) => (
          <li key={o.id} className="quick">
            <strong>{times(o)}</strong>
            <Merge row={props.row} o={o} />
            <Free row={props.row} o={o} pick={props.pick} />
          </li>
        ))}
      </ul>
    </>
  );
}
