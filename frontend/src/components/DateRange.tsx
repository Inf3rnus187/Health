import { localToday } from '../utils/format';
import { lastDays, type Range } from '../utils/range';

const PRESETS: [string, number | null][] = [
  ['7 j', 7],
  ['30 j', 30],
  ['3 mois', 91],
  ['1 an', 365],
  ['Tout', null],
];

interface Props {
  value: Range;
  onChange: (r: Range) => void;
}

function Presets({ value, onChange }: Props) {
  return (
    <>
      {PRESETS.map(([label, days]) => {
        const r = lastDays(days);
        const on = r.start === value.start && r.end === value.end;
        return (
          <button
            key={label}
            className={on ? 'tab active' : 'tab'}
            onClick={() => onChange(r)}
          >
            {label}
          </button>
        );
      })}
    </>
  );
}

function Day(props: {
  label: string;
  value: string;
  onChange: (day: string) => void;
}) {
  return (
    <label className="muted">
      {props.label}{' '}
      <input
        className="input"
        type="date"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </label>
  );
}

/** A period ending before today (kept from an earlier visit): say so. */
function Past({ value, onChange }: Props) {
  const today = localToday();
  if (!value.end || value.end >= today) return null;
  return (
    <p className="notice">
      La période s’arrête le {value.end.split('-').reverse().join('/')} : les
      jours suivants ne sont pas affichés.{' '}
      <button
        className="btn ghost"
        onClick={() => onChange({ ...value, end: today })}
      >
        Jusqu’à aujourd’hui
      </button>
    </p>
  );
}

/** Quick periods plus exact "Du" / "au" days. */
export function DateRange({ value, onChange }: Props) {
  return (
    <>
      <Periods value={value} onChange={onChange} />
      <Past value={value} onChange={onChange} />
    </>
  );
}

function Periods({ value, onChange }: Props) {
  return (
    <div className="tabs date-range">
      <Presets value={value} onChange={onChange} />
      <Day
        label="Du"
        value={value.start}
        onChange={(start) => onChange({ ...value, start })}
      />
      <Day
        label="au"
        value={value.end}
        onChange={(end) => onChange({ ...value, end: end || localToday() })}
      />
    </div>
  );
}
