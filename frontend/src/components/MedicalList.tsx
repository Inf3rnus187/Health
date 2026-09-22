import { viewMedicalDoc } from '../api/medical';
import type { MedicalDoc } from '../api/types';
import {
  useAnalyzeAllDocs,
  useAnalyzeDoc,
  useDeleteDoc,
  useMedicalDocs,
} from '../hooks/useMedical';
import { KIND_LABELS } from '../medical/kinds';
import { DocAnalysis } from './DocAnalysis';

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

export function MedicalList() {
  const docs = useMedicalDocs().data ?? [];
  const del = useDeleteDoc();
  const analyze = useAnalyzeDoc();
  if (docs.length === 0) {
    return <p className="muted">Aucun document pour l’instant.</p>;
  }
  return (
    <>
      <AnalyzeAll />
      <ul className="med-list">
        {docs.map((doc) => (
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
