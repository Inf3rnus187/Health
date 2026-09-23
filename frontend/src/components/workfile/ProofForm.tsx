import { type ChangeEvent, type FormEvent, useState } from 'react';

import {
  EVIDENCE_KINDS,
  MEAL_TRACES,
  postForm,
  TRACE_KINDS,
} from '../../api/workfile';
import { useWorkRefresh } from '../../hooks/useWork';
import { nameStamp } from '../../utils/nameStamp';
import { nowLocal } from '../journal/time';
import { Choice } from './fields';

function useAddEvidence(onDone?: () => void) {
  const [error, setError] = useState('');
  const refresh = useWorkRefresh();
  const add = (form: HTMLFormElement) => {
    setError('');
    postForm('/evidence', new FormData(form)).then(
      () => {
        form.reset();
        refresh();
        onDone?.();
      },
      (e: Error) => setError(e.message),
    );
  };
  return { add, error };
}

function Count() {
  return (
    <input
      className="input"
      type="number"
      name="count"
      min={1}
      defaultValue={1}
      title="Combien (ex. 12 appels)"
    />
  );
}

function When(props: {
  kind: string;
  onKind: (kind: string) => void;
  when?: string;
}) {
  return (
    <>
      <input
        className="input"
        type="datetime-local"
        name="occurred_at"
        title="Quand (début, entrée, commande)"
        defaultValue={props.when ?? nowLocal()}
        required
      />
      <Choice
        name="kind"
        options={EVIDENCE_KINDS}
        value={props.kind}
        onChange={props.onKind}
      />
      <Count />
    </>
  );
}

function MealBox() {
  return (
    <label className="muted">
      <input type="checkbox" name="meal" value="true" defaultChecked /> Ajouter
      aussi ce repas au Journal (prix, analyse IA)
    </label>
  );
}

function End() {
  return (
    <input
      className="input"
      type="datetime-local"
      name="ended_at"
      title="Fin (sortie du parking, arrivée du taxi, départ de l’hôtel)"
    />
  );
}

function TraceFields({ kind }: { kind: string }) {
  if (!(kind in TRACE_KINDS)) {
    return null;
  }
  return (
    <>
      <End />
      <input
        className="input"
        name="place"
        placeholder="Lieu, enseigne, trajet"
      />
      <input
        className="input"
        type="number"
        name="amount"
        min={0}
        step={0.01}
        placeholder="Montant €"
      />
      {MEAL_TRACES.includes(kind) && <MealBox />}
    </>
  );
}

/** A file named with its date-time ("2026-05-09 03h47") sets "Quand". */
function fillWhen(e: ChangeEvent<HTMLInputElement>) {
  const name = e.currentTarget.files?.[0]?.name ?? '';
  const stamp = nameStamp(name);
  const when = e.currentTarget.form?.elements.namedItem('occurred_at');
  if (stamp && when instanceof HTMLInputElement) {
    when.value = stamp;
  }
}

function What() {
  return (
    <>
      <input
        className="input"
        name="title"
        placeholder="Titre (ex. appels du responsable)"
      />
      <textarea
        className="input"
        name="description"
        placeholder="Ce que la preuve montre (ex. ce qui a été commandé)"
      />
      <input type="file" name="file" onChange={fillWhen} />
    </>
  );
}

/** Add a proof or a trace; ``when`` presets its date (a day, an absence). */
export function ProofForm(props: {
  when?: string;
  absenceId?: string;
  onDone?: () => void;
}) {
  const { add, error } = useAddEvidence(props.onDone);
  const [kind, setKind] = useState('appel');
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    add(e.currentTarget);
  };
  return (
    <form className="care-form" onSubmit={submit}>
      <When kind={kind} onKind={setKind} when={props.when} />
      <TraceFields kind={kind} />
      <What />
      <input type="hidden" name="absence_id" value={props.absenceId ?? ''} />
      <button className="btn" type="submit">
        Ajouter
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

/** « + Ajouter une preuve » for a day or an absence, after the fact. */
export function AddProof(props: {
  when: string;
  absenceId?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button className="btn ghost" onClick={() => setOpen(true)}>
        + Ajouter une preuve{props.label ?? ''}
      </button>
    );
  }
  return (
    <div className="add-proof">
      <ProofForm {...props} onDone={() => setOpen(false)} />
      <button className="btn ghost" onClick={() => setOpen(false)}>
        Fermer
      </button>
    </div>
  );
}
