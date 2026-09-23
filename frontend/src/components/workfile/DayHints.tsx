import type { IncompleteDay } from '../../api/workfile';
import { type Hint, hintsOf } from './dayHints';

/** "Preuve présente" or not, at a glance. */
export function ProofBadge({ row }: { row: IncompleteDay }) {
  return row.context.has_proof ? (
    <span className="badge badge-done">preuve présente</span>
  ) : (
    <span className="badge">sans preuve</span>
  );
}

function HintChip(props: { hint: Hint; pick: (at: string) => void }) {
  const { hint, pick } = props;
  if (!hint.at) {
    return (
      <span className="muted" title={hint.title}>
        {hint.label}
      </span>
    );
  }
  return (
    <button className="chip" title={hint.title} onClick={() => pick(hint.at)}>
      {hint.label}
    </button>
  );
}

/** Clickable times (traces, wake-up, steps, habit) to fill the day. */
export function DayHints(props: {
  row: IncompleteDay;
  pick: (at: string) => void;
}) {
  const hints = hintsOf(props.row);
  if (hints.length === 0) {
    return <p className="muted">Aucun indice ce jour-là.</p>;
  }
  return (
    <div className="chips">
      {hints.map((h) => (
        <HintChip key={h.key} hint={h} pick={props.pick} />
      ))}
    </div>
  );
}
