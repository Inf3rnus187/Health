import { viewMedicalDoc } from '../api/medical';
import type { MedicalDoc } from '../api/types';
import { useDeleteDoc, useMedicalDocs } from '../hooks/useMedical';
import { KIND_LABELS } from '../medical/kinds';

interface RowProps {
  doc: MedicalDoc;
  onDelete: (id: string) => void;
}

function Row({ doc, onDelete }: RowProps) {
  return (
    <li>
      <span className="import-name">{doc.title}</span>
      <span className="badge">{KIND_LABELS[doc.kind] ?? doc.kind}</span>
      <span className="muted">{doc.doc_date ?? '—'}</span>
      <div className="row-actions">
        <button
          className="btn ghost"
          onClick={() => void viewMedicalDoc(doc.id)}
        >
          Voir
        </button>
        <button className="btn ghost" onClick={() => onDelete(doc.id)}>
          Supprimer
        </button>
      </div>
    </li>
  );
}

export function MedicalList() {
  const docs = useMedicalDocs().data ?? [];
  const del = useDeleteDoc();
  if (docs.length === 0) {
    return <p className="muted">Aucun document pour l’instant.</p>;
  }
  return (
    <ul className="med-list">
      {docs.map((doc) => (
        <Row key={doc.id} doc={doc} onDelete={(id) => del.mutate(id)} />
      ))}
    </ul>
  );
}
