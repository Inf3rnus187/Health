import type { ChangeEvent } from 'react';

interface UploadControlsProps {
  canImport: boolean;
  uploading: boolean;
  resetting: boolean;
  onFile: (event: ChangeEvent<HTMLInputElement>) => void;
  onImport: () => void;
  onReset: () => void;
}

const CONFIRM =
  'Supprimer tout ce qui vient de l’export Apple (relevés, séances, ECG, ' +
  'tracés GPS, dossier CDA) ? Vos saisies, compteurs, repas et documents ' +
  'restent. Cette action ne peut pas être annulée.';

export function UploadControls(props: UploadControlsProps) {
  const reset = () => {
    if (window.confirm(CONFIRM)) props.onReset();
  };
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
      <button className="btn ghost" disabled={props.resetting} onClick={reset}>
        Supprimer les données importées
      </button>
    </div>
  );
}
