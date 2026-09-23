import { TRACE_KINDS } from '../../api/workfile';
import { money, shortDate } from '../../utils/format';

/** One trace as read, before it is stored. */
export interface PreviewRow {
  day: string;
  time: string | null;
  end: string | null;
  kind: string;
  title: string;
  place: string;
  amount: number | null;
  what: string;
}

export interface SkippedRow {
  line: number;
  reason: string;
}

function Row({ t }: { t: PreviewRow }) {
  const label = TRACE_KINDS[t.kind] ?? t.kind;
  return (
    <tr>
      <td className="nowrap">{shortDate(t.day)}</td>
      <td className="nowrap">
        {t.time ?? '?'}
        {t.end && ` → ${t.end}`}
      </td>
      <td>{label.split(' (')[0]}</td>
      <td>
        <strong>{t.title}</strong>
        {t.place && !t.title.includes(t.place) && ` · ${t.place}`}
        {t.what && <div className="muted">{t.what}</div>}
      </td>
      <td className="nowrap">{t.amount != null && `${money(t.amount)} €`}</td>
    </tr>
  );
}

/** The first traces read, as they will be stored: check before importing. */
export function TracePreview({ rows }: { rows: PreviewRow[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Jour</th>
            <th>Heure</th>
            <th>Type</th>
            <th>Établissement, trajet, détail</th>
            <th>Prix</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t, i) => (
            <Row key={`${t.day}-${t.time}-${i}`} t={t} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The lines left out, and why (cancelled, no date…). */
export function Skipped(props: { rows: SkippedRow[]; count: number }) {
  if (props.count === 0) return null;
  return (
    <details>
      <summary>
        {props.count} ligne{props.count > 1 ? 's' : ''} non importée
        {props.count > 1 ? 's' : ''} : pourquoi
      </summary>
      <ul className="care-list">
        {props.rows.map((s) => (
          <li key={s.line}>
            ligne {s.line} : {s.reason}
          </li>
        ))}
      </ul>
    </details>
  );
}
