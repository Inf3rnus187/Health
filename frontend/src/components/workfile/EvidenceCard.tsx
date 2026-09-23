import { type ChangeEvent, useState } from 'react';

import {
  EVIDENCE_KINDS,
  MEAL_TRACES,
  postForm,
  TRACE_KINDS,
} from '../../api/workfile';
import { useWorkRefresh } from '../../hooks/useWork';
import { nameStamp } from '../../utils/nameStamp';
import { nowLocal } from '../journal/time';
import { EvidenceList } from './EvidenceList';
import { Choice } from './fields';

function useAddEvidence() {
  const [error, setError] = useState('');
  const refresh = useWorkRefresh();
  const add = (form: HTMLFormElement) => {
    setError('');
    postForm('/evidence', new FormData(form)).then(
      () => {
        form.reset();
        refresh();
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

function When(props: { kind: string; onKind: (kind: string) => void }) {
  return (
    <>
      <input
        className="input"
        type="datetime-local"
        name="occurred_at"
        title="Quand (début, entrée, commande)"
        defaultValue={nowLocal()}
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

function EvidenceForm() {
  const { add, error } = useAddEvidence();
  const [kind, setKind] = useState('appel');
  return (
    <form
      className="care-form"
      onSubmit={(e) => {
        e.preventDefault();
        add(e.currentTarget);
      }}
    >
      <When kind={kind} onKind={setKind} />
      <TraceFields kind={kind} />
      <What />
      <button className="btn" type="submit">
        Ajouter
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

/** Proofs (calls, mails…) and traces (transport, taxi, parking, meals…). */
export function EvidenceCard() {
  return (
    <section className="card">
      <h2>Preuves et traces</h2>
      <p className="muted">
        Preuves : appels, SMS, mails, captures. Traces : ce que des tiers ont
        enregistré — métro, taxi, parking, repas livré, hôtel, note de frais.
        Chaque fichier garde son empreinte SHA-256 (imprimée dans le rapport).
        Un fichier nommé avec sa date et son heure (« 2026-05-09 03h47.pdf », «
        09-05-2026_03.47.png ») remplit « Quand » tout seul.
      </p>
      <EvidenceForm />
      <EvidenceList />
    </section>
  );
}
