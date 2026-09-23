import { useState } from 'react';

import {
  EVIDENCE_KINDS,
  type EvidenceItem,
  MEAL_TRACES,
  postForm,
  TRACE_KINDS,
} from '../../api/workfile';
import { useWorkRefresh } from '../../hooks/useWork';
import { useDeleteEvidence, useEvidence } from '../../hooks/useWorkFile';
import { DownloadButton } from '../DownloadButton';
import { nowLocal } from '../journal/time';
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
      <input type="file" name="file" />
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

function fmt(iso: string, withTime: boolean): string {
  const at = new Date(iso);
  return withTime
    ? at.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
    : at.toLocaleDateString('fr-FR');
}

function span(item: EvidenceItem): string {
  const end = item.ended_at ? ` → ${fmt(item.ended_at, true)}` : '';
  return `${fmt(item.occurred_at, item.time_known)}${end}`;
}

function Details({ item }: { item: EvidenceItem }) {
  return (
    <>
      {span(item)} — <strong>{EVIDENCE_KINDS[item.kind] ?? item.kind}</strong>
      {item.count > 1 && ` ×${item.count}`} {item.title}
      {item.place && item.place !== item.title && ` · ${item.place}`}
      {item.amount != null && ` · ${item.amount} €`}
      {item.meal_id && ' · repas au Journal'}
      {item.sha256 && (
        <span className="muted"> · SHA-256 {item.sha256.slice(0, 12)}…</span>
      )}
    </>
  );
}

function Item({ item }: { item: EvidenceItem }) {
  const del = useDeleteEvidence();
  return (
    <li>
      <Details item={item} />
      {item.file_name && (
        <DownloadButton
          path={`/evidence/${item.id}/file`}
          filename={item.file_name}
          label="Fichier"
        />
      )}
      <button className="btn ghost" onClick={() => del.mutate(item.id)}>
        Supprimer
      </button>
    </li>
  );
}

/** Proofs (calls, mails…) and traces (transport, taxi, parking, meals…). */
export function EvidenceCard() {
  const items = useEvidence().data ?? [];
  return (
    <section className="card">
      <h2>Preuves et traces ({items.length})</h2>
      <p className="muted">
        Preuves : appels, SMS, mails, captures. Traces : ce que des tiers ont
        enregistré — métro, taxi, parking, repas livré, hôtel, note de frais.
        Chaque fichier garde son empreinte SHA-256 (imprimée dans le rapport).
      </p>
      <EvidenceForm />
      <ul className="care-list">
        {items.map((item) => (
          <Item key={item.id} item={item} />
        ))}
      </ul>
    </section>
  );
}
