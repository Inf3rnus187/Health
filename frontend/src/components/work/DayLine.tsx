import { Fragment, useState } from 'react';

import type { WorkDayLine } from '../../api/work';
import { money, shortDate } from '../../utils/format';
import { EvidenceFile } from '../FileButtons';
import { hm } from './format';

const WEEKDAYS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'];
const OFF: Record<string, string> = {
  arret: 'Arrêt',
  conge: 'Congés',
  repos: 'Repos',
  autre: 'Absence',
  ferie: 'Férié',
};

function night(d: WorkDayLine): string {
  if (d.sleep_min == null) return '—';
  const woke = d.awakenings ? ` · ${d.awakenings} réveils` : '';
  return `${hm(d.sleep_min / 60)}${woke}`;
}

function worked(d: WorkDayLine): string {
  if (d.hours == null) return d.sessions ? '?' : '—';
  return hm(d.hours) + (d.remote ? ` (dist. ${hm(d.remote)})` : '');
}

function absence(d: WorkDayLine): string {
  if (!d.absence) return '';
  return (OFF[d.absence] ?? d.absence) + (d.absence_share < 1 ? ' ½' : '');
}

function State(props: { d: WorkDayLine; toComplete: () => void }) {
  if (props.d.state === 'a_completer') {
    return (
      <button className="badge badge-warn" onClick={props.toComplete}>
        à compléter
      </button>
    );
  }
  return props.d.state === 'en_cours' ? <span>en cours</span> : null;
}

function Proofs({ d }: { d: WorkDayLine }) {
  return (
    <ul className="care-list">
      {d.proofs.map((p) => (
        <li key={p.id}>
          <strong>{p.label}</strong> {p.time ?? 'heure inconnue'}
          {p.end && ` → ${p.end}`} {p.title}
          {p.amount != null && ` · ${money(p.amount)} €`}{' '}
          <EvidenceFile id={p.id} name={p.file_name} />
        </li>
      ))}
    </ul>
  );
}

function cells(d: WorkDayLine): string[] {
  const day = `${WEEKDAYS[d.weekday]} ${shortDate(d.date)}`;
  const times = [d.wake_time, d.start, d.end].map((t) => t ?? '—');
  return [day, night(d), ...times, worked(d), d.bedtime ?? '—'];
}

function Toggle(props: { count: number; open: boolean; on: () => void }) {
  if (props.count === 0) return null;
  return (
    <button className="btn ghost" onClick={props.on}>
      {props.count} {props.open ? '▴' : '▾'}
    </button>
  );
}

function Row(props: {
  d: WorkDayLine;
  open: boolean;
  toggle: () => void;
  toComplete: () => void;
}) {
  const { d } = props;
  return (
    <tr className={d.weekday >= 5 ? 'weekend' : undefined}>
      {cells(d).map((text, n) => (
        <td key={n} className={n === 5 ? 'nowrap strong' : 'nowrap'}>
          {text}
        </td>
      ))}
      <td>{absence(d)}</td>
      <td>
        <Toggle count={d.proofs.length} open={props.open} on={props.toggle} />
      </td>
      <td>
        <State d={d} toComplete={props.toComplete} />
      </td>
    </tr>
  );
}

/** One day: night, wake-up, work, evening, absence, proofs, state. */
export function DayLine(props: { d: WorkDayLine; toComplete: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Fragment>
      <Row
        d={props.d}
        open={open}
        toggle={() => setOpen(!open)}
        toComplete={props.toComplete}
      />
      {open && (
        <tr>
          <td colSpan={10}>
            <Proofs d={props.d} />
          </td>
        </tr>
      )}
    </Fragment>
  );
}
