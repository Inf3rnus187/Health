import { useState } from 'react';

import {
  EVIDENCE_KINDS,
  type EvidenceItem,
  postForm,
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

function When() {
  const [kind, setKind] = useState('appel');
  return (
    <>
      <input
        className="input"
        type="datetime-local"
        name="occurred_at"
        title="Quand"
        defaultValue={nowLocal()}
        required
      />
      <Choice
        name="kind"
        options={EVIDENCE_KINDS}
        value={kind}
        onChange={setKind}
      />
      <Count />
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
        placeholder="Ce que la preuve montre"
      />
      <input type="file" name="file" />
    </>
  );
}

function EvidenceFields() {
  return (
    <>
      <When />
      <What />
    </>
  );
}

function EvidenceForm() {
  const { add, error } = useAddEvidence();
  return (
    <form
      className="care-form"
      onSubmit={(e) => {
        e.preventDefault();
        add(e.currentTarget);
      }}
    >
      <EvidenceFields />
      <button className="btn" type="submit">
        Ajouter la preuve
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

function Item({ item }: { item: EvidenceItem }) {
  const del = useDeleteEvidence();
  const when = new Date(item.occurred_at).toLocaleString('fr-FR');
  return (
    <li>
      {when} — <strong>{EVIDENCE_KINDS[item.kind] ?? item.kind}</strong>
      {item.count > 1 && ` ×${item.count}`} {item.title}
      {item.sha256 && (
        <span className="muted"> · SHA-256 {item.sha256.slice(0, 12)}…</span>
      )}
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

/** Calls, messages, mails, screenshots: dated, counted, fingerprinted. */
export function EvidenceCard() {
  const items = useEvidence().data ?? [];
  return (
    <section className="card">
      <h2>Preuves ({items.length})</h2>
      <p className="muted">
        Chaque fichier garde son empreinte SHA-256 (imprimée dans le rapport) :
        une copie peut être comparée à l’original.
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
