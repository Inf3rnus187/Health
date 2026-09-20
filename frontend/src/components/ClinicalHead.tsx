import { DownloadButton } from './DownloadButton';

export function ClinicalHead({ count }: { count: number }) {
  return (
    <div className="data-head">
      <h2>Documents cliniques ({count})</h2>
      <DownloadButton
        path="/clinical/document/file"
        filename="export_cda.xml"
        label="XML brut"
      />
    </div>
  );
}
