import { useState } from 'react';

import type { Bulk, Deleted } from '../api/bulk';
import { useBulkDelete, type Selection } from '../hooks/useSelection';

/** The tick box of one item. */
export function PickBox(props: { sel: Selection; id: string }) {
  return (
    <input
      type="checkbox"
      aria-label="Sélectionner"
      checked={props.sel.has(props.id)}
      onChange={() => props.sel.toggle(props.id)}
    />
  );
}

function AllBox(props: { sel: Selection; shown: string[]; picked: number }) {
  const all = props.shown.length > 0 && props.picked === props.shown.length;
  return (
    <label>
      <input
        type="checkbox"
        checked={all}
        onChange={(e) => props.sel.set(e.target.checked ? props.shown : [])}
      />{' '}
      Tout sélectionner ({props.shown.length} affiché
      {props.shown.length > 1 ? 's' : ''}, toutes pages)
    </label>
  );
}

function MealsBox(props: {
  count: number;
  on: boolean;
  set: (on: boolean) => void;
}) {
  if (props.count === 0) return null;
  return (
    <label>
      <input
        type="checkbox"
        checked={props.on}
        onChange={(e) => props.set(e.target.checked)}
      />{' '}
      et les {props.count} repas du Journal créés par ces livraisons
    </label>
  );
}

interface BarProps {
  what: Bulk;
  /** "sessions", "preuves et traces (avec leurs fichiers)"… */
  noun: string;
  /** Ids of every item the filters show (all pages). */
  shown: string[];
  sel: Selection;
  /** How many of these ids have a meal logged (proofs only). */
  meals?: (ids: string[]) => number;
}

function useRun(props: BarProps, picked: string[], meals: boolean) {
  const del = useBulkDelete(props.what);
  const [done, setDone] = useState('');
  const run = () => {
    const text = `Supprimer ${picked.length} ${props.noun} ? C’est définitif.`;
    if (!window.confirm(text)) return;
    const onSuccess = (r: Deleted) => {
      props.sel.set([]);
      setDone(report(r));
    };
    del.mutate({ ids: picked, meals }, { onSuccess });
  };
  return { run, done, error: del.error };
}

/** Tick all, how many are ticked, delete them (after a confirmation). */
export function BulkBar(props: BarProps) {
  const [withMeals, setWithMeals] = useState(true);
  const picked = props.shown.filter((id) => props.sel.has(id));
  const meals = props.meals?.(picked) ?? 0;
  const { run, done, error } = useRun(props, picked, withMeals && meals > 0);
  return (
    <div className="bulk-bar">
      <AllBox sel={props.sel} shown={props.shown} picked={picked.length} />
      <MealsBox count={meals} on={withMeals} set={setWithMeals} />
      <button className="btn danger" disabled={!picked.length} onClick={run}>
        Supprimer la sélection ({picked.length})
      </button>
      {done && <span className="muted">{done}</span>}
      {error && <span className="error">{error.message}</span>}
    </div>
  );
}

function report(r: Deleted): string {
  const meals = r.meals ? `, ${r.meals} repas` : '';
  return `${r.deleted} supprimé${r.deleted > 1 ? 's' : ''}${meals}.`;
}
