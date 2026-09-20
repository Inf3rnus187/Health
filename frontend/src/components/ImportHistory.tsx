import type { ImportJob } from '../api/types';

interface ImportHistoryProps {
  jobs: ImportJob[];
}

function summary(job: ImportJob): string {
  if (job.status === 'running') {
    return `${job.phase} — ${job.processed} enregistrements lus`;
  }
  if (job.status === 'error') {
    return job.error ?? 'erreur';
  }
  if (job.status === 'queued') {
    return 'en file d’attente…';
  }
  return [
    `${job.samples} échantillons`,
    `${job.workouts} séances`,
    `${job.ecg} ECG`,
    `${job.routes} tracés`,
  ].join(' · ');
}

export function ImportHistory({ jobs }: ImportHistoryProps) {
  if (jobs.length === 0) {
    return null;
  }
  return (
    <ul className="import-list">
      {jobs.map((job) => (
        <li key={job.id}>
          <span className={`badge badge-${job.status}`}>{job.status}</span>
          <span className="import-name">{job.filename}</span>
          <span className="muted">{summary(job)}</span>
        </li>
      ))}
    </ul>
  );
}
