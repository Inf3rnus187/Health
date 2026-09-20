import { DownloadButton } from './DownloadButton';

const FORMATS = [
  { fmt: 'csv', label: 'CSV', ext: 'csv' },
  { fmt: 'json', label: 'JSON', ext: 'json' },
  { fmt: 'xlsx', label: 'Excel', ext: 'xlsx' },
  { fmt: 'fhir', label: 'FHIR', ext: 'json' },
];

export function ExportPanel() {
  return (
    <section className="card">
      <h2>Exporter mes données</h2>
      <p className="muted">
        Télécharge l'intégralité de tes mesures dans le format choisi.
      </p>
      <div className="quick">
        {FORMATS.map((item) => (
          <DownloadButton
            key={item.fmt}
            path={`/export?format=${item.fmt}`}
            filename={`phoenix_export.${item.ext}`}
            label={item.label}
          />
        ))}
      </div>
    </section>
  );
}
