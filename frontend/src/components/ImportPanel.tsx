import { useImportJobs } from '../hooks/useImportJobs';
import { ImportHistory } from './ImportHistory';
import { UploadForm } from './UploadForm';

export function ImportPanel() {
  const jobs = useImportJobs();
  return (
    <section className="card">
      <h2>Importer mes données Apple Santé</h2>
      <p className="muted">
        Déposez export.zip (ECG et tracés inclus) ou export.xml.
      </p>
      <UploadForm />
      <ImportHistory jobs={jobs.data ?? []} />
    </section>
  );
}
