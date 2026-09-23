import { useEffect } from 'react';

import { useFileUrl } from '../../hooks/useFileUrl';
import { money } from '../../utils/format';
import { DownloadButton } from '../DownloadButton';

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
  const path = item.file_name ? `/evidence/${item.id}/file` : null;
  const { url, error } = useFileUrl(path);
  if (!path) return <p className="muted">Pas de fichier joint.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!url) return <p className="muted">Chargement du fichier…</p>;
  const media = item.media_type ?? '';
  if (media.startsWith('image/')) {
    return <img className="viewer-file" src={url} alt={item.title} />;
  }
  if (media === 'application/pdf') {
    return (
      <>
        <button
          className="btn ghost"
          onClick={() => window.open(url, '_blank', 'noopener')}
        >
          Ouvrir le PDF dans un onglet
        </button>
        <iframe className="viewer-file" src={url} title={item.title} />
      </>
    );
  }
  return <p className="muted">Aperçu impossible : téléchargez le fichier.</p>;
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
        <Preview item={item} />
        {item.file_name && (
          <DownloadButton
            path={`/evidence/${item.id}/file`}
            filename={item.file_name}
          />
        )}
      </div>
    </div>
  );
}
