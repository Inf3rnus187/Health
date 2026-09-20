import type { ChangeEvent } from 'react';

interface UploadControlsProps {
  canImport: boolean;
  uploading: boolean;
  resetting: boolean;
  onFile: (event: ChangeEvent<HTMLInputElement>) => void;
  onImport: () => void;
  onReset: () => void;
}

export function UploadControls(props: UploadControlsProps) {
  return (
    <div className="quick">
      <input type="file" accept=".zip,.xml" onChange={props.onFile} />
      <button
        className="btn"
        disabled={!props.canImport || props.uploading}
        onClick={props.onImport}
      >
        Importer
      </button>
      <button
        className="btn ghost"
        disabled={props.resetting}
        onClick={props.onReset}
      >
        Supprimer les données importées
      </button>
    </div>
  );
}
