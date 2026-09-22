import { viewMedicalDoc } from '../../api/medical';
import type { DocRef } from '../../api/record';
import { shortDate } from '../../utils/format';

/** Opens the source document (title + date). */
export function DocLink({ doc }: { doc: DocRef }) {
  return (
    <button
      className="link-btn"
      title="Ouvrir le document"
      onClick={() => void viewMedicalDoc(doc.id)}
    >
      {doc.title} ({shortDate(doc.date)})
    </button>
  );
}

export function DocLinks({ docs }: { docs: DocRef[] }) {
  if (docs.length === 0) {
    return null;
  }
  return (
    <span className="doc-links">
      {docs.map((doc) => (
        <DocLink key={doc.id} doc={doc} />
      ))}
    </span>
  );
}
