import { useState } from 'react';

import { downloadRecord } from '../api/records';

interface DownloadButtonProps {
  path: string;
  filename: string;
  label?: string;
}

export function DownloadButton(props: DownloadButtonProps) {
  const [busy, setBusy] = useState(false);
  const onClick = async () => {
    setBusy(true);
    try {
      await downloadRecord(props.path, props.filename);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button
      className="btn ghost"
      disabled={busy}
      onClick={() => void onClick()}
    >
      {props.label ?? 'Télécharger'}
    </button>
  );
}
