import type { WorkDayLine } from '../../api/work';
import { useWorkDays } from '../../hooks/useWork';
import { useRange } from '../../utils/range';
import { useStored } from '../../utils/stored';
import { DateRange } from '../DateRange';
import { usePaging } from '../Paging';
import { DayLine } from './DayLine';
import { hm } from './format';

const HEAD = [
  'Jour',
  'Nuit (avant)',
  'Réveil',
  'Embauche',
  'Débauche',
  'Travaillé',
  'Coucher',
  'Absence',
  'Preuves',
  'État',
];

const SHOW: Record<string, (d: WorkDayLine) => boolean> = {
  'Tous les jours': () => true,
  'Jours travaillés': (d) => d.sessions > 0,
  'À compléter': (d) => d.state === 'a_completer',
  Absences: (d) => d.absence !== null && d.absence !== 'ferie',
  'Avec preuves': (d) => d.proofs.length > 0,
};

function Totals({ days }: { days: WorkDayLine[] }) {
  const worked = days.filter((d) => d.hours);
  const hours = worked.reduce((sum, d) => sum + (d.hours ?? 0), 0);
  const remote = days.reduce((sum, d) => sum + d.remote, 0);
  const slept = days.filter((d) => d.sleep_min != null);
  const sleep = slept.reduce((sum, d) => sum + (d.sleep_min ?? 0), 0);
  const todo = days.filter((d) => d.state === 'a_completer').length;
  return (
    <p className="muted">
      {`${worked.length} jours travaillés · ${hm(hours)}` +
        (remote ? ` (dont ${hm(remote)} à distance)` : '') +
        (slept.length
          ? ` · sommeil moyen ${hm(sleep / slept.length / 60)}`
          : '') +
        (todo ? ` · ${todo} à compléter` : '')}
    </p>
  );
}

function Filter(props: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      className="input"
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
    >
      {Object.keys(SHOW).map((name) => (
        <option key={name}>{name}</option>
      ))}
    </select>
  );
}

function Table(props: { days: WorkDayLine[]; toComplete: () => void }) {
  return (
    <div className="table-wrap">
      <table className="data-table days-table">
        <thead>
          <tr>
            {HEAD.map((title) => (
              <th key={title}>{title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.days.map((d) => (
            <DayLine key={d.date} d={d} toComplete={props.toComplete} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** One line per day, newest first: the whole day at a glance. */
export function DaysTable(props: { toComplete: () => void }) {
  const [range, setRange] = useRange(30, 'work.days');
  const [show, setShow] = useStored(
    'work.days.show',
    'Tous les jours',
    Object.keys(SHOW),
  );
  const days = [...(useWorkDays(range).data ?? [])].reverse();
  const shown = days.filter(SHOW[show] ?? (() => true));
  const { page, bar } = usePaging(shown, 50);
  return (
    <section className="card">
      <h2>Mes journées</h2>
      <div className="toolbar">
        <DateRange value={range} onChange={setRange} />
        <Filter value={show} onChange={setShow} />
      </div>
      <Totals days={shown} />
      {bar}
      <Table days={page} toComplete={props.toComplete} />
    </section>
  );
}
