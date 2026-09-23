import { useState } from 'react';

import type { Night } from '../../api/workfile';
import { useAddNight, useNights } from '../../hooks/useWorkFile';
import { localToday, shortDate } from '../../utils/format';
import { daysAgo } from '../work/format';
import { Input } from './fields';
import { hoursText } from './keys';

function Row({ night }: { night: Night }) {
  if (night.missing) {
    return (
      <tr>
        <td>{shortDate(night.wake_day)}</td>
        <td colSpan={4} className="muted">
          aucune donnée (montre non portée ?)
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td>{shortDate(night.wake_day)}</td>
      <td>{hoursText(night.asleep_min)}</td>
      <td>{night.awakenings ?? '—'} réveils</td>
      <td>{night.blocks ?? '—'} blocs</td>
      <td>
        {night.bedtime ?? '?'} → {night.wake_time ?? '?'}
      </td>
    </tr>
  );
}

const FIELDS = [
  { key: 'bed', label: 'Coucher', type: 'datetime-local' },
  { key: 'wake', label: 'Lever', type: 'datetime-local' },
  { key: 'woke', label: 'Réveils', type: 'number' },
] as const;
type Values = Record<(typeof FIELDS)[number]['key'], string>;

function Inputs(props: { values: Values; set: (v: Values) => void }) {
  const { values, set } = props;
  return (
    <>
      {FIELDS.map((f) => (
        <Input
          key={f.key}
          label={f.label}
          type={f.type}
          value={values[f.key]}
          onChange={(v) => set({ ...values, [f.key]: v })}
        />
      ))}
    </>
  );
}

function TypeNight() {
  const add = useAddNight();
  const [values, setValues] = useState<Values>({ bed: '', wake: '', woke: '' });
  const save = () =>
    add.mutate({
      bedtime: values.bed,
      wake_time: values.wake,
      awakenings: values.woke ? Number(values.woke) : null,
    });
  return (
    <div className="quick">
      <Inputs values={values} set={setValues} />
      <button
        className="btn"
        disabled={!values.bed || !values.wake}
        onClick={save}
      >
        Ajouter la nuit
      </button>
      {add.error && <span className="error">{add.error.message}</span>}
    </div>
  );
}

/** The last 30 nights; type the ones the watch missed. */
export function NightsCard() {
  const nights = useNights(daysAgo(29), localToday()).data ?? [];
  return (
    <section className="card">
      <h2>Nuits (30 derniers réveils)</h2>
      <p className="muted">
        Réveils et « blocs » (sommeil en plusieurs fois, coupé d’une heure ou
        plus) lus dans les phases de la montre. Une nuit manquante se saisit ici
        : elle est marquée « saisie » dans le rapport.
      </p>
      <TypeNight />
      <div className="table-wrap">
        <table className="data-table">
          <tbody>
            {nights.map((n) => (
              <Row key={n.wake_day} night={n} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
