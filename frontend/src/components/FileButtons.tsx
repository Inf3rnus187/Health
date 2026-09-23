import { useState } from 'react';

import { openFile } from '../api/files';
import { DownloadButton } from './DownloadButton';

/** « Voir » opens the file in a tab (a blob); « Télécharger » saves it. */
export function FileButtons(props: { path: string; filename: string }) {
  const [error, setError] = useState('');
  const view = () =>
    openFile(props.path, props.filename).catch((e: Error) =>
      setError(e.message),
    );
  return (
    <>
      <button className="btn ghost" onClick={() => void view()}>
        Voir
      </button>
      <DownloadButton path={props.path} filename={props.filename} />
      {error && <span className="error">{error}</span>}
    </>
  );
}

/** A proof's file: « Voir » in a tab, « Télécharger » (none without file). */
export function EvidenceFile(props: { id: string; name: string | null }) {
  if (!props.name) return null;
  return (
    <FileButtons path={`/evidence/${props.id}/file`} filename={props.name} />
  );
}
