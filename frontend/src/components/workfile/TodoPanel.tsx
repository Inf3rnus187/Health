import type { IncompleteDay } from '../../api/workfile';
import { shortDate } from '../../utils/format';
import { DayCard } from './DayCard';

type Select = (day: string) => void;

function Go(props: { day?: string; label: string; onSelect: Select }) {
  const { day } = props;
  return (
    <button
      className="btn ghost"
      disabled={!day}
      onClick={() => day && props.onSelect(day)}
    >
      {props.label}
    </button>
  );
}

/** « Jour précédent / suivant » among the days to complete. */
function Step(props: { days: string[]; day: string; onSelect: Select }) {
  const at = props.days.indexOf(props.day);
  const before = at > 0 ? props.days[at - 1] : undefined;
  const after = at >= 0 ? props.days[at + 1] : props.days[0];
  return (
    <div className="quick">
      <Go day={before} label="← Jour précédent" onSelect={props.onSelect} />
      <Go day={after} label="Jour suivant →" onSelect={props.onSelect} />
    </div>
  );
}

function Empty({ day }: { day: string }) {
  return (
    <p className="muted">
      {day
        ? `Plus rien à compléter le ${shortDate(day)} ✓`
        : 'Cliquez un jour marqué pour le compléter.'}
    </p>
  );
}

/** The day picked on the calendar: the same cards as the list. */
export function TodoPanel(props: {
  day: string;
  rows: IncompleteDay[];
  days: string[];
  onSelect: Select;
}) {
  const cards = props.rows.filter((r) => r.date_key === props.day);
  return (
    <aside className="todo-panel">
      <Step days={props.days} day={props.day} onSelect={props.onSelect} />
      {cards.length === 0 && <Empty day={props.day} />}
      <ul className="day-list">
        {cards.map((row) => (
          <DayCard key={row.id} row={row} />
        ))}
      </ul>
    </aside>
  );
}
