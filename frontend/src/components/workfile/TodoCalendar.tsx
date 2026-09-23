import { localToday } from '../../utils/format';
import {
  type Mark,
  type Month,
  monthDays,
  monthName,
  shiftMonth,
  thisMonth,
  yearTo,
} from './todoCalendar';

const WEEK = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];

const TITLES: Record<Mark, string> = {
  'todo-none': 'à compléter, sans preuve',
  'todo-proof': 'à compléter, preuve présente',
  done: 'journée complète',
  off: 'absence, congé ou férié',
  '': '',
};

interface Pick {
  marks: Map<string, Mark>;
  selected: string;
  onSelect: (day: string) => void;
}

function Day(props: Pick & { day: string; today: string }) {
  const mark = props.marks.get(props.day) ?? '';
  const todo = mark.startsWith('todo');
  const classes = ['cal-day', mark];
  if (props.day === props.selected) classes.push('selected');
  if (props.day === props.today) classes.push('today');
  return (
    <button
      className={classes.join(' ')}
      title={`${props.day.split('-').reverse().join('/')} ${TITLES[mark]}`}
      disabled={!todo}
      onClick={() => props.onSelect(props.day)}
    >
      {Number(props.day.slice(8))}
    </button>
  );
}

function MonthGrid(props: Pick & { month: Month; today: string }) {
  const days = monthDays(props.month);
  const count = days.filter(
    (d) => d && (props.marks.get(d) ?? '').startsWith('todo'),
  ).length;
  return (
    <div className="cal-month">
      <h4>
        {monthName(props.month)}
        {count > 0 && <span className="badge badge-warn">{count}</span>}
      </h4>
      <div className="cal-grid">
        {WEEK.map((w, i) => (
          <span key={i} className="cal-head">
            {w}
          </span>
        ))}
        {days.map((d, i) =>
          d ? <Day key={d} {...props} day={d} /> : <span key={`b${i}`} />,
        )}
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="cal-legend muted">
      {(['todo-none', 'todo-proof', 'done', 'off'] as Mark[]).map((m) => (
        <span key={m}>
          <span className={`cal-dot ${m}`} /> {TITLES[m]}
        </span>
      ))}
    </div>
  );
}

function Nav(props: { last: Month; setLast: (m: Month) => void }) {
  const move = (by: number) => props.setLast(shiftMonth(props.last, by));
  return (
    <div className="quick">
      <button className="btn ghost" onClick={() => move(-12)}>
        ◀ 12 mois
      </button>
      <button className="btn ghost" onClick={() => props.setLast(thisMonth())}>
        Aujourd’hui
      </button>
      <button className="btn ghost" onClick={() => move(12)}>
        12 mois ▶
      </button>
    </div>
  );
}

/** 12 months at a glance: a pastille on each day to complete. */
export function TodoCalendar(
  props: Pick & { last: Month; setLast: (m: Month) => void },
) {
  const today = localToday();
  return (
    <div className="todo-calendar">
      <Nav last={props.last} setLast={props.setLast} />
      <Legend />
      <div className="cal-months">
        {yearTo(props.last).map((m) => (
          <MonthGrid key={m} {...props} month={m} today={today} />
        ))}
      </div>
    </div>
  );
}
