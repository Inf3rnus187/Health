import { viewMedicalDoc } from '../api/medical';
import type { MedicalDoc } from '../api/types';
import {
  useAnalyzeAllDocs,
  useAnalyzeDoc,
  useDeleteDoc,
  useMedicalDocs,
} from '../hooks/useMedical';
import { useState } from 'react';

import { KIND_LABELS } from '../medical/kinds';
import { DocAnalysis } from './DocAnalysis';
import { usePaging } from './Paging';

interface RowProps {
  doc: MedicalDoc;
  onDelete: (id: string) => void;
  onAnalyze: (id: string) => void;
}

function Actions({ doc, onDelete, onAnalyze }: RowProps) {
  return (
    <div className="row-actions">
      <button className="btn ghost" onClick={() => void viewMedicalDoc(doc.id)}>
        Voir
      </button>
      <button className="btn ghost" onClick={() => onAnalyze(doc.id)}>
        {doc.analysis_status ? 'Réanalyser (IA)' : 'Analyser (IA)'}
      </button>
      <button className="btn ghost" onClick={() => onDelete(doc.id)}>
        Supprimer
      </button>
    </div>
  );
}

function Row(props: RowProps) {
  const { doc } = props;
  return (
    <li>
      <span className="import-name">{doc.title}</span>
      <span className="badge">{KIND_LABELS[doc.kind] ?? doc.kind}</span>
      <span className="muted">{doc.doc_date ?? '—'}</span>
      <Actions {...props} />
      <DocAnalysis status={doc.analysis_status} analysis={doc.analysis} />
    </li>
  );
}

function AnalyzeAll() {
  const all = useAnalyzeAllDocs();
  return (
    <div className="med-toolbar">
      <button
        className="btn ghost"
        disabled={all.isPending}
        onClick={() => all.mutate()}
      >
        Analyser tous les documents (IA)
      </button>
      {all.data && (
        <span className="muted">{all.data.queued} document(s) en lecture…</span>
      )}
    </div>
  );
}

function matches(doc: MedicalDoc, text: string): boolean {
  const needle = text.trim().toLowerCase();
  const kind = KIND_LABELS[doc.kind] ?? doc.kind;
  const said = `${doc.title} ${kind} ${doc.doc_date ?? ''}`.toLowerCase();
  return said.includes(needle);
}

function Rows({ docs }: { docs: MedicalDoc[] }) {
  const del = useDeleteDoc();
  const analyze = useAnalyzeDoc();
  const { page, bar } = usePaging(docs, 10);
  return (
    <>
      {bar}
      <ul className="med-list">
        {page.map((doc) => (
          <Row
            key={doc.id}
            doc={doc}
            onDelete={(id) => del.mutate(id)}
            onAnalyze={(id) => analyze.mutate(id)}
          />
        ))}
      </ul>
    </>
  );
}

/** The documents, searchable (title, kind, date), a page at a time. */
export function MedicalList() {
  const docs = useMedicalDocs().data ?? [];
  const [text, setText] = useState('');
  if (docs.length === 0) {
    return <p className="muted">Aucun document pour l’instant.</p>;
  }
  return (
    <>
      <AnalyzeAll />
      <input
        className="input"
        placeholder="Chercher (titre, type, date)"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Rows docs={docs.filter((doc) => matches(doc, text))} />
    </>
  );
}
