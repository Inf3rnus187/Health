import { useEffect } from 'react';

import { useFileUrl } from '../../hooks/useFileUrl';
import { money } from '../../utils/format';
import { EvidenceFile } from '../FileButtons';

/** What the viewer shows of a proof or a trace. */
export interface Viewable {
  id: string;
  label: string;
  when: string;
  title: string;
  place?: string | null;
  amount?: number | null;
  currency?: string | null;
  description?: string | null;
  file_name?: string | null;
  media_type?: string | null;
}

function Preview({ item }: { item: Viewable }) {
  const image = (item.media_type ?? '').startsWith('image/');
  const path = item.file_name && image ? `/evidence/${item.id}/file` : null;
  const { url, error } = useFileUrl(path);
  if (!item.file_name) return <p className="muted">Pas de fichier joint.</p>;
  if (!image) return null;
  if (error) return <p className="error">{error}</p>;
  if (!url) return <p className="muted">Chargement de l’image…</p>;
  return <img className="viewer-file" src={url} alt={item.title} />;
}

function Facts({ item }: { item: Viewable }) {
  const amount =
    item.amount != null
      ? `${money(item.amount)} ${item.currency ?? 'EUR'}`
      : '';
  const facts: [string, string][] = [
    ['Quand', item.when],
    ['Titre', item.title],
    ['Lieu', item.place ?? ''],
    ['Montant', amount],
  ];
  return (
    <dl className="viewer-facts">
      {facts
        .filter(([, value]) => value)
        .map(([name, value]) => (
          <div key={name}>
            <dt className="muted">{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
    </dl>
  );
}

function useEscape(onClose: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
}

/** A proof or a trace, its details and its file, over the page. */
export function EvidenceViewer(props: { item: Viewable; onClose: () => void }) {
  const { item, onClose } = props;
  useEscape(onClose);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="data-head">
          <h3>{item.label}</h3>
          <button className="btn ghost" onClick={onClose}>
            Fermer
          </button>
        </div>
        <Facts item={item} />
        {item.description && <p className="viewer-text">{item.description}</p>}
        <div className="quick">
          <EvidenceFile id={item.id} name={item.file_name ?? null} />
        </div>
        <Preview item={item} />
      </div>
    </div>
  );
}
